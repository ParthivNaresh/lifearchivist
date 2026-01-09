import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Iterable, Optional

from pydantic import BaseModel

from ...utils.logx import log_event, track
from ..resolver import resolve_params
from .constants import AgentExecutionDefaults
from .exceptions import ToolExecutionError
from .models import (
    AgentTask,
    ConversationContext,
    ResultEnvelope,
)
from .prompts import TaskPromptBuilder
from .tool_registry import AgentToolRegistry
from .types import DEFAULT_RETRIABLE
from .utils.async_utils import compute_exponential_backoff, maybe_timeout
from .utils.parsing import (
    _PLACEHOLDER_PATTERN,
    _approx_size,
    _json_preview,
    _safe_preview,
    sanitize_tool_output,
)

if TYPE_CHECKING:
    from llm import LLMProviderManager


class AgentSpawner:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        *,
        task_timeout_s: float | None = AgentExecutionDefaults.TASK_TIMEOUT_SECONDS,
        max_retries: int = AgentExecutionDefaults.MAX_RETRIES,
        max_history_messages: int = AgentExecutionDefaults.MAX_HISTORY_MESSAGES,
        max_dependent_bytes: int = AgentExecutionDefaults.MAX_DEPENDENT_BYTES,
        retriable_exceptions: Optional[Iterable[type[BaseException]]] = None,
        backoff_base_s: float = AgentExecutionDefaults.BACKOFF_BASE_SECONDS,
        backoff_max_s: float = AgentExecutionDefaults.BACKOFF_MAX_SECONDS,
        logger: Optional[logging.Logger] = None,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry

        self.task_timeout_s = task_timeout_s
        self.max_retries = max_retries
        self.max_history_messages = max_history_messages
        self.max_dependent_bytes = max_dependent_bytes

        self.retriable_exceptions = (
            tuple(retriable_exceptions) if retriable_exceptions else DEFAULT_RETRIABLE
        )
        self.backoff_base_s = backoff_base_s
        self.backoff_max_s = backoff_max_s

        self.log = logger or logging.getLogger(__name__)

    @track(operation="spawn_and_execute")
    async def spawn_and_execute(
        self,
        task: AgentTask,
        previous_results: dict[str, Any],
        context: ConversationContext,
    ) -> ResultEnvelope:
        early_exit = self._check_early_exit(task, context)
        if early_exit is not None:
            return early_exit

        tool = self.tools.get_tool(task.tool_name)
        if not tool:
            return self._handle_tool_not_found(task, context)

        task_ctx = self._build_task_context(task, previous_results, context)
        requires_llm = self._resolve_llm_requirement(task, tool)

        return await self._execute_with_retries(
            task, tool, task_ctx, requires_llm, previous_results, context
        )

    def _check_early_exit(
        self,
        task: AgentTask,
        context: ConversationContext,
    ) -> Optional[ResultEnvelope]:
        if context.is_cancelled:
            log_event(
                "spawner_task_cancelled_before_start",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                },
            )
            return ResultEnvelope.error(
                task.task_id,
                "Cancelled",
                "Task cancelled before execution",
                attempts=0,
            )

        log_event(
            "spawner_execute_started",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "tool_name": task.tool_name,
                "requires_llm": task.requires_llm,
                "depends_on_count": len(task.depends_on),
            },
        )
        return None

    def _handle_tool_not_found(
        self,
        task: AgentTask,
        context: ConversationContext,
    ) -> ResultEnvelope:
        log_event(
            "spawner_tool_not_found",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "tool_name": task.tool_name,
            },
            level=logging.ERROR,
        )
        return ResultEnvelope.error(
            task.task_id,
            "ToolNotFound",
            f"Tool not found: {task.tool_name}",
        )

    def _resolve_llm_requirement(self, task: AgentTask, tool: Any) -> bool:
        tool_requires = tool.requires_llm
        task_requires = task.requires_llm

        if tool_requires and task_requires is False:
            raise ValueError(
                f"Task '{task.task_id}' uses '{task.tool_name}' which requires LLM, "
                f"but task.requires_llm=False. Either set requires_llm=True or use a different tool."
            )

        return task_requires if task_requires is not None else tool_requires

    async def _execute_with_retries(
        self,
        task: AgentTask,
        tool: Any,
        task_ctx: dict[str, Any],
        requires_llm: bool,
        previous_results: dict[str, Any],
        context: ConversationContext,
    ) -> ResultEnvelope:
        attempts = 0
        start_ns = time.perf_counter_ns()
        last_exc: Optional[BaseException] = None

        while True:
            attempts += 1

            try:
                value = await self._execute_single_attempt(
                    task, tool, task_ctx, requires_llm, previous_results, context
                )
                return self._finalize_success(
                    task, value, attempts, start_ns, requires_llm, context
                )

            except asyncio.CancelledError:
                log_event(
                    "spawner_task_cancelled",
                    {
                        "conversation_id": context.conversation_id,
                        "task_id": task.task_id,
                        "attempt": attempts,
                    },
                )
                self.log.debug("Task %s cancelled", task.task_id)
                raise

            except self.retriable_exceptions as e:
                last_exc = e
                should_retry = await self._handle_retriable_error(
                    task, e, attempts, context
                )
                if should_retry:
                    continue
                break

            except Exception as e:
                last_exc = e
                log_event(
                    "spawner_non_retriable_error",
                    {
                        "conversation_id": context.conversation_id,
                        "task_id": task.task_id,
                        "attempt": attempts,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
                break

        return self._finalize_failure(task, last_exc, attempts, start_ns, context)

    async def _execute_single_attempt(
        self,
        task: AgentTask,
        tool: Any,
        task_ctx: dict[str, Any],
        requires_llm: bool,
        previous_results: dict[str, Any],
        context: ConversationContext,
    ) -> Any:
        async with maybe_timeout(self.task_timeout_s):
            typed_params = self._resolve_and_validate_params(
                task, tool, previous_results, context
            )

            value = await self._invoke_tool(
                tool=tool,
                task=task,
                task_ctx=task_ctx,
                requires_llm=requires_llm,
                typed_params=typed_params,
            )

            log_event("spawner_task_value_summary_pre_sanitized", {"value": value})
            value = sanitize_tool_output(value)
            log_event("spawner_task_value_summary_post_sanitized", {"value": value})

            return value

    def _resolve_and_validate_params(
        self,
        task: AgentTask,
        tool: Any,
        previous_results: dict[str, Any],
        context: ConversationContext,
    ) -> BaseModel:
        try:
            resolved_params = resolve_params(
                task.parameters,
                previous_results,
                task.depends_on or [],
            )
        except Exception as e:
            log_event(
                "spawner_param_resolution_failed",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "error": str(e),
                    "depends_on": task.depends_on,
                    "params_preview": _safe_preview(task.parameters, 600),
                },
                level=logging.ERROR,
            )
            raise

        self._check_unresolved_placeholders(task, resolved_params, context)

        model: type[BaseModel] | None = getattr(tool, "input_model", None)
        if model is None:
            raise ToolExecutionError(
                f"Tool '{task.tool_name}' missing input_model (Pydantic BaseModel)"
            )

        return model.model_validate(resolved_params)

    def _check_unresolved_placeholders(
        self,
        task: AgentTask,
        resolved_params: dict[str, Any],
        context: ConversationContext,
    ) -> None:
        try:
            params_str = json.dumps(resolved_params, ensure_ascii=False)
        except Exception:
            params_str = str(resolved_params)

        if _PLACEHOLDER_PATTERN.search(params_str):
            log_event(
                "spawner_unresolved_placeholders",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "params_preview": _json_preview(params_str, 1500),
                },
                level=logging.ERROR,
            )
            raise ValueError(
                "Unresolved dependency placeholder remains in parameters. "
                "Ensure all '<from task_id>' references point to completed dependencies."
            )

    async def _handle_retriable_error(
        self,
        task: AgentTask,
        error: BaseException,
        attempts: int,
        context: ConversationContext,
    ) -> bool:
        if attempts <= self.max_retries:
            delay = self._compute_backoff(attempts)
            log_event(
                "spawner_retriable_error",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                    "attempt": attempts,
                    "max_retries": self.max_retries,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "backoff_seconds": delay,
                },
                level=logging.WARNING,
            )
            self.log.warning(
                "Retriable error on task %s (attempt %d/%d): %s; backing off %.2fs",
                task.task_id,
                attempts,
                self.max_retries,
                type(error).__name__,
                delay,
            )
            await asyncio.sleep(delay)
            return True

        log_event(
            "spawner_retries_exhausted",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "attempts": attempts,
                "error_type": type(error).__name__,
                "error": str(error),
            },
            level=logging.ERROR,
        )
        return False

    def _finalize_success(
        self,
        task: AgentTask,
        value: Any,
        attempts: int,
        start_ns: int,
        requires_llm: bool,
        context: ConversationContext,
    ) -> ResultEnvelope:
        duration_ms = self._elapsed_ms(start_ns)

        log_event(
            "spawner_execute_success",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "tool_name": task.tool_name,
                "attempts": attempts,
                "duration_ms": duration_ms,
                "requires_llm": requires_llm,
            },
        )

        if isinstance(value, ResultEnvelope):
            if value.attempts < attempts:
                value.attempts = attempts
            if not value.duration_ms:
                value.duration_ms = duration_ms
            return value

        return ResultEnvelope.ok(
            task.task_id,
            value,
            attempts=attempts,
            duration_ms=duration_ms,
        )

    def _finalize_failure(
        self,
        task: AgentTask,
        error: Optional[BaseException],
        attempts: int,
        start_ns: int,
        context: ConversationContext,
    ) -> ResultEnvelope:
        duration_ms = self._elapsed_ms(start_ns)
        error_type = type(error).__name__ if error else "UnknownError"
        error_message = str(error) if error else "Unknown error"

        log_event(
            "spawner_execute_failed",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "tool_name": task.tool_name,
                "attempts": attempts,
                "duration_ms": duration_ms,
                "error_type": error_type,
                "error": error_message,
            },
            level=logging.ERROR,
        )

        return ResultEnvelope.error(
            task.task_id,
            error_type,
            error_message,
            attempts=attempts,
            duration_ms=duration_ms,
        )

    async def _invoke_tool(
        self,
        tool: Any,
        task: AgentTask,
        task_ctx: dict[str, Any],
        requires_llm: bool,
        *,
        typed_params: BaseModel,
    ) -> Any:
        if requires_llm:
            if not hasattr(tool, "execute_with_llm"):
                raise ToolExecutionError(
                    f"Tool '{task.tool_name}' requires LLM but has no 'execute_with_llm' implementation"
                )
            prompt = TaskPromptBuilder.build(task=task, tool=tool, context=task_ctx)

            return await tool.execute_with_llm(
                llm_provider=self.llm,
                prompt=prompt,
                params=typed_params,
                context=task_ctx,
            )

        if not hasattr(tool, "execute_typed"):
            raise ToolExecutionError(
                f"Tool '{task.tool_name}' is missing 'execute_typed' implementation"
            )
        return await tool.execute_typed(params=typed_params, context=task_ctx)

    def _build_task_context(
        self,
        task: AgentTask,
        previous_results: dict[str, Any],
        context: ConversationContext,
    ) -> dict[str, Any]:
        history = (
            context.recent_messages[-self.max_history_messages :]
            if self.max_history_messages
            else context.recent_messages
        )

        deps: dict[str, Any] = {}
        total_bytes = 0

        for dep_id in task.depends_on:
            if dep_id in previous_results:
                val = previous_results[dep_id]
                sz = _approx_size(val)
                deps[dep_id] = val
                total_bytes += sz

        if self.max_dependent_bytes and total_bytes > self.max_dependent_bytes:
            self.log.warning(
                "Dependent results for task %s total ~%d bytes (> %d). "
                "Consider summarizing upstream outputs or raising the cap.",
                task.task_id,
                total_bytes,
                self.max_dependent_bytes,
            )

        return {
            "task_description": task.description,
            "dependent_results": deps,
            "conversation_history": history,
            "user_preferences": context.user_preferences,
            "dependent_bytes_estimate": total_bytes,
        }

    def _compute_backoff(self, attempt: int) -> float:
        return compute_exponential_backoff(
            attempt,
            base_seconds=self.backoff_base_s,
            max_seconds=self.backoff_max_s,
        )

    @staticmethod
    def _elapsed_ms(start_ns: int) -> int:
        return (time.perf_counter_ns() - start_ns) // 1_000_000
