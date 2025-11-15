import json
from typing import TYPE_CHECKING, Dict, List

from ..models.task import AgentTask, ExecutionPlan

if TYPE_CHECKING:
    from ..models.context import ConversationContext
    from ..tools.base import BaseAgentTool


class PromptBuilder:

    def build_complexity_classification_prompt(self, query: str) -> str:
        return f"""Classify this query as SIMPLE or COMPLEX.

Query: "{query}"

SIMPLE: Can be answered with document retrieval + single LLM response
Examples:
- "What is X?"
- "Summarize document Y"
- "When did Z happen?"
- "Tell me about..."

COMPLEX: Requires multiple steps, tool orchestration, or data processing
Examples:
- "Create a PDF of my trip photos"
- "Compare my income across years"
- "Find documents matching this checklist"
- "Generate a timeline of..."
- "Analyze trends in..."

Respond with JSON:
{{
  "complexity": "simple" | "complex",
  "reasoning": "brief explanation",
  "estimated_steps": 1-10
}}"""

    def build_planning_prompt(
        self,
        query: str,
        context: "ConversationContext",
        available_tools: List["BaseAgentTool"],
    ) -> str:
        tool_descriptions = self._format_tool_descriptions(available_tools)
        conversation_history = self._format_conversation_history(context)

        return f"""You are an AI orchestrator. Create an execution plan for this query.

Query: "{query}"

Conversation History:
{conversation_history}

Available Tools:
{tool_descriptions}

Create a step-by-step execution plan. Each step should:
1. Use one tool
2. Have clear parameters
3. Specify if it requires LLM processing
4. List dependencies on previous steps

Respond with JSON:
{{
  "tasks": [
    {{
      "task_id": "task_1",
      "tool_name": "ThemeFilterTool",
      "description": "Filter documents by theme",
      "requires_llm": false,
      "parameters": {{"theme": "Healthcare"}},
      "depends_on": []
    }},
    {{
      "task_id": "task_2",
      "tool_name": "DataExtractionTool",
      "description": "Extract specific data from documents",
      "requires_llm": true,
      "parameters": {{"fields": ["cholesterol"]}},
      "depends_on": ["task_1"]
    }}
  ],
  "estimated_time_seconds": 10,
  "estimated_cost_usd": 0.015,
  "reasoning": "Brief explanation of plan"
}}

Be creative and adaptive. Use tools in novel combinations if needed."""

    def build_agent_prompt(
        self, task: AgentTask, tool: "BaseAgentTool", context: Dict[str, any]
    ) -> str:
        context_str = json.dumps(context, indent=2)
        params_str = json.dumps(task.parameters, indent=2)

        return f"""You are an AI agent specialized in: {task.description}

Task: {task.description}

Context from previous steps:
{context_str}

Parameters:
{params_str}

Tool: {tool.name}
Tool Description: {tool.description}

Execute this task and return structured results. Focus on:
1. Accuracy - extract/process data correctly
2. Completeness - don't miss relevant information
3. Structure - return well-formatted results
4. Confidence - indicate certainty in your results

Return results in a format appropriate for the tool."""

    def build_synthesis_prompt(
        self, query: str, plan: ExecutionPlan, results: Dict[str, any]
    ) -> str:
        results_summary = json.dumps(results, indent=2)
        plan_summary = self._format_plan_summary(plan)

        return f"""Synthesize a comprehensive response to the user's query.

Original Query: "{query}"

Execution Plan:
{plan_summary}

Task Results:
{results_summary}

Create a natural, helpful response that:
1. Directly answers the query
2. Presents data clearly (use markdown formatting)
3. Provides insights and observations
4. Mentions any limitations or caveats
5. Is conversational and helpful

Do NOT:
- Mention tool names or technical details
- Apologize or be overly cautious
- Repeat the query back
- Use phrases like "based on the results" excessively

Stream your response naturally."""

    def _format_tool_descriptions(self, tools: List["BaseAgentTool"]) -> str:
        if not tools:
            return "No tools available"

        descriptions = []
        for tool in tools:
            desc = f"- {tool.name}: {tool.description}"
            try:
                schema = tool.input_schema
                if schema:
                    desc += f"\n  Input: {json.dumps(schema, indent=2)}"
            except (AttributeError, TypeError):
                pass
            descriptions.append(desc)
        return "\n\n".join(descriptions)

    def _format_conversation_history(self, context: "ConversationContext") -> str:
        if not hasattr(context, "recent_messages") or not context.recent_messages:
            return "No previous conversation"

        messages = []
        for msg in context.recent_messages[-5:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            messages.append(f"{role}: {content}")

        return "\n".join(messages)

    def _format_plan_summary(self, plan: ExecutionPlan) -> str:
        tasks = []
        for task in plan.tasks:
            tasks.append(f"- {task.task_id}: {task.tool_name} - {task.description}")
        return "\n".join(tasks)
