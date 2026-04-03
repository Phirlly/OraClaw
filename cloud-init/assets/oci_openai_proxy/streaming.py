import json
import uuid
from typing import Any, Dict, Iterable, List, Optional


def as_openai_sse_data(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def stream_oci_sse_as_openai(
    *,
    sse_client: Any,
    completion_id: str,
    created: int,
    model_name: str,
    include_usage: bool,
) -> Iterable[str]:
    if not hasattr(sse_client, "events"):
        raise RuntimeError("Unexpected OCI streaming response: resp.data does not expose events()")

    finish_reason: Optional[str] = None
    usage_obj: Optional[Dict[str, Any]] = None
    tool_call_id_by_name: Dict[str, str] = {}

    for ev in sse_client.events():
        raw = getattr(ev, "data", None)
        if raw is None:
            continue

        try:
            obj = json.loads(raw)
        except Exception:
            continue

        if not isinstance(obj, dict):
            continue

        if "usage" in obj and isinstance(obj.get("usage"), dict):
            usage_obj = obj.get("usage")
            continue

        msg = obj.get("message")
        if isinstance(msg, dict):
            tool_calls = msg.get("toolCalls")
            if isinstance(tool_calls, list) and tool_calls:
                openai_tool_calls: List[Dict[str, Any]] = []
                for i, tc in enumerate(tool_calls):
                    if not isinstance(tc, dict):
                        continue
                    if tc.get("type") != "FUNCTION":
                        continue
                    name = tc.get("name")
                    args = tc.get("arguments")
                    if not isinstance(name, str) or not name:
                        continue
                    if args is None:
                        args = "{}"
                    if not isinstance(args, str):
                        args = json.dumps(args)

                    oci_id = tc.get("id")
                    if isinstance(oci_id, str) and oci_id:
                        call_id = oci_id
                    else:
                        call_id = tool_call_id_by_name.get(name)
                        if not call_id:
                            call_id = f"call_{uuid.uuid4().hex}"
                            tool_call_id_by_name[name] = call_id

                    openai_tool_calls.append(
                        {
                            "index": i,
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": args},
                        }
                    )

                if openai_tool_calls:
                    yield as_openai_sse_data(
                        {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model_name,
                            "choices": [
                                {"index": 0, "delta": {"tool_calls": openai_tool_calls}, "finish_reason": None}
                            ],
                        }
                    )
                    continue

            content_list = msg.get("content")
            if isinstance(content_list, list) and content_list:
                first = content_list[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if isinstance(text, str) and text:
                        yield as_openai_sse_data(
                            {
                                "id": completion_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model_name,
                                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                            }
                        )
                        continue

        fr = obj.get("finishReason")
        if isinstance(fr, str) and fr:
            finish_reason = fr
            break

    yield as_openai_sse_data(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason or "stop"}],
        }
    )

    if include_usage and isinstance(usage_obj, dict):
        yield as_openai_sse_data(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
                "usage": {
                    "prompt_tokens": usage_obj.get("promptTokens", 0),
                    "completion_tokens": usage_obj.get("completionTokens", 0),
                    "total_tokens": usage_obj.get("totalTokens", 0),
                },
            }
        )

    yield "data: [DONE]\n\n"
