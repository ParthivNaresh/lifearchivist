from typing import TYPE_CHECKING, Any, Dict

from .base import BasePromptBuilder

if TYPE_CHECKING:
    from ..models.task import AgentTask
    from ..tools.base import BaseAgentTool


class TaskPromptBuilder(BasePromptBuilder):

    @classmethod
    def build(
        cls,
        task: "AgentTask",
        tool: "BaseAgentTool",
        context: Dict[str, Any],
    ) -> str:
        desc = cls.tool_descriptor(tool)
        tool_name = desc.get("name", "")
        tool_summary = desc.get("summary", "")

        dep_prev = cls.preview(
            context.get("dependent_results"), cls.DEP_RESULTS_PREVIEW_CHARS
        )
        hist_prev = cls.preview(
            context.get("conversation_history"), cls.COMPACT_HISTORY_PREVIEW_CHARS
        )
        prefs_prev = cls.preview(
            context.get("user_preferences"), cls.PREFS_PREVIEW_CHARS
        )
        params_prev = cls.preview(task.parameters, cls.PARAMS_PREVIEW_CHARS)

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
