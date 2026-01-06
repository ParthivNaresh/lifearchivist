from typing import Any, Iterable

from .base import BasePromptBuilder, ToolLike


class TacticalPromptBuilder(BasePromptBuilder):

    DEFAULT_MAX_TASKS: int = 20

    @classmethod
    def build(
        cls,
        query: str,
        context: Any,
        available_tools: Iterable[ToolLike],
        max_tasks: int = DEFAULT_MAX_TASKS,
    ) -> str:
        tools_text = cls.tools_as_text(available_tools)
        history_preview = cls.format_history_preview(context)
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
            base_prompt += cls._doc_ids_provided_section()
        else:
            base_prompt += cls._dependency_binding_section()

        base_prompt += cls._tool_parameter_cheatsheet()
        base_prompt += f"\nCONSTRAINTS:\n- Max tasks: {max_tasks}\n"

        if has_provided_doc_ids:
            base_prompt += cls._example_with_doc_ids()
        else:
            base_prompt += cls._example_with_search()

        base_prompt += cls._output_format()

        return base_prompt

    @staticmethod
    def _doc_ids_provided_section() -> str:
        return """
IMPORTANT - DOCUMENT IDS ALREADY PROVIDED:
The query above contains "DOCUMENT IDS FROM PREVIOUS PHASES" with actual document IDs.
- Use these document IDs DIRECTLY in the "document_ids" parameter as a literal array of strings.
- Do NOT use "<from ...>" placeholder syntax for these IDs.
- Do NOT add any "depends_on" entries for these IDs - they are already resolved.
- Example: "document_ids": ["abc123", "def456"] (use the actual IDs from the query)

"""

    @staticmethod
    def _dependency_binding_section() -> str:
        return """
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

    @staticmethod
    def _tool_parameter_cheatsheet() -> str:
        return """TOOL PARAMETER CHEATSHEET (follow exactly):
- document_search (LLM-only):
    - requires_llm: true
    - parameters:
        {
          "query": string,
          "search_method": "hybrid" | "semantic" | "keyword" | "metadata",
          "top_k": integer (1-100),
          "similarity_threshold": float (0..1)   // optional, recommended
          "semantic_weight": float (0..1)        // optional, recommended for hybrid
          "mime_types": [string]?,
          "themes": [string]?,
          "date_filter": {"after": "YYYY-MM-DD"?, "before": "YYYY-MM-DD"?}?,
          "status": string?,
          "include_metadata": true/false?,
          "include_text_preview": true/false?,
          "instructions": string?,               // guidance to the search agent
          "model": string?                       // optional model hint
        }

- structured_extraction:
    - requires_llm: true (recommended)
    - parameters:
        {
          "document_ids": [string, ...]         // array of document ID strings
          "fields": [string, ...],
          "max_total_chars": integer?,      // optional safety cap
          "max_chunks_per_doc": integer?,   // optional per-doc cap
          "model": string?                  // optional model hint
        }

- text_extraction:
    - requires_llm: true
    - parameters:
        {
          "document_ids": [string, ...]         // array of document ID strings
          "instructions": string,           // what to extract/summarize
          "style": "concise" | "detailed" | "bullet_points" | "narrative" | "technical" | "executive",
          "focus": "overview" | "key_points" | "insights" | "recommendations" | "analysis" | "comparison"?,
          "max_output_length": integer?,    // target word count
          "include_citations": true/false?, // include document references
          "model": string?                  // optional model hint
        }

"""

    @staticmethod
    def _example_with_doc_ids() -> str:
        return """
EXAMPLE - Using Pre-Provided Document IDs:
{
  "tasks": [
    {
      "task_id": "extract_data",
      "tool_name": "structured_extraction",
      "description": "Extract gross pay information from the documents",
      "requires_llm": true,
      "parameters": {
        "document_ids": ["doc_abc123", "doc_def456"],
        "fields": ["gross_pay", "pay_date", "employer"],
        "max_total_chars": 200000,
        "max_chunks_per_doc": 100
      },
      "depends_on": []
    }
  ],
  "estimated_time_seconds": 30,
  "estimated_cost_usd": 0.01,
  "reasoning": "Extract structured fields from the provided documents."
}
"""

    @staticmethod
    def _example_with_search() -> str:
        return """
EXAMPLE - Document Search (LLM) + Extraction:
{
  "tasks": [
    {
      "task_id": "search_docs",
      "tool_name": "document_search",
      "description": "Find relevant blood test documents",
      "requires_llm": true,
      "parameters": {
        "query": "blood test",
        "search_method": "hybrid",
        "top_k": 5,
        "similarity_threshold": 0.3,
        "semantic_weight": 0.6,
        "instructions": "Prefer recent lab reports; exclude appointment reminders."
      },
      "depends_on": []
    },
    {
      "task_id": "extract_data",
      "tool_name": "structured_extraction",
      "description": "Extract test_type, date, results from the retrieved documents",
      "requires_llm": true,
      "parameters": {
        "document_ids": ["<from search_docs>"],
        "fields": ["test_type", "date", "results"],
        "max_total_chars": 200000,
        "max_chunks_per_doc": 100
      },
      "depends_on": ["search_docs"]
    }
  ],
  "estimated_time_seconds": 45,
  "estimated_cost_usd": 0.02,
  "reasoning": "Search first with LLM-chosen strategy; then extract structured fields with provenance."
}
"""

    @staticmethod
    def _output_format() -> str:
        return """
OUTPUT FORMAT:
Return STRICT JSON (no markdown, no prose) matching this schema:
{
  "tasks": [
    {
      "task_id": "unique_id",
      "tool_name": "MUST be from AVAILABLE TOOLS list",
      "description": "what this task does",
      "requires_llm": true/false,
      "parameters": {},
      "depends_on": ["other_task_ids_from_THIS_plan_only"]
    }
  ],
  "estimated_time_seconds": number,
  "estimated_cost_usd": number,
  "reasoning": "brief explanation"
}
"""
