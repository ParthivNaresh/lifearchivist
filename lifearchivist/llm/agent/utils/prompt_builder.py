import json
from typing import Any, Dict, Iterable, List, Union

try:
    # optional import to type-hint tool objects; code works without it
    from ..tools.base import BaseAgentTool

    ToolLike = Union[Dict[str, Any], "BaseAgentTool"]
except Exception:
    ToolLike = Dict[str, Any]


class PromptBuilder:
    """
    Centralized, compact prompt templates for classification, planning, task execution, and synthesis.
    Prompts prefer small previews over full payloads to control token use.
    """

    # ------------ Complexity ------------
    def build_complexity_classification_prompt(
        self, *, query: str, context: Any = None
    ) -> str:
        # You can embed a tiny preview of context if you want; omitted here for brevity.
        return f"""You are a classifier that decides if a user query needs multi-step tool usage.

USER QUERY:
{query}

TASK:
Return strict JSON with keys:
- "complexity": "simple" | "complex"
- "confidence": number between 0 and 1
- "reasoning": brief string
- "estimated_steps": integer >= 1

Return ONLY JSON. No prose.
"""

    # ------------ Planning ------------
    def build_planning_prompt(
        self,
        *,
        query: str,
        context: Any,
        available_tools: Iterable[ToolLike],
        max_tasks: int = 20,
        cost_budget_usd: float = 1.0,
        time_budget_s: int = 300,
    ) -> str:
        tools_text = self._tools_as_text(available_tools)
        history_preview = self._preview(
            self._maybe_get(context, "recent_messages"), 1200
        )

        return f"""You are a planner for a multi-tool agent. Plan a DAG of tasks to answer the user's query.

USER QUERY:
{query}

RECENT CONVERSATION (preview):
{history_preview}

AVAILABLE TOOLS:
{tools_text}

CONSTRAINTS:
- Max tasks: {max_tasks}
- Cost budget (USD): {cost_budget_usd:.2f}
- Time budget (seconds): {time_budget_s}

OUTPUT:
Return STRICT JSON (no prose) matching this schema. Each task MUST include a unique, stable "task_id"; "depends_on" MUST reference these task_ids exactly.
{{
  "tasks": [
    {{
      "task_id": "string",
      "tool_name": "string",
      "description": "string",
      "requires_llm": true/false,
      "parameters": {{ ... }},
      "depends_on": ["task_id_1", "task_id_2"]
    }}
  ],
  "estimated_time_seconds": number,
  "estimated_cost_usd": number,
  "reasoning": "string"
}}
"""

    # ------------ Task (LLM-assisted tools) ------------
    def build_agent_prompt(self, *, task, tool, context: Dict[str, Any]) -> str:
        # Resolve a compact tool descriptor regardless of whether `tool` is an object or a dict-like
        desc = self._tool_descriptor(tool)
        tool_name = desc.get("name", "")
        tool_summary = desc.get("summary", "")

        dep_prev = self._preview(context.get("dependent_results"), 1200)
        hist_prev = self._preview(context.get("conversation_history"), 800)
        prefs_prev = self._preview(context.get("user_preferences"), 400)
        params_prev = self._preview(task.parameters, 800)

        return f"""You are assisting a tool invocation.

TOOL:
- name: {tool_name}
- summary: {tool_summary}

TASK DESCRIPTION:
{task.description}

DEPENDENT RESULTS (preview):
{dep_prev}

CONVERSATION HISTORY (preview):
{hist_prev}

USER PREFERENCES (preview):
{prefs_prev}

PARAMETERS (preview):
{params_prev}

INSTRUCTIONS:
- Produce only the output appropriate for the tool.
- Be precise and avoid fabricating information.
"""

    # ------------ Synthesis ------------
    def build_synthesis_prompt(
        self, *, query: str, plan, results: Dict[str, Any]
    ) -> str:
        plan_reasoning = getattr(plan, "reasoning", "")
        plan_prev = self._preview(plan_reasoning, 800)
        results_prev = self._preview(results, 2000)

        return f"""You are synthesizing a final answer for the user.

USER QUERY:
{query}

PLAN (brief):
{plan_prev}

TASK RESULTS (by task_id):
{results_prev}

Write a clear, concise answer grounded in the results. Use markdown when helpful.
Do not invent facts. If something is missing, state the limitation.
"""

    # ------------ Helpers ------------
    def _tools_as_text(self, tools: Iterable[ToolLike]) -> str:
        """
        Accepts either tool objects (with .descriptor()) or plain descriptors.
        Emits a compact, deterministic list.
        """
        lines: List[str] = []
        for tool in tools:
            d = self._tool_descriptor(tool)
            name = d.get("name", "")
            rllm = d.get("requires_llm", False)
            summary = d.get("summary") or ""
            schema = d.get("input_schema") or {}
            prop_keys = list(schema.get("properties", {}).keys())
            lines.append(
                f"- {name} (requires_llm={rllm}) — {summary} | params={prop_keys}"
            )
        return "\n".join(lines) if lines else "No tools available"

    def _tool_descriptor(self, tool: ToolLike) -> Dict[str, Any]:
        # If it looks like a dict/descriptor already, return it
        if isinstance(tool, dict):
            return {
                "name": tool.get("name", ""),
                "requires_llm": bool(tool.get("requires_llm", False)),
                "input_schema": tool.get("input_schema") or {},
                "summary": tool.get("summary") or "",
            }
        # Otherwise, assume a tool object
        if hasattr(tool, "descriptor"):
            try:
                return dict(tool.descriptor())
            except Exception:
                pass
        # Fallback: best-effort extract
        return {
            "name": getattr(tool, "name", ""),
            "requires_llm": bool(getattr(tool, "requires_llm", False)),
            "input_schema": getattr(tool, "input_schema", {}) or {},
            "summary": getattr(tool, "summary", "") or "",
        }

    def _preview(self, obj: Any, max_chars: int) -> str:
        try:
            # Try to be readable first; compact if too long
            s = json.dumps(obj, ensure_ascii=False, default=repr)
        except Exception:
            s = repr(obj)
        if len(s) > max_chars:
            return s[:max_chars] + "…"
        return s

    def _maybe_get(self, obj: Any, key: str) -> Any:
        try:
            if isinstance(obj, dict):
                return obj.get(key)
            # For dataclasses/objects
            return getattr(obj, key, None)
        except Exception:
            return None
