import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, cast

from ..constants import MAX_JSON_CHARS


class _LlmCallError(RuntimeError): ...


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"^```(?:json|JSON)?\s*|\s*```$", re.MULTILINE)
_PLACEHOLDER_PATTERN = re.compile(r"<from\s+[\w\-\.:/]+")
_HEAVY_KEYS = {
    "_node_content",
    "_node_text",
    "embedding",
    "vector",
    "content_bytes",
    "text_preview",
}
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]")
_EXCESSIVE_WHITESPACE_RE = re.compile(r"[ \t]+")
_EXCESSIVE_NEWLINES_RE = re.compile(r"\n{3,}")


def _safe_preview(value: Any, max_chars: int = 1200) -> str:
    try:
        s = repr(value)
    except Exception:
        s = "<unrepr>"
    if len(s) > max_chars:
        return s[:max_chars] + "…"
    return s


def _json_preview(obj, limit: int = 800) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    # only slice strings
    return s[:limit]


def _parse_json_object_lenient(raw: Any) -> Any:
    """
    Best-effort JSON object parser:
    - accept str; strip code fences
    - try json.loads directly
    - fallback: extract first {...} block and parse
    Returns dict on success; list on success (if top-level array); None otherwise.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip()

    # Strip ```json fences if present
    s = _CODE_FENCE_RE.sub("", s).strip()

    # Try direct parse first
    try:
        return json.loads(s)
    except Exception:
        pass

    # Fallback: extract the first balanced-looking {...}
    m = _JSON_OBJECT_RE.search(s)
    if m:
        snippet = m.group(0)
        try:
            return json.loads(snippet)
        except Exception:
            pass

    # If it starts with '[' try parsing list
    if s.startswith("["):
        try:
            return json.loads(s)
        except Exception:
            pass

    # If the LLM responded without structured output, just create a json
    return json.loads(json.dumps({"response": s}))


def _maybe_parse_json_string(x: Any) -> Any:
    """If x looks like a JSON string, parse it; otherwise return x unchanged."""
    if isinstance(x, str):
        s = x.strip()
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):
            try:
                return json.loads(s)
            except Exception:
                return x
    return x


def _approx_json_size(obj: Any) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception:
        return len(str(obj))


def _compact_for_synthesis(task_id: str, value: Any, byte_budget: int = 20_000) -> Any:
    """
    Keep every task; compact large payloads (esp. extraction output) instead of dropping them.
    - Parse stringified JSON if present (extractions often arrive as a string).
    - Normalize top-level arrays to objects.
    - Clip long lists and long strings; trim provenance lists.
    """
    v = value

    # Common case: ResultEnvelope wrapper
    if isinstance(v, dict) and "value" in v and len(v) == 1:
        v = v["value"]

    # If tool stashed model output under 'extractions' as a string, parse it
    if isinstance(v, dict) and "extractions" in v:
        v = v.copy()
        v["extractions"] = _maybe_parse_json_string(v.get("extractions"))

    # If we got a top-level array, normalize into expected object shape
    if isinstance(v, list):
        v = {"extractions": v, "provenance": []}

    if _approx_json_size(v) <= byte_budget:
        return v

    # Compact extraction payloads responsibly
    if isinstance(v, dict) and "extractions" in v:
        v = v.copy()
        ex = _maybe_parse_json_string(v.get("extractions"))
        if isinstance(ex, list):
            # keep first few items
            ex = ex[:5]
            # clip long fields
            for item in ex:
                if isinstance(item, dict):
                    for k, val in item.items():
                        if isinstance(val, str) and len(val) > 500:
                            item[k] = val[:500] + "…"
                        elif isinstance(val, dict):
                            for rk, rv in val.items():
                                if isinstance(rv, str) and len(rv) > 300:
                                    val[rk] = rv[:300] + "…"
        v["extractions"] = ex

        # trim provenance
        if "provenance" in v and isinstance(v["provenance"], list):
            v["provenance"] = v["provenance"][:10]

        if _approx_json_size(v) <= byte_budget:
            return v

    # Last resort: stringify and clip but NEVER drop the whole task
    s = str(v)
    if len(s) > byte_budget:
        s = s[:byte_budget] + "…"
    return s


def _approx_size(obj: Any) -> int:
    """Best-effort, cheap size heuristic in bytes."""
    try:
        return len(repr(obj).encode("utf-8"))
    except Exception:
        return 0


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


def _sanitize_search_result_doc(d: dict) -> dict:
    """Keep useful fields; drop heavy/internal ones from metadata & limit previews."""
    out = {
        "document_id": d.get("document_id"),
        "score": d.get("score"),
        "search_type": d.get("search_type"),
    }
    md = d.get("metadata") or {}
    if isinstance(md, dict):
        md2 = {}
        for k, v in md.items():
            if k in _HEAVY_KEYS:
                continue
            if k in ("title", "mime_type", "status", "uploaded_date", "document_id"):
                md2[k] = v
        if md2:
            out["metadata"] = md2
    return out


def _sanitize_documents_list(
    docs: List[Any], *, max_docs: Optional[int] = None
) -> list[Any]:
    """Sanitize a list of document search results, optionally truncating length."""
    items = docs if max_docs is None else docs[:max_docs]
    out: list[Any] = []
    for d in items:
        out.append(_sanitize_search_result_doc(d) if isinstance(d, dict) else d)
    return out


def _deep_sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        sanitized: dict[str, Any] = {}
        for k, v in obj.items():
            if k in _HEAVY_KEYS:
                continue
            sanitized[k] = _deep_sanitize(v)
        return sanitized
    if isinstance(obj, list):
        return [_deep_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_deep_sanitize(v) for v in obj)
    return obj


def clean_extracted_text(text: str, *, normalize_unicode: bool = True) -> str:
    """
    Clean extracted text by removing control characters, null bytes, and normalizing whitespace.

    Removes:
    - Null bytes (\x00) and other control characters
    - Non-printable characters in ranges \x00-\x1f and \x7f-\x9f (except \t, \n, \r)
    - Excessive whitespace and newlines

    Preserves:
    - Meaningful whitespace (single spaces, tabs, newlines)
    - All printable Unicode characters
    - Text structure and readability

    Args:
        text: Raw extracted text that may contain unwanted characters
        normalize_unicode: If True, applies NFC normalization for consistent Unicode representation

    Returns:
        Cleaned text suitable for LLM processing
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    if not text:
        return ""

    cleaned = _CONTROL_CHAR_RE.sub("", text)

    if normalize_unicode:
        try:
            cleaned = unicodedata.normalize("NFC", cleaned)
        except (ValueError, TypeError):
            pass

    cleaned = _EXCESSIVE_WHITESPACE_RE.sub(" ", cleaned)
    cleaned = _EXCESSIVE_NEWLINES_RE.sub("\n\n", cleaned)

    return cleaned.strip()


def clean_extraction_chunks(
    chunks: List[dict[str, str]],
    *,
    text_key: str = "text",
    normalize_unicode: bool = True,
    skip_empty: bool = True,
) -> List[dict[str, str]]:
    """
    Clean a list of extraction chunks by sanitizing text content while preserving structure.

    Designed for chunks in format: [{'doc_id': '...', 'text': '...'}, ...]

    Args:
        chunks: List of chunk dictionaries containing text to clean
        text_key: Key name for the text field to clean (default: "text")
        normalize_unicode: If True, applies Unicode normalization
        skip_empty: If True, filters out chunks with empty text after cleaning

    Returns:
        List of cleaned chunks with same structure as input
    """
    if not isinstance(chunks, list):
        return []

    cleaned_chunks: List[dict[str, str]] = []

    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        cleaned_chunk = dict(chunk)

        if text_key in cleaned_chunk:
            original_text = cleaned_chunk[text_key]
            cleaned_text = clean_extracted_text(
                original_text, normalize_unicode=normalize_unicode
            )

            if skip_empty and not cleaned_text:
                continue

            cleaned_chunk[text_key] = cleaned_text

        cleaned_chunks.append(cleaned_chunk)

    return cleaned_chunks


def sanitize_tool_output(
    value: Any, *, max_docs: Optional[int] = None, deep: bool = True
) -> Any:
    """
    Sanitize a tool output by removing heavy keys and applying structure-aware
    filtering (e.g., document_search). If max_docs is set, caps documents length.
    If deep is True, recursively strips _HEAVY_KEYS everywhere.
    """
    try:
        v = value
        if isinstance(v, dict):
            if isinstance(v.get("documents"), list):
                v = dict(v)
                v["documents"] = _sanitize_documents_list(
                    v["documents"], max_docs=max_docs
                )
            return _deep_sanitize(v) if deep else v
        if isinstance(v, (list, tuple)):
            return _deep_sanitize(v) if deep else v
        return v
    except Exception:
        return value


def extract_json_from_markdown(s: str) -> str:
    s = s.strip()

    if s.startswith("```"):
        lines = s.split("\n")

        if lines[0].strip() in ("```", "```json", "```JSON"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        s = "\n".join(lines).strip()

    return s


def json_loads_strict(
    s: str,
    *,
    allow_list: bool = False,
    list_wrapper_key: str = "tasks",
) -> Dict[str, Any]:
    if len(s) > MAX_JSON_CHARS:
        raise ValueError(f"LLM JSON exceeds {MAX_JSON_CHARS} chars")

    s_clean = extract_json_from_markdown(s)

    try:
        parsed = json.loads(s_clean)

        if isinstance(parsed, dict):
            return cast(Dict[str, Any], parsed)

        if allow_list and isinstance(parsed, list):
            return {
                list_wrapper_key: parsed,
                "estimated_time_seconds": 0,
                "estimated_cost_usd": 0.0,
                "reasoning": "LLM returned list directly without wrapper object",
            }

        expected = "dict or list" if allow_list else "dict"
        raise ValueError(f"Expected {expected}, got {type(parsed).__name__}")

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON decode error at pos {e.pos}: {e.msg}") from e
