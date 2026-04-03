import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

import oci
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import config
from .models_registry import load_models_registry, resolve_chat_model_id, resolve_embedding_model_id
from .oci_client import genai_client
from .openai_mapping import (
    openai_messages_to_single_user_prompt,
    openai_messages_to_oci_generic_messages,
    parse_openai_tool_choice_to_oci_tool_choice,
    parse_openai_tools_to_oci_generic_tools,
)
from .streaming import as_openai_sse_data, stream_oci_sse_as_openai

app = FastAPI()


def require_api_key(authorization: Optional[str]) -> None:
    if not config.PROXY_API_KEY:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != config.PROXY_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")


def _resolve_endpoint_from_registry_or_default() -> str:
    endpoint, _models = load_models_registry()
    return endpoint


def oci_chat_text_only(*, prompt: str, model_id: str, endpoint: str, max_tokens: int, temperature: float, top_p: float) -> Dict[str, Any]:
    client = genai_client(endpoint)

    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    content = oci.generative_ai_inference.models.TextContent()
    content.text = prompt

    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [message]
    chat_request.max_tokens = max_tokens
    chat_request.temperature = temperature
    chat_request.top_p = top_p
    chat_request.top_k = 1

    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = config.OCI_COMPARTMENT_ID

    resp = client.chat(chat_detail)

    data = resp.data
    chat_response = getattr(data, "chat_response", None)
    if not chat_response:
        raise HTTPException(status_code=502, detail="Unexpected OCI response: missing chat_response")

    choices = getattr(chat_response, "choices", None) or []
    if not choices:
        raise HTTPException(status_code=502, detail="Unexpected OCI response: missing choices")

    choice0 = choices[0]
    msg = getattr(choice0, "message", None)
    if msg is None:
        raise HTTPException(status_code=502, detail="Unexpected OCI response: missing message")

    content_list = getattr(msg, "content", None) or []
    if not content_list:
        raise HTTPException(status_code=502, detail="Unexpected OCI response: missing message content")

    text = getattr(content_list[0], "text", "")
    usage = getattr(chat_response, "usage", None)

    return {
        "text": text,
        "usage": usage,
        "raw_model_id": getattr(data, "model_id", None),
        "raw_model_version": getattr(data, "model_version", None),
    }


def oci_chat_stream(*, body: Dict[str, Any], model_id: str, endpoint: str, model_name: str, completion_id: str, created: int, max_tokens: int, temperature: float, top_p: float) -> Iterable[str]:
    client = genai_client(endpoint)

    oci_tools = parse_openai_tools_to_oci_generic_tools(body.get("tools"))
    oci_tool_choice = parse_openai_tool_choice_to_oci_tool_choice(body.get("tool_choice"))

    is_parallel_tool_calls = body.get("is_parallel_tool_calls")
    if is_parallel_tool_calls is not None and not isinstance(is_parallel_tool_calls, bool):
        raise HTTPException(status_code=400, detail="is_parallel_tool_calls must be boolean")

    include_usage = False
    stream_options = body.get("stream_options")
    if isinstance(stream_options, dict) and isinstance(stream_options.get("include_usage"), bool):
        include_usage = bool(stream_options.get("include_usage"))

    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise HTTPException(status_code=400, detail="messages[] is required")

    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = openai_messages_to_oci_generic_messages(raw_messages)

    chat_request.max_tokens = max_tokens
    chat_request.temperature = temperature
    chat_request.top_p = top_p
    chat_request.top_k = 1
    chat_request.is_stream = True

    if oci_tools is not None:
        chat_request.tools = oci_tools
    if oci_tool_choice is not None:
        chat_request.tool_choice = oci_tool_choice
    if is_parallel_tool_calls is not None:
        chat_request.is_parallel_tool_calls = is_parallel_tool_calls

    if include_usage:
        chat_request.stream_options = {"isIncludeUsage": True}

    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = config.OCI_COMPARTMENT_ID

    resp = client.chat(chat_detail)

    yield as_openai_sse_data(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
    )

    yield from stream_oci_sse_as_openai(
        sse_client=resp.data,
        completion_id=completion_id,
        created=created,
        model_name=model_name,
        include_usage=include_usage,
    )


def oci_embed(inputs: List[str], model_id: str, endpoint: str, truncate: str = "NONE") -> Any:
    client = genai_client(endpoint)

    embed_detail = oci.generative_ai_inference.models.EmbedTextDetails()
    embed_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)
    embed_detail.inputs = inputs
    embed_detail.truncate = truncate
    embed_detail.compartment_id = config.OCI_COMPARTMENT_ID

    resp = client.embed_text(embed_detail)
    return resp.data


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def list_models():
    _endpoint, models = load_models_registry()
    data = []
    for name, mi in sorted(models.items(), key=lambda kv: kv[0]):
        data.append({"id": name, "object": "model", "created": 0, "owned_by": "oci", "type": mi.model_type})
    return JSONResponse({"object": "list", "data": data})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: Optional[str] = Header(default=None)):
    require_api_key(authorization)

    body = await request.json()

    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages[] is required")

    stream = bool(body.get("stream", False))

    raw_max_completion_tokens = body.get("max_completion_tokens")
    raw_max_tokens = body.get("max_tokens", 600)
    try:
        max_tokens = int(raw_max_completion_tokens if raw_max_completion_tokens is not None else raw_max_tokens)
    except Exception:
        raise HTTPException(status_code=400, detail="max_tokens/max_completion_tokens must be an integer")
    if max_tokens < 1:
        raise HTTPException(status_code=400, detail="max_tokens/max_completion_tokens must be >= 1")

    temperature = float(body.get("temperature", 1.0))
    top_p = float(body.get("top_p", 1.0))

    request_model = body.get("model", "oci-genai")
    model_id = resolve_chat_model_id(request_model if isinstance(request_model, str) else None)
    model_name = request_model if isinstance(request_model, str) else "oci-genai"

    endpoint = _resolve_endpoint_from_registry_or_default()

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if not stream:
        prompt = openai_messages_to_single_user_prompt(messages)
        t0 = time.time()
        result = oci_chat_text_only(prompt=prompt, model_id=model_id, endpoint=endpoint, max_tokens=max_tokens, temperature=temperature, top_p=top_p)
        dt = time.time() - t0

        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model_name,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result["text"]}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": getattr(result["usage"], "prompt_tokens", 0) if result["usage"] else 0,
                "completion_tokens": getattr(result["usage"], "completion_tokens", 0) if result["usage"] else 0,
                "total_tokens": getattr(result["usage"], "total_tokens", 0) if result["usage"] else 0,
                "proxy_latency_s": dt,
            },
            "oci": {
                "endpoint": endpoint,
                "requested_model": model_name,
                "resolved_model_id": model_id,
                "model_id": result.get("raw_model_id"),
                "model_version": result.get("raw_model_version"),
            },
        }
        return JSONResponse(response)

    def event_stream() -> Iterable[str]:
        yield from oci_chat_stream(
            body=body,
            model_id=model_id,
            endpoint=endpoint,
            model_name=model_name,
            completion_id=completion_id,
            created=created,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/v1/embeddings")
async def embeddings(request: Request, authorization: Optional[str] = Header(default=None)):
    require_api_key(authorization)

    body = await request.json()

    request_model = body.get("model")
    if not isinstance(request_model, str) or not request_model.strip():
        raise HTTPException(status_code=400, detail="model is required for embeddings")

    raw_input = body.get("input")
    if isinstance(raw_input, str):
        inputs = [raw_input]
    elif isinstance(raw_input, list) and all(isinstance(x, str) for x in raw_input):
        inputs = raw_input
    else:
        raise HTTPException(status_code=400, detail="input must be a string or array of strings")

    try:
        model_id = resolve_embedding_model_id(request_model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    endpoint = _resolve_endpoint_from_registry_or_default()

    t0 = time.time()
    raw = oci_embed(inputs=inputs, model_id=model_id, endpoint=endpoint)
    dt = time.time() - t0

    data_items = []
    vectors = getattr(raw, "embeddings", None)
    if isinstance(vectors, list):
        for i, item in enumerate(vectors):
            vec = getattr(item, "embedding", None)
            if vec is None and isinstance(item, dict):
                vec = item.get("embedding")
            if vec is None:
                vec = item
            data_items.append({"object": "embedding", "index": i, "embedding": vec})

    resp = {
        "object": "list",
        "data": data_items,
        "model": request_model,
        "usage": {"prompt_tokens": 0, "total_tokens": 0, "proxy_latency_s": dt},
        "oci": {"endpoint": endpoint, "requested_model": request_model, "resolved_model_id": model_id, "raw": str(raw)},
    }
    return JSONResponse(resp)
