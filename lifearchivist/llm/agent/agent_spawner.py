import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple

from pydantic import BaseModel

from ...utils.logx import log_event, track
from .exceptions import ToolExecutionError
from .models import (  # adjust to your package layout
    AgentTask,
    ConversationContext,
    ResultEnvelope,
)
from .tool_registry import AgentToolRegistry

if TYPE_CHECKING:
    from llm import LLMProviderManager

    from .utils.prompt_builder import PromptBuilder


def _approx_size(obj: Any) -> int:
    """Best-effort, cheap size heuristic in bytes."""
    try:
        return len(repr(obj).encode("utf-8"))
    except Exception:
        return 0


DEFAULT_RETRIABLE: Tuple[type[BaseException], ...] = (
    asyncio.TimeoutError,
    ConnectionError,
)


@asynccontextmanager
async def _maybe_timeout(seconds: float | None):
    """Async context manager that applies an asyncio timeout when provided."""
    if seconds is None:
        yield
    else:
        async with asyncio.timeout(seconds):
            yield


class AgentSpawner:
    """
    Runs a single AgentTask by invoking the appropriate tool, with:
      - timeouts & bounded retries
      - LLM/non-LLM routing
      - Pydantic-typed parameter validation
      - normalized ResultEnvelope contract
      - trimmed context (history, dependent results audit)
    """

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        prompt_builder: "PromptBuilder",
        *,
        task_timeout_s: float | None = 60.0,
        max_retries: int = 2,
        max_history_messages: int = 50,
        max_dependent_bytes: int = 256 * 1024,  # soft cap (warn when exceeded)
        retriable_exceptions: Optional[Iterable[type[BaseException]]] = None,
        backoff_base_s: float = 0.5,
        backoff_max_s: float = 5.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.prompt_builder = prompt_builder

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
        """
        Execute a task through its tool. Always returns a ResultEnvelope.
        Cancellation propagates (asyncio.CancelledError is not swallowed).
        """
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

        tool = self.tools.get_tool(task.tool_name)
        if not tool:
            log_event(
                "spawner_tool_not_found",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                },
                level=logging.ERROR,
            )
            return ResultEnvelope(
                task_id=task.task_id,
                status="error",
                error_type="ToolNotFound",
                error_message=f"Tool not found: {task.tool_name}",
                attempts=1,
                duration_ms=0,
            )

        task_ctx = self._build_task_context(task, previous_results, context)
        requires_llm = bool(task.requires_llm or getattr(tool, "requires_llm", False))

        attempts = 0
        start_ns = time.perf_counter_ns()
        last_exc: Optional[BaseException] = None

        while True:
            attempts += 1
            log_event(
                "spawner_attempt_started",
                {
                    "conversation_id": context.conversation_id,
                    "task_id": task.task_id,
                    "attempt": attempts,
                    "max_retries": self.max_retries,
                },
            )

            try:
                async with _maybe_timeout(self.task_timeout_s):
                    model = getattr(tool, "input_model", None)
                    if model is None:
                        raise ToolExecutionError(
                            f"Tool '{task.tool_name}' missing input_model (Pydantic BaseModel)"
                        )
                    typed_params: BaseModel = model.model_validate(task.parameters)

                    value = await self._invoke_tool(
                        tool=tool,
                        task=task,
                        task_ctx=task_ctx,
                        requires_llm=requires_llm,
                        typed_params=typed_params,
                    )

                duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

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

                return ResultEnvelope(
                    task_id=task.task_id,
                    status="ok",
                    value=value,
                    attempts=attempts,
                    duration_ms=duration_ms,
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
                if attempts <= self.max_retries:
                    delay = self._compute_backoff(attempts)
                    log_event(
                        "spawner_retriable_error",
                        {
                            "conversation_id": context.conversation_id,
                            "task_id": task.task_id,
                            "attempt": attempts,
                            "max_retries": self.max_retries,
                            "error_type": type(e).__name__,
                            "error": str(e),
                            "backoff_seconds": delay,
                        },
                        level=logging.WARNING,
                    )
                    self.log.warning(
                        "Retriable error on task %s (attempt %d/%d): %s; backing off %.2fs",
                        task.task_id,
                        attempts,
                        self.max_retries,
                        type(e).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                log_event(
                    "spawner_retries_exhausted",
                    {
                        "conversation_id": context.conversation_id,
                        "task_id": task.task_id,
                        "attempts": attempts,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
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

        duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
        log_event(
            "spawner_execute_failed",
            {
                "conversation_id": context.conversation_id,
                "task_id": task.task_id,
                "tool_name": task.tool_name,
                "attempts": attempts,
                "duration_ms": duration_ms,
                "error_type": type(last_exc).__name__ if last_exc else "UnknownError",
                "error": str(last_exc) if last_exc else "Unknown error",
            },
            level=logging.ERROR,
        )
        return ResultEnvelope(
            task_id=task.task_id,
            status="error",
            error_type=type(last_exc).__name__ if last_exc else "UnknownError",
            error_message=str(last_exc) if last_exc else "Unknown error",
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
        """
        Invoke tool in LLM or non-LLM mode using Pydantic-typed parameters.
        """
        if requires_llm:
            if not hasattr(tool, "execute_with_llm"):
                raise ToolExecutionError(
                    f"Tool '{task.tool_name}' requires LLM but has no 'execute_with_llm' implementation"
                )
            prompt = self.prompt_builder.build_agent_prompt(
                task=task, tool=tool, context=task_ctx
            )
            return await tool.execute_with_llm(
                llm_provider=self.llm,
                prompt=prompt,
                params=typed_params,
                context=task_ctx,
            )

        # Non-LLM path: typed only
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
        """
        Construct the context passed to tools. History is trimmed; dependent
        results are included and size-audited (soft cap with logging).
        """
        # Trim conversation history
        history = (
            context.recent_messages[-self.max_history_messages :]
            if self.max_history_messages
            else context.recent_messages
        )

        # Include dependent results (soft size cap: warn when exceeded)
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
            # could also pass: conversation_id/user_id/trace ids here for observability
        }

    def _compute_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter, capped at backoff_max_s."""
        base = self.backoff_base_s * (2 ** (attempt - 1))
        jitter = 0.2 * base * (2 * random.random() - 1)  # ±20%
        return float(min(self.backoff_max_s, max(0.0, base + jitter)))
