import json
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Union

if TYPE_CHECKING:
    from ..tools.base import BaseAgentTool

ToolLike = Union[Dict[str, Any], "BaseAgentTool"]


class PromptBuilderMixin:

    HISTORY_PREVIEW_CHARS: int = 1200
    COMPACT_HISTORY_PREVIEW_CHARS: int = 800
    PARAMS_PREVIEW_CHARS: int = 800
    PREFS_PREVIEW_CHARS: int = 400
    DEP_RESULTS_PREVIEW_CHARS: int = 1200

    @staticmethod
    def preview(obj: Any, max_chars: int) -> str:
        try:
            s = json.dumps(obj, ensure_ascii=False, default=repr)
        except Exception:
            s = repr(obj)
        if len(s) > max_chars:
            return s[:max_chars] + "…"
        return s

    @staticmethod
    def maybe_get(obj: Any, key: str) -> Any:
        try:
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)
        except Exception:
            return None

    @staticmethod
    def tool_descriptor(tool: ToolLike) -> Dict[str, Any]:
        if isinstance(tool, dict):
            return {
                "name": tool.get("name", ""),
                "requires_llm": bool(tool.get("requires_llm", False)),
                "input_schema": tool.get("input_schema") or {},
                "summary": tool.get("summary") or "",
            }
        if hasattr(tool, "descriptor"):
            try:
                return dict(tool.descriptor())
            except Exception:
                pass
        return {
            "name": getattr(tool, "name", ""),
            "requires_llm": bool(getattr(tool, "requires_llm", False)),
            "input_schema": getattr(tool, "input_schema", {}) or {},
            "summary": getattr(tool, "summary", "") or "",
        }

    @classmethod
    def tools_as_text(cls, tools: Iterable[ToolLike], *, compact: bool = False) -> str:
        lines: List[str] = []
        for tool in tools:
            d = cls.tool_descriptor(tool)
            name = d.get("name", "")
            rllm = d.get("requires_llm", False)

            if compact:
                summary = d.get("summary_short") or (d.get("summary") or "")[:140]
                priority_params = d.get("priority_params", [])

                if not priority_params:
                    schema = d.get("input_schema") or {}
                    required = schema.get("required", [])
                    props = schema.get("properties", {})
                    priority_params = (
                        required[:4] if required else list(props.keys())[:4]
                    )

                params_str = ", ".join(priority_params[:4])
                if len(priority_params) > 4:
                    params_str += ", ..."

                line = f"- {name} (llm={str(rllm).lower()}): {summary}"
                if params_str:
                    line += f" | {params_str}"
            else:
                summary = d.get("summary") or ""
                schema = d.get("input_schema") or {}
                prop_keys = list(schema.get("properties", {}).keys())
                line = (
                    f"- {name} (requires_llm={rllm}) — {summary} | params={prop_keys}"
                )

            lines.append(line)

        return "\n".join(lines) if lines else "No tools available"

    @classmethod
    def format_history_preview(cls, context: Any, compact: bool = False) -> str:
        max_chars = (
            cls.COMPACT_HISTORY_PREVIEW_CHARS if compact else cls.HISTORY_PREVIEW_CHARS
        )
        return cls.preview(cls.maybe_get(context, "recent_messages"), max_chars)


BasePromptBuilder = PromptBuilderMixin
