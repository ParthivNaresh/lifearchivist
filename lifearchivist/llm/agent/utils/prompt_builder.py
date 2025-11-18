import json
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Union

from ....utils.logx import log_event

if TYPE_CHECKING:
    ToolLike = Union[Dict[str, Any], "BaseAgentTool"]
else:
    ToolLike = Union[Dict[str, Any], Any]


def _json_preview(obj, limit: int = 800) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    # only slice strings
    return s[:limit]


def _maybe_parse_json_string(x: Any) -> Any:
    """If x looks like a JSON string, parse it; otherwise return x unchanged."""
    if isinstance(x, str):
        s = x.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
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
                    for k, val in list(item.items()):
                        if isinstance(val, str) and len(val) > 500:
                            item[k] = val[:500] + "…"
                        elif isinstance(val, dict):
                            for rk, rv in list(val.items()):
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
        return f"""You are a classifier that decides whether a user query requires a single-step response (simple)
or multi-step reasoning or tool usage (complex).

Definitions:
- "simple" → can be answered directly with text or a single retrieval of facts.
- "complex" → needs planning, multiple steps, API/tool calls, or reasoning beyond retrieval (e.g., data analysis, code, long reasoning chains).

Return ONLY strict JSON with:
{{
  "complexity": "simple" | "complex",
  "confidence": float (0–1),
  "reasoning": short string (max 20 words),
  "estimated_steps": integer >= 1
}}

Examples:
1. Query: "Who is the CEO of Apple?"
   → {{ "complexity": "simple", "confidence": 0.95, "reasoning": "single fact lookup", "estimated_steps": 1 }}

2. Query: "Summarize these three documents and generate a recommendation."
   → {{ "complexity": "complex", "confidence": 0.93, "reasoning": "multi-doc analysis and synthesis", "estimated_steps": 3 }}

3. Query: "Write Python code that plots sales by region."
   → {{ "complexity": "complex", "confidence": 0.9, "reasoning": "requires code generation", "estimated_steps": 2 }}

4. Query: "What time is it in Tokyo?"
   → {{ "complexity": "simple", "confidence": 0.9, "reasoning": "single lookup", "estimated_steps": 1 }}

USER QUERY:
{query}

Output only the JSON object, nothing else.
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
        history_preview = self._preview(self._maybe_get(context, "recent_messages"), 1200)

        return f"""You are a planner for a multi-tool agent. Plan a DAG of tasks to answer the user's query.
    
    USER QUERY:
    {query}
    
    RECENT CONVERSATION (preview):
    {history_preview}
    
    AVAILABLE TOOLS:
    {tools_text}
    
    CRITICAL RULES:
    1) ONLY use tools from the AVAILABLE TOOLS list above.
    2) Each task MUST have a valid "tool_name" from the list.
    3) Do NOT invent tools that don't exist; do NOT leave tool_name empty.
    4) Respect tool contracts:
       - If a tool states it REQUIRES LLM, set "requires_llm": true on that task.
       - If a tool does not require LLM, you may set true or false based on need.
    5) All parameters MUST match the tool's expected input schema.
    6) All dependencies MUST form a DAG (no cycles).
    
    DEPENDENCY BINDING SYNTAX (VERY IMPORTANT):
    - To pass outputs from an upstream task into a downstream task parameter, use a placeholder:
        "<from TASK_ID>"
    - You may optionally limit how many items you take from the upstream result:
        "<from TASK_ID | top_k=N>"
    - The placeholder MUST exactly match one of the above forms.
    - If you use "<from TASK_ID...>", then TASK_ID MUST appear in "depends_on" for that task.
    - Do NOT use any other templating or variable syntax.
    
    TOOL PARAMETER CHEATSHEET (follow exactly):
    - document_search (LLM-only):
        - requires_llm: true
        - parameters:
            {{
              "query": string,
              "search_method": "hybrid" | "semantic" | "keyword" | "metadata",
              "top_k": integer (1-100),
              "similarity_threshold": float (0..1)   // optional, recommended
              "semantic_weight": float (0..1)        // optional, recommended for hybrid
              "mime_types": [string]?,
              "themes": [string]?,
              "date_filter": {{"after": "YYYY-MM-DD"?, "before": "YYYY-MM-DD"?"}}?,
              "status": string?,
              "include_metadata": true/false?,
              "include_text_preview": true/false?,
              "instructions": string?,               // guidance to the search agent
              "model": string?                       // optional model hint
            }}
    
    - data_extraction:
        - requires_llm: true (recommended)
        - parameters:
            {{
              "document_ids": ["<from SEARCH_TASK_ID>" | "<from SEARCH_TASK_ID | top_k=N>", ...]  // usually one placeholder list
              "fields": [string, ...],
              "max_total_chars": integer?,      // optional safety cap
              "max_chunks_per_doc": integer?,   // optional per-doc cap
              "model": string?                  // optional model hint
            }}
    
    CONSTRAINTS:
    - Max tasks: {max_tasks}
    - Cost budget: ${cost_budget_usd:.2f}
    - Time budget: {time_budget_s}s
    
    EXAMPLE - Document Search (LLM) + Extraction:
    {{
      "tasks": [
        {{
          "task_id": "search_docs",
          "tool_name": "document_search",
          "description": "Find relevant blood test documents",
          "requires_llm": true,
          "parameters": {{
            "query": "blood test",
            "search_method": "hybrid",
            "top_k": 5,
            "similarity_threshold": 0.3,
            "semantic_weight": 0.6,
            "instructions": "Prefer recent lab reports; exclude appointment reminders."
          }},
          "depends_on": []
        }},
        {{
          "task_id": "extract_data",
          "tool_name": "data_extraction",
          "description": "Extract test_type, date, results from the retrieved documents",
          "requires_llm": true,
          "parameters": {{
            "document_ids": ["<from search_docs>"],
            "fields": ["test_type", "date", "results"],
            "max_total_chars": 200000,
            "max_chunks_per_doc": 100
          }},
          "depends_on": ["search_docs"]
        }}
      ],
      "estimated_time_seconds": 45,
      "estimated_cost_usd": 0.02,
      "reasoning": "Search first with LLM-chosen strategy; then extract structured fields with provenance."
    }}
    
    OUTPUT FORMAT:
    Return STRICT JSON (no markdown, no prose) matching this schema:
    {{
      "tasks": [
        {{
          "task_id": "unique_id",
          "tool_name": "MUST be from AVAILABLE TOOLS list",
          "description": "what this task does",
          "requires_llm": true/false,
          "parameters": {{}},
          "depends_on": ["other_task_ids"]
        }}
      ],
      "estimated_time_seconds": number,
      "estimated_cost_usd": number,
      "reasoning": "brief explanation"
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
        plan_brief = getattr(plan, "reasoning", "") or ""
        # compact each task payload; never drop entire tasks
        compacted_results: Dict[str, Any] = {}
        for tid, payload in (results or {}).items():
            try:
                compacted_results[tid] = _compact_for_synthesis(tid, payload)
            except Exception:
                compacted_results[tid] = (str(payload)[:20000] + "…")

        task_results_json = json.dumps(compacted_results, ensure_ascii=False, default=str)

        log_event(
            "synthesis_prompt_compacted",
            {
                "task_count": len(results or {}),
                "included_tasks": list(compacted_results.keys()),
                "avg_task_size_bytes": int(sum(len(json.dumps(v, ensure_ascii=False, default=str)) for v in compacted_results.values()) / max(1, len(compacted_results))),
                "prompt_len": len(task_results_json),
                "prompt_preview": task_results_json[:600],
            },
        )

        # build your final prompt text (keep your existing verbiage)
        return (
            "You are synthesizing a final answer for the user.\n\n"
            f"USER QUERY:\n{query}\n\n"
            "PLAN (brief):\n"
            f"{plan_brief}\n\n"
            "TASK RESULTS (by task_id):\n"
            f"{task_results_json}\n"
            "\nRespond clearly and concisely. Prefer grounded facts from the task results."
        )

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
