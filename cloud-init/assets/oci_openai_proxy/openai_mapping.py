import json
from typing import Any, Dict, List, Optional


def openai_messages_to_single_user_prompt(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for m in messages:
        role = (m.get("role") or "user").upper()
        content = m.get("content", "")
        if isinstance(content, list):
            text_bits = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    text_bits.append(c.get("text", ""))
            content = "\n".join(text_bits)
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def parse_openai_tools_to_oci_generic_tools(tools: Any) -> Optional[List[Dict[str, Any]]]:
    if tools is None:
        return None
    if not isinstance(tools, list):
        raise ValueError("tools must be an array")

    oci_tools: List[Dict[str, Any]] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        if t.get("type") != "function":
            continue
        fn = t.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        desc = fn.get("description")
        if desc is not None and not isinstance(desc, str):
            desc = str(desc)
        params = fn.get("parameters")
        if params is None:
            params = {"type": "object", "properties": {}}
        if not isinstance(params, dict):
            raise ValueError(f"tool {name} function.parameters must be an object")

        oci_tools.append(
            {
                "type": "FUNCTION",
                "name": name.strip(),
                "description": (desc or "").strip(),
                "parameters": params,
            }
        )

    return oci_tools


def parse_openai_tool_choice_to_oci_tool_choice(tool_choice: Any) -> Optional[Dict[str, Any]]:
    if tool_choice is None:
        return None

    if isinstance(tool_choice, str):
        tc = tool_choice.strip().lower()
        if tc == "auto":
            return {"type": "AUTO"}
        if tc == "none":
            return {"type": "NONE"}
        if tc == "required":
            return {"type": "REQUIRED"}
        raise ValueError("tool_choice must be one of auto|none|required or a function selector")

    if isinstance(tool_choice, dict):
        if tool_choice.get("type") == "function":
            fn = tool_choice.get("function")
            if not isinstance(fn, dict):
                raise ValueError("tool_choice.function must be an object")
            name = fn.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("tool_choice.function.name is required")
            return {"type": "FUNCTION", "name": name.strip()}

        ttype = tool_choice.get("type")
        if isinstance(ttype, str) and ttype.upper() in ("AUTO", "NONE", "REQUIRED", "FUNCTION"):
            out = {"type": ttype.upper()}
            if out["type"] == "FUNCTION":
                name = tool_choice.get("name")
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("tool_choice.name is required when type=FUNCTION")
                out["name"] = name.strip()
            return out

    raise ValueError("tool_choice must be a string or object")


def openai_messages_to_oci_generic_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for m in messages:
        if not isinstance(m, dict):
            continue

        role = m.get("role")
        if not isinstance(role, str):
            role = "user"
        role_l = role.lower().strip()

        if role_l == "tool":
            tool_call_id = m.get("tool_call_id")
            if not isinstance(tool_call_id, str) or not tool_call_id.strip():
                tool_call_id = m.get("toolCallId")
            if not isinstance(tool_call_id, str) or not tool_call_id.strip():
                raise ValueError("tool message must include tool_call_id")

            content = m.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content)

            out.append(
                {
                    "role": "TOOL",
                    "toolCallId": tool_call_id.strip(),
                    "content": [{"type": "TEXT", "text": content}],
                }
            )
            continue

        if role_l == "system":
            oci_role = "SYSTEM"
        elif role_l == "developer":
            oci_role = "DEVELOPER"
        elif role_l == "assistant":
            oci_role = "ASSISTANT"
        else:
            oci_role = "USER"

        content = m.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            bits: List[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("text", "TEXT"):
                    t = part.get("text")
                    if isinstance(t, str):
                        bits.append(t)
            text = "\n".join(bits)
        else:
            text = json.dumps(content)

        msg_obj: Dict[str, Any] = {"role": oci_role, "content": [{"type": "TEXT", "text": text}]}

        # Pass assistant tool_calls back to OCI if present (tool loop)
        if role_l == "assistant":
            tool_calls = m.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                oci_tool_calls: List[Dict[str, Any]] = []
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    if tc.get("type") != "function":
                        continue
                    fn = tc.get("function")
                    if not isinstance(fn, dict):
                        continue
                    name = fn.get("name")
                    args = fn.get("arguments")
                    if not isinstance(name, str) or not name.strip():
                        continue
                    if args is None:
                        args = "{}"
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    oci_tool_calls.append(
                        {
                            "type": "FUNCTION",
                            "name": name.strip(),
                            "arguments": args,
                            "id": tc.get("id") if isinstance(tc.get("id"), str) else None,
                        }
                    )
                if oci_tool_calls:
                    msg_obj["toolCalls"] = [x for x in oci_tool_calls if x.get("name")]

        out.append(msg_obj)

    return out
