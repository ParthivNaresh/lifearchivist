import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

from .exceptions import ToolExecutionError
from .models.context import ConversationContext
from .models.task import AgentTask
from .tool_registry import AgentToolRegistry

if TYPE_CHECKING:
    from ..llm import LLMProviderManager
    from .utils.prompt_builder import PromptBuilder

RETRIABLE = (TimeoutError, ConnectionError)


async def _with_timeout(coro, timeout_s: Optional[float]):
    if timeout_s is None:
        return await coro
    async with asyncio.timeout(timeout_s):
        return await coro


def _approx_size(obj: Any) -> int:
    """Very rough size heuristic."""
    return len(repr(obj).encode("utf-8"))


class AgentSpawner:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        prompt_builder: "PromptBuilder",
        task_timeout_s: float | None = 60,
        max_retries: int = 2,
        max_history_messages: int = 50,
        max_dependent_bytes: int = 256 * 1024,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.prompt_builder = prompt_builder
        self.task_timeout_s = task_timeout_s
        self.max_retries = max_retries
        self.max_history_messages = max_history_messages
        self.max_dependent_bytes = max_dependent_bytes

    async def spawn_and_execute(
        self,
        task: AgentTask,
        previous_results: Dict[str, Any],
        context: ConversationContext,
    ) -> Any:
        tool = self.tools.get_tool(task.tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {task.tool_name}")

        task_context = self._build_task_context(task, previous_results, context)

        if task.requires_llm and tool.requires_llm:
            prompt = self.prompt_builder.build_agent_prompt(
                task=task, tool=tool, context=task_context
            )
            result = await tool.execute_with_llm(
                llm_provider=self.llm,
                prompt=prompt,
                parameters=task.parameters,
                context=task_context,
            )
        else:
            result = await tool.execute(**task.parameters)

        return result

    def _build_task_context(
        self,
        task: AgentTask,
        previous_results: Dict[str, Any],
        context: ConversationContext,
    ) -> Dict[str, Any]:
        dependent_results = {
            dep_id: previous_results[dep_id]
            for dep_id in task.depends_on
            if dep_id in previous_results
        }

        return {
            "task_description": task.description,
            "dependent_results": dependent_results,
            "conversation_history": context.recent_messages,
            "user_preferences": context.user_preferences,
        }
