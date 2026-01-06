import json
from typing import TYPE_CHECKING, Any, Dict

from ....utils.logx import log_event
from .base import BasePromptBuilder

if TYPE_CHECKING:
    from ..models.task import ExecutionPlan


class SynthesisPromptBuilder(BasePromptBuilder):

    BYTE_BUDGET: int = 20_000

    @classmethod
    def build(
        cls,
        query: str,
        plan: "ExecutionPlan",
        results: Dict[str, Any],
    ) -> str:
        plan_brief = getattr(plan, "reasoning", "") or ""
        compacted_results = cls._compact_results(results)

        task_results_json = json.dumps(
            compacted_results, ensure_ascii=False, default=str
        )

        log_event(
            "synthesis_prompt_compacted",
            {
                "task_count": len(results or {}),
                "included_tasks": list(compacted_results.keys()),
                "prompt_preview": task_results_json[:6000],
            },
        )

        return (
            "You are synthesizing a final answer for the user.\n\n"
            f"USER QUERY:\n{query}\n\n"
            "PLAN (brief):\n"
            f"{plan_brief}\n\n"
            "TASK RESULTS (by task_id):\n"
            f"{task_results_json}\n"
            "\nRespond clearly and concisely. Prefer grounded facts from the task results."
        )

    @classmethod
    def _compact_results(cls, results: Dict[str, Any]) -> Dict[str, Any]:
        from ..utils.parsing import sanitize_tool_output

        compacted_results: Dict[str, Any] = {}

        for tid, payload in (results or {}).items():
            log_event("------------------------------------------------")
            log_event(tid)
            log_event(payload)
            try:
                val = payload
                if isinstance(val, dict) and "value" in val and len(val) == 1:
                    val = val["value"]

                if tid == "search_docs":
                    val = sanitize_tool_output(val)

                compacted_value = cls._compact_for_synthesis(tid, val)

                if isinstance(compacted_value, str) and isinstance(val, dict):
                    safe: Dict[str, Any] = {}
                    for k, v in val.items():
                        if k == "documents" and isinstance(v, list):
                            safe["documents"] = v[:5]
                        elif isinstance(v, str):
                            safe[k] = v[:600]
                        else:
                            safe[k] = v
                    compacted_value = safe

                compacted_results[tid] = compacted_value

            except Exception:
                compacted_results[tid] = str(payload)[:20000] + "…"

        return compacted_results

    @classmethod
    def _compact_for_synthesis(
        cls, task_id: str, value: Any, byte_budget: int = 20_000
    ) -> Any:
        v = value

        if isinstance(v, dict) and "value" in v and len(v) == 1:
            v = v["value"]

        if isinstance(v, dict) and "extractions" in v:
            v = v.copy()
            v["extractions"] = cls._maybe_parse_json_string(v.get("extractions"))

        if isinstance(v, list):
            v = {"extractions": v, "provenance": []}

        if cls._approx_json_size(v) <= byte_budget:
            return v

        if isinstance(v, dict) and "extractions" in v:
            v = v.copy()
            ex = cls._maybe_parse_json_string(v.get("extractions"))
            if isinstance(ex, list):
                ex = ex[:5]
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

            if "provenance" in v and isinstance(v["provenance"], list):
                v["provenance"] = v["provenance"][:10]

            if cls._approx_json_size(v) <= byte_budget:
                return v

        s = str(v)
        if len(s) > byte_budget:
            s = s[:byte_budget] + "…"
        return s

    @staticmethod
    def _maybe_parse_json_string(x: Any) -> Any:
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

    @staticmethod
    def _approx_json_size(obj: Any) -> int:
        try:
            return len(json.dumps(obj, ensure_ascii=False, default=str))
        except Exception:
            return len(str(obj))
