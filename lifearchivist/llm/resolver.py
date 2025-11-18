import re
from typing import Any, Dict, List

_PLACEHOLDER_RE = re.compile(r"^<from\s+([\w\-\.:/]+)(?:\s*\|\s*([^\>]+))?>$")

def _extract_doc_ids(upstream_payload: Dict[str, Any]) -> List[str]:
    """
    Standard path for your document_search tool:
      payload = {"documents": [{"document_id": "...", ...}, ...], ...}
    """
    docs = upstream_payload.get("documents") or []
    return [d.get("document_id") for d in docs if d.get("document_id")]

def resolve_params(params: Any, results_by_task: Dict[str, Dict[str, Any]], deps: List[str]) -> Any:
    """
    Recursively resolve placeholders like:
      "<from search_docs>"
      "<from search_docs | top_k=5>"
    into concrete values using upstream results.
    """
    if isinstance(params, dict):
        return {k: resolve_params(v, results_by_task, deps) for k, v in params.items()}

    if isinstance(params, list):
        out = []
        for v in params:
            rv = resolve_params(v, results_by_task, deps)
            # If a placeholder expands to a list, splice it in place
            if isinstance(rv, list) and any(isinstance(v, str) and _PLACEHOLDER_RE.match(v) for v in [v]):
                out.extend(rv)
            else:
                out.append(rv)
        return out

    if isinstance(params, str):
        m = _PLACEHOLDER_RE.match(params.strip())
        if not m:
            return params

        task_id, options = m.group(1), (m.group(2) or "").strip()
        if task_id not in results_by_task:
            raise ValueError(f"Dependency placeholder refers to unknown task_id '{task_id}'")

        upstream = results_by_task[task_id]

        # Support simple option: top_k
        top_k = None
        if options:
            for part in options.split(","):
                k, _, v = part.partition("=")
                if k.strip() == "top_k":
                    try: top_k = int(v.strip())
                    except: pass

        ids = _extract_doc_ids(upstream)
        if top_k is not None:
            ids = ids[:top_k]

        if not ids:
            # Bubble a clear error so the executor can fail the plan (or skip downstream)
            raise ValueError(f"No document_ids available from task '{task_id}'")

        return ids  # Let list splice logic expand it when present inside a list

    return params
