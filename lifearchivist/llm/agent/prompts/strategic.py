from typing import Any, Iterable

from .base import BasePromptBuilder, ToolLike


class StrategicPromptBuilder(BasePromptBuilder):

    DEFAULT_MAX_PHASES: int = 7

    @classmethod
    def build(
        cls,
        query: str,
        context: Any,
        available_tools: Iterable[ToolLike],
        max_phases: int = DEFAULT_MAX_PHASES,
    ) -> str:
        tools_text = cls.tools_as_text(available_tools, compact=True)
        history_preview = cls.format_history_preview(context, compact=True)

        return f"""You are a strategic planner for a multi-tool agent system. Your job is to break down complex user queries into high-level phases.

USER QUERY:
{query}

RECENT CONVERSATION (preview):
{history_preview}

AVAILABLE TOOLS (short descriptions):
{tools_text}

YOUR TASK:
Analyze the user's query and create a strategic plan consisting of 1-7 high-level phases. Each phase represents a major step toward completing the user's request.

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
