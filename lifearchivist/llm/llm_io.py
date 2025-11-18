import json
from typing import Any, Optional

class _LlmCallError(RuntimeError): ...

def _unwrap_result_or_raise(result) -> Any:
    if hasattr(result, "is_failure") and result.is_failure():
        err = result.unwrap_error()
        raise _LlmCallError(str(err))
    return result.unwrap() if hasattr(result, "unwrap") else result

def _response_text(resp: Any) -> str:
    # Your LLMResponse has .content. Fall back to str if needed.
    for attr in ("content", "text"):
        if hasattr(resp, attr) and getattr(resp, attr) is not None:
            return getattr(resp, attr)
    return str(resp)

def _parse_json_maybe(s: str) -> Optional[Any]:
    s = (s or "").strip()
    try:
        return json.loads(s)
    except Exception:
        return None
