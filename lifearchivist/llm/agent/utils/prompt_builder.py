import json
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union

from ....utils.logx import log_event
from .parsing import _compact_for_synthesis, sanitize_tool_output

if TYPE_CHECKING:
    from ..tools.base import BaseAgentTool

    ToolLike = Union[Dict[str, Any], "BaseAgentTool"]
else:
    ToolLike = Union[Dict[str, Any], Any]


# TODO: REFACTOR CLASS TO STATIC METHODS
class PromptBuilder:
    """
    Centralized, compact prompt templates for classification, planning, task execution, and synthesis.
    Prompts prefer small previews over full payloads to control token use.
    """

    # ------------ Strategic Planning ------------
    def build_strategic_planning_prompt(
        self,
        *,
        query: str,
        context: Any,
        available_tools: Iterable[ToolLike],
        max_phases: int = 7,
    ) -> str:
        tools_text = self._tools_as_text(available_tools, compact=True)
        history_preview = self._preview(
            self._maybe_get(context, "recent_messages"), 800
        )

        return f"""You are a strategic planner for a multi-tool agent system. Your job is to break down complex user queries into high-level phases.

USER QUERY:
{query}

RECENT CONVERSATION (preview):
{history_preview}

AVAILABLE TOOLS (short descriptions):
{tools_text}

YOUR TASK:
Analyze the user's query and create a strategic plan consisting of 3-7 high-level phases. Each phase represents a major step toward completing the user's request.

PHASE DESIGN PRINCIPLES:
1. Each phase should be a cohesive unit of work (e.g., "discover documents", "extract data", "generate report")
2. Phases should have clear dependencies (which phases must complete before this one starts)
3. Assign required_tools to each phase (which tools from the AVAILABLE TOOLS list are needed)
4. Estimate complexity: "simple" (1-3 tasks), "medium" (4-8 tasks), "complex" (9+ tasks)
5. Keep phases coarse-grained - detailed task planning happens later

COMPLEXITY GUIDELINES:
- "simple": Single tool, straightforward operation (e.g., search documents)
- "medium": Multiple tool calls or moderate data processing (e.g., extract from multiple docs)
- "complex": Many iterations, large data volumes, or sophisticated logic (e.g., aggregate 50+ documents)

TOOL ASSIGNMENT:
- List tool names that will be needed in this phase
- Be inclusive - if a tool might be needed, include it
- Tools will be filtered more precisely in detailed planning

CONSTRAINTS:
- Max phases: {max_phases}
- Phase IDs must be lowercase with underscores (e.g., "discover_docs", "extract_data")
- Dependencies must form a DAG (no cycles)

EXAMPLE 1 - Simple Query ("Organize my blood tests"):
{{
  "strategy": "Search for blood test documents and extract key information",
  "phases": [
    {{
      "phase_id": "search_documents",
      "description": "Find all blood test related documents",
      "required_tools": ["document_search"],
      "depends_on": [],
      "estimated_complexity": "simple"
    }},
    {{
      "phase_id": "extract_results",
      "description": "Extract test results, dates, and values from documents",
      "required_tools": ["structured_extraction"],
      "depends_on": ["search_documents"],
      "estimated_complexity": "medium"
    }}
  ]
}}

EXAMPLE 2 - Complex Query ("Build financial health presentation"):
{{
  "strategy": "Multi-phase financial analysis: discover documents, extract data from different sources, aggregate, and generate presentation",
  "phases": [
    {{
      "phase_id": "discover_financial_docs",
      "description": "Search for all financial documents (bank statements, brokerage, tax docs)",
      "required_tools": ["document_search"],
      "depends_on": [],
      "estimated_complexity": "simple"
    }},
    {{
      "phase_id": "extract_banking_data",
      "description": "Extract transaction data, balances, and trends from bank statements",
      "required_tools": ["structured_extraction", "text_extraction"],
      "depends_on": ["discover_financial_docs"],
      "estimated_complexity": "complex"
    }},
    {{
      "phase_id": "extract_investment_data",
      "description": "Extract portfolio data, returns, and holdings from brokerage statements",
      "required_tools": ["structured_extraction", "text_extraction"],
      "depends_on": ["discover_financial_docs"],
      "estimated_complexity": "complex"
    }},
    {{
      "phase_id": "aggregate_financial_data",
      "description": "Combine and analyze all financial data to compute net worth, trends, insights",
      "required_tools": ["structured_extraction"],
      "depends_on": ["extract_banking_data", "extract_investment_data"],
      "estimated_complexity": "medium"
    }},
    {{
      "phase_id": "generate_presentation",
      "description": "Create presentation with charts, summaries, and recommendations",
      "required_tools": ["text_extraction"],
      "depends_on": ["aggregate_financial_data"],
      "estimated_complexity": "medium"
    }}
  ]
}}

OUTPUT FORMAT:
Return STRICT JSON (no markdown, no prose) matching this schema:
{{
  "strategy": "brief description of overall approach",
  "phases": [
    {{
      "phase_id": "unique_lowercase_id",
      "description": "what this phase accomplishes",
      "required_tools": ["tool_name1", "tool_name2"],
      "depends_on": ["other_phase_ids"],
      "estimated_complexity": "simple" | "medium" | "complex"
    }},
    ...
  ]
}}
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
    ) -> str:
        tools_text = self._tools_as_text(available_tools)
        history_preview = self._preview(
            self._maybe_get(context, "recent_messages"), 1200
        )

        has_provided_doc_ids = "DOCUMENT IDS FROM PREVIOUS PHASES" in query

        base_prompt = f"""You are a planner for a multi-tool agent. Plan a DAG of tasks to answer the user's query.

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
7) "depends_on" MUST ONLY reference task_ids defined in THIS PLAN - never reference external IDs or phase names.
"""

        if has_provided_doc_ids:
            base_prompt += """
IMPORTANT - DOCUMENT IDS ALREADY PROVIDED:
The query above contains "DOCUMENT IDS FROM PREVIOUS PHASES" with actual document IDs.
- Use these document IDs DIRECTLY in the "document_ids" parameter as a literal array of strings.
- Do NOT use "<from ...>" placeholder syntax for these IDs.
- Do NOT add any "depends_on" entries for these IDs - they are already resolved.
- Example: "document_ids": ["abc123", "def456"] (use the actual IDs from the query)

"""
        else:
            base_prompt += """
DEPENDENCY BINDING SYNTAX (for multi-task plans):
- To pass outputs from an upstream task INTO a downstream task parameter, use a placeholder:
    "<from TASK_ID>"
- You may optionally limit how many items you take from the upstream result:
    "<from TASK_ID | top_k=N>"
- The placeholder MUST exactly match one of the above forms.
- If you use "<from TASK_ID...>", then TASK_ID MUST appear in "depends_on" for that task.
- Do NOT use any other templating or variable syntax.

CRITICAL - document_ids MUST BE AN ARRAY:
- When using "<from TASK_ID>" for document_ids, it MUST be inside an array: ["<from TASK_ID>"]
- WRONG: "document_ids": "<from search_docs>"
- CORRECT: "document_ids": ["<from search_docs>"]

"""

        base_prompt += f"""TOOL PARAMETER CHEATSHEET (follow exactly):
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

- structured_extraction:
    - requires_llm: true (recommended)
    - parameters:
        {{
          "document_ids": [string, ...]         // array of document ID strings
          "fields": [string, ...],
          "max_total_chars": integer?,      // optional safety cap
          "max_chunks_per_doc": integer?,   // optional per-doc cap
          "model": string?                  // optional model hint
        }}

- text_extraction:
    - requires_llm: true
    - parameters:
        {{
          "document_ids": [string, ...]         // array of document ID strings
          "instructions": string,           // what to extract/summarize
          "style": "concise" | "detailed" | "bullet_points" | "narrative" | "technical" | "executive",
          "focus": "overview" | "key_points" | "insights" | "recommendations" | "analysis" | "comparison"?,
          "max_output_length": integer?,    // target word count
          "include_citations": true/false?, // include document references
          "model": string?                  // optional model hint
        }}

CONSTRAINTS:
- Max tasks: {max_tasks}
"""

        if has_provided_doc_ids:
            base_prompt += """
EXAMPLE - Using Pre-Provided Document IDs:
{{
  "tasks": [
    {{
      "task_id": "extract_data",
      "tool_name": "structured_extraction",
      "description": "Extract gross pay information from the documents",
      "requires_llm": true,
      "parameters": {{
        "document_ids": ["doc_abc123", "doc_def456"],
        "fields": ["gross_pay", "pay_date", "employer"],
        "max_total_chars": 200000,
        "max_chunks_per_doc": 100
      }},
      "depends_on": []
    }}
  ],
  "estimated_time_seconds": 30,
  "estimated_cost_usd": 0.01,
  "reasoning": "Extract structured fields from the provided documents."
}}
"""
        else:
            base_prompt += """
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
      "tool_name": "structured_extraction",
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
"""

        base_prompt += """
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
      "depends_on": ["other_task_ids_from_THIS_plan_only"]
    }}
  ],
  "estimated_time_seconds": number,
  "estimated_cost_usd": number,
  "reasoning": "brief explanation"
}}
"""
        return base_prompt

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

    def build_synthesis_prompt(
        self, *, query: str, plan, results: Dict[str, Any]
    ) -> str:
        plan_brief = getattr(plan, "reasoning", "") or ""
        # compact each task payload; never drop entire tasks
        compacted_results: Dict[str, Any] = {}
        for tid, payload in (results or {}).items():
            log_event("------------------------------------------------")
            log_event(tid)
            log_event(payload)
            try:
                # unwrap ResultEnvelope-like shapes ({"value": ...}) if present
                val = payload
                if isinstance(val, dict) and "value" in val and len(val) == 1:
                    val = val["value"]

                # keep search results structured & light (avoid stringifying giant dicts)
                if tid == "search_docs":
                    val = sanitize_tool_output(val)

                # use existing extraction-aware compactor
                compacted = _compact_for_synthesis(tid, val)

                # if worst-case compactor returned a giant string but original was a dict,
                # try a safer dict-preserving fallback for readability
                if isinstance(compacted, str) and isinstance(val, dict):
                    safe = {}
                    for k, v in val.items():
                        if k == "documents" and isinstance(v, list):
                            safe["documents"] = v[:5]
                        elif isinstance(v, str):
                            safe[k] = v[:600]
                        else:
                            safe[k] = v
                    compacted = safe

                compacted_results[tid] = compacted

            except Exception:
                compacted_results[tid] = str(payload)[:20000] + "…"

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
    def _tools_as_text(
        self, tools: Iterable[ToolLike], *, compact: bool = False
    ) -> str:
        """
        Accepts either tool objects (with .descriptor()) or plain descriptors.
        Emits a compact, deterministic list optimized for token efficiency.
        """
        lines: List[str] = []
        for tool in tools:
            d = self._tool_descriptor(tool)
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


def _build_document_search_system_message() -> str:
    """
    Build the system message with dynamic schema.
    """
    return (
        "You are a retrieval strategist. "
        "Return ONLY compact JSON with keys: "
        "method ('semantic'|'keyword'|'hybrid'|'metadata'), "
        "query, filters (optional), top_k, semantic_weight, similarity_threshold, rerank_top_k."
    )


def _build_structured_extraction_system_message(
    full_schema: Dict[str, Any],
    instructions: str,
) -> str:
    """
    Build the system message with dynamic schema.
    """
    schema_json = json.dumps(full_schema, indent=2, ensure_ascii=False)

    return (
        "You are a JSON extraction system. Your ONLY job is to output valid JSON.\n\n"
        "CRITICAL: Do NOT write explanations, summaries, or prose. Output ONLY the JSON object.\n\n"
        f"TASK:\n{instructions}\n\n"
        f"REQUIRED OUTPUT FORMAT:\n{schema_json}\n\n"
        "STRICT RULES:\n"
        "1. Output MUST be valid JSON matching the schema exactly\n"
        "2. Do NOT wrap in markdown code blocks (no ```json)\n"
        "3. Do NOT add any text before or after the JSON\n"
        "4. Do NOT write explanations or summaries\n"
        "5. If a field has no data, use null (not explanatory text)\n"
        "6. Include document_id in provenance array for citations\n\n"
        "OUTPUT ONLY THE JSON OBJECT NOW:"
    )


def _build_text_extraction_system_message(
    style: str,
    focus: Optional[str],
    max_output_length: int,
    include_citations: bool,
) -> str:
    """
    Build the system message for free-form text extraction and summarization.
    """
    style_guidance = {
        "concise": "Be brief and to the point. Use short sentences and avoid unnecessary details.",
        "detailed": "Provide comprehensive coverage with thorough explanations and context.",
        "bullet_points": "Use bullet points or numbered lists to organize information clearly.",
        "narrative": "Write in a flowing, story-like format that connects ideas smoothly.",
        "technical": "Use precise technical language and include relevant technical details.",
        "executive": "Focus on high-level insights and actionable takeaways for decision-makers.",
    }

    focus_guidance = {
        "overview": "Provide a comprehensive overview covering all major aspects.",
        "key_points": "Identify and highlight the most important points and findings.",
        "insights": "Extract deeper insights, patterns, and non-obvious observations.",
        "recommendations": "Focus on actionable recommendations and next steps.",
        "analysis": "Provide analytical perspective with critical evaluation.",
        "comparison": "Compare and contrast different aspects, highlighting similarities and differences.",
    }

    style_instruction = style_guidance.get(style, style_guidance["detailed"])
    focus_instruction = focus_guidance.get(focus, "") if focus else ""

    citation_instruction = (
        "\n\nCITATIONS:\n"
        "- Reference document IDs when making specific claims or citing information\n"
        "- Use format: [document_id] or (document_id) when referencing sources\n"
        "- Ensure all major points are attributed to source documents"
        if include_citations
        else ""
    )

    return (
        "You are a document analysis and summarization system. Your task is to extract, "
        "analyze, and present information from documents in clear, well-structured prose.\n\n"
        f"OUTPUT STYLE:\n{style_instruction}\n\n"
        + (f"FOCUS:\n{focus_instruction}\n\n" if focus_instruction else "")
        + f"LENGTH CONSTRAINT:\n"
        f"Target approximately {max_output_length} words. Be thorough but respect this constraint.\n"
        + citation_instruction
        + "\n\nCRITICAL RULES:\n"
        "1. Output ONLY the requested text content - no JSON, no metadata wrappers\n"
        "2. Do NOT add explanatory prefixes like 'Here is the summary:' or 'Based on the documents:'\n"
        "3. Start directly with the content\n"
        "4. Be factual and grounded in the provided document content\n"
        "5. Do NOT fabricate information not present in the documents\n"
        "6. If documents lack information on a topic, acknowledge this clearly\n"
        "7. Maintain professional tone and clarity throughout\n\n"
        "BEGIN YOUR RESPONSE NOW:"
    )
