import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional

from ...server.api.routes.conversations.misc_models import EventType, StreamContext
from ...server.api.routes.shared.exceptions import ServiceUnavailableError
from ...utils.logx import log_event
from ...utils.sse import SSEFormatter
from ..agent import ComplexityClassifier
from ..agent import ConversationContext as AgentConversationContext
from ..agent import PromptBuilder
from ..agent.cancellation import CancellationReason, CancellationToken
from ..agent.models.events import AgentEventType
from ..processors.base import StreamProcessor
from ..processors.direct import DirectStreamProcessor


class AgentProgressTracker:

    def __init__(self) -> None:
        self.phases: List[Dict[str, Any]] = []
        self.current_phase_index: int = -1
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_phases: List[str] = []
        self.is_synthesizing: bool = False
        self.is_cancelled: bool = False
        self.cancellation_reason: Optional[str] = None

    def set_strategic_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        if plan_data.get("type") == "strategic":
            self.phases = [
                {
                    "phase_id": p["phase_id"],
                    "description": p["description"],
                    "status": "pending",
                    "tasks": [],
                }
                for p in plan_data.get("phases", [])
            ]
        return self._build_progress_event("plan_created")

    def set_tactical_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.current_phase_index >= 0 and self.current_phase_index < len(
            self.phases
        ):
            tasks = plan_data.get("tasks", [])
            self.phases[self.current_phase_index]["tasks"] = [
                {
                    "task_id": t.get("task_id"),
                    "tool": t.get("tool"),
                    "description": t.get("description", ""),
                    "status": "pending",
                }
                for t in tasks
            ]
            for t in tasks:
                self.tasks[t.get("task_id", "")] = {
                    "phase_index": self.current_phase_index,
                    "status": "pending",
                }
        return self._build_progress_event("tactical_plan_created")

    def start_phase(self, phase_id: str) -> Dict[str, Any]:
        for i, phase in enumerate(self.phases):
            if phase["phase_id"] == phase_id:
                self.current_phase_index = i
                phase["status"] = "running"
                break
        return self._build_progress_event("phase_started", phase_id=phase_id)

    def complete_phase(self, phase_id: str) -> Dict[str, Any]:
        for phase in self.phases:
            if phase["phase_id"] == phase_id:
                phase["status"] = "completed"
                self.completed_phases.append(phase_id)
                break
        return self._build_progress_event("phase_completed", phase_id=phase_id)

    def start_task(
        self, task_id: str, tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "running"
            phase_idx = self.tasks[task_id]["phase_index"]
            for task in self.phases[phase_idx].get("tasks", []):
                if task["task_id"] == task_id:
                    task["status"] = "running"
                    break
        return self._build_progress_event(
            "task_started", task_id=task_id, tool=tool_name
        )

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "completed"
            phase_idx = self.tasks[task_id]["phase_index"]
            for task in self.phases[phase_idx].get("tasks", []):
                if task["task_id"] == task_id:
                    task["status"] = "completed"
                    break
        return self._build_progress_event("task_completed", task_id=task_id)

    def fail_task(self, task_id: str, error: str) -> Dict[str, Any]:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "failed"
            phase_idx = self.tasks[task_id]["phase_index"]
            for task in self.phases[phase_idx].get("tasks", []):
                if task["task_id"] == task_id:
                    task["status"] = "failed"
                    break
        return self._build_progress_event("task_failed", task_id=task_id, error=error)

    def start_synthesis(self) -> Dict[str, Any]:
        self.is_synthesizing = True
        return self._build_progress_event("synthesis_started")

    def cancel_task(self, task_id: str, reason: str) -> Dict[str, Any]:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "cancelled"
            phase_idx = self.tasks[task_id]["phase_index"]
            for task in self.phases[phase_idx].get("tasks", []):
                if task["task_id"] == task_id:
                    task["status"] = "cancelled"
                    break
        return self._build_progress_event("task_cancelled", task_id=task_id, error=reason)

    def cancel_phase(self, phase_id: str, reason: str) -> Dict[str, Any]:
        for phase in self.phases:
            if phase["phase_id"] == phase_id:
                phase["status"] = "cancelled"
                break
        return self._build_progress_event("phase_cancelled", phase_id=phase_id, error=reason)

    def cancel_plan(self, reason: str) -> Dict[str, Any]:
        self.is_cancelled = True
        self.cancellation_reason = reason
        for phase in self.phases:
            if phase["status"] == "running":
                phase["status"] = "cancelled"
            elif phase["status"] == "pending":
                phase["status"] = "cancelled"
        return self._build_progress_event("plan_cancelled", error=reason)

    def _build_progress_event(
        self,
        event: str,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tool: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "event": event,
            "phase_id": phase_id,
            "task_id": task_id,
            "tool": tool,
            "error": error,
            "phases": self.phases,
            "current_phase_index": self.current_phase_index,
            "completed_phases": self.completed_phases,
            "is_synthesizing": self.is_synthesizing,
        }


class GatewayStreamProcessor(StreamProcessor):
    def __init__(self, server: Any):
        self.server = server
        self._validate_services()

    def _validate_services(self) -> None:
        if not self.server.service_container:
            raise ServiceUnavailableError("Service Container")
        required = [
            ("llm_provider_manager", "LLM Provider Manager"),
            ("conversation_service", "Conversation Service"),
            ("message_service", "Message Service"),
        ]
        for attr, name in required:
            if not getattr(self.server.service_container, attr, None):
                raise ServiceUnavailableError(name)

    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        dsp = DirectStreamProcessor(self.server)
        processing_message_id: Optional[str] = None
        try:
            await dsp._initialize_context(context)
            yield await dsp._save_user_message(context)
            processing_message_id = await dsp._create_processing_message(context)
            await dsp._broadcast_message_status(
                context.conversation_id, processing_message_id, "processing"
            )

            classifier = ComplexityClassifier(
                llm_provider_manager=self.server.service_container.llm_provider_manager,
                prompt_builder=PromptBuilder(),
            )
            log_event(
                "complexity_classification_started",
                {"conversation_id": context.conversation_id},
            )
            agent_ctx = AgentConversationContext(
                conversation_id=context.conversation_id,
                user_id="default",
                recent_messages=[],
                user_preferences={},
                metadata={"route": "gateway"},
                cancellation_token=context.cancellation_token,
            )
            classification = await classifier.classify(
                context.request.content, agent_ctx
            )
            log_event(
                "complexity_classification_completed",
                {
                    "conversation_id": context.conversation_id,
                    "complexity": classification.complexity.value,
                    "confidence": classification.confidence,
                    "estimated_steps": classification.estimated_steps,
                },
            )
            yield SSEFormatter.format_event(
                EventType.INTENT,
                {
                    "complexity": classification.complexity.value,
                    "confidence": classification.confidence,
                    "estimated_steps": classification.estimated_steps,
                },
            )

            is_simple = classification.complexity.value == "simple"

            if is_simple:
                await dsp._perform_search(context)
                yield SSEFormatter.format_event(EventType.SOURCES, context.sources)
                config = await dsp._get_stream_config(context)
                messages = dsp._build_messages(context, config)

                async for event in dsp._stream_llm_only(context, messages, config):
                    yield event

                if processing_message_id:
                    await dsp._finalize_processing_message(
                        processing_message_id, context.accumulated_text or ""
                    )
                    await dsp._broadcast_message_status(
                        context.conversation_id,
                        processing_message_id,
                        "completed",
                        content=context.accumulated_text,
                    )

                    msg_service = self.server.service_container.message_service
                    msg_result = await msg_service.get_message_with_citations(
                        processing_message_id
                    )
                    assistant_message = (
                        msg_result.unwrap() if msg_result.is_success() else None
                    )

                    latency_ms = int((time.time() - context.start_time) * 1000)
                    completion_data = {
                        "user_message": context.user_message,
                        "assistant_message": assistant_message,
                        "latency_ms": latency_ms,
                    }
                    yield SSEFormatter.format_event(EventType.COMPLETE, completion_data)
                return

            if not self.server.service_container.phase_coordinator:
                log_event(
                    "phase_coordinator_not_initialized",
                    {"conversation_id": context.conversation_id},
                    level=logging.ERROR,
                )
                async for ev in dsp._handle_generation_error(
                    Exception("Hierarchical planner not initialized"), context
                ):
                    yield ev
                return

            coordinator = self.server.service_container.phase_coordinator
            progress_tracker = AgentProgressTracker()

            accumulated = []
            yield SSEFormatter.format_event(
                EventType.CONTEXT, {"note": "hierarchical_planning_started"}
            )
            async for ev in coordinator.execute_query(
                context.request.content, agent_ctx
            ):
                if context.is_cancelled:
                    log_event(
                        "gateway_detected_cancellation_in_loop",
                        {"conversation_id": context.conversation_id},
                    )
                    latency_ms = int((time.time() - context.start_time) * 1000)
                    yield SSEFormatter.format_event(
                        EventType.CANCELLED,
                        {
                            "reason": "Request was cancelled",
                            "latency_ms": latency_ms,
                            "completed_phases": progress_tracker.completed_phases,
                        },
                    )
                    if processing_message_id:
                        await dsp._mark_message_failed(processing_message_id)
                        await dsp._broadcast_message_status(
                            context.conversation_id, processing_message_id, "cancelled"
                        )
                    return

                et = ev.type.value if hasattr(ev, "type") else str(ev)
                if et == "plan_created":
                    plan_data = ev.data if isinstance(ev.data, dict) else {}
                    yield SSEFormatter.format_event(
                        EventType.METADATA, {"plan": plan_data}
                    )
                    if plan_data.get("type") == "strategic":
                        progress_event = progress_tracker.set_strategic_plan(plan_data)
                        yield SSEFormatter.format_event(
                            EventType.AGENT_PROGRESS, progress_event
                        )
                    elif plan_data.get("type") == "tactical":
                        phase_id = plan_data.get("phase_id")
                        if phase_id:
                            progress_event = progress_tracker.start_phase(phase_id)
                            yield SSEFormatter.format_event(
                                EventType.AGENT_PROGRESS, progress_event
                            )
                        progress_event = progress_tracker.set_tactical_plan(plan_data)
                        yield SSEFormatter.format_event(
                            EventType.AGENT_PROGRESS, progress_event
                        )
                elif et == "plan_failed":
                    log_event(
                        "agent_plan_failed",
                        {
                            "conversation_id": context.conversation_id,
                            "error": getattr(ev, "data", {}),
                        },
                    )
                    error_data = ev.data if isinstance(ev.data, dict) else {}
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS,
                        {
                            "event": "plan_failed",
                            "error": error_data.get("error", "Plan failed"),
                            "phases": progress_tracker.phases,
                            "current_phase_index": progress_tracker.current_phase_index,
                            "completed_phases": progress_tracker.completed_phases,
                            "is_synthesizing": False,
                        },
                    )
                elif et == "task_started":
                    task_data = ev.data if isinstance(ev.data, dict) else {}
                    task_id = ev.task_id or task_data.get("task_id", "")
                    tool_name = task_data.get("tool")
                    progress_event = progress_tracker.start_task(task_id, tool_name)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "task_completed":
                    task_id = ev.task_id or ""
                    progress_event = progress_tracker.complete_task(task_id)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "task_failed":
                    log_event(
                        "agent_task_failed",
                        {
                            "conversation_id": context.conversation_id,
                            "task_id": ev.task_id,
                            "error": getattr(ev, "data", {}),
                        },
                    )
                    task_id = ev.task_id or ""
                    error_data = ev.data if isinstance(ev.data, dict) else {}
                    progress_event = progress_tracker.fail_task(
                        task_id, error_data.get("error", "Task failed")
                    )
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "phase_completed":
                    phase_data = ev.data if isinstance(ev.data, dict) else {}
                    phase_id = phase_data.get("phase_id", "")
                    progress_event = progress_tracker.complete_phase(phase_id)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "synthesis_started":
                    log_event(
                        "agent_synthesis_started",
                        {"conversation_id": context.conversation_id},
                    )
                    progress_event = progress_tracker.start_synthesis()
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "response_chunk":
                    if isinstance(ev.data, Mapping):
                        chunk = str(ev.data.get("text", ""))
                    elif isinstance(ev.data, str):
                        chunk = ev.data
                    else:
                        chunk = str(ev.data)
                    accumulated.append(chunk)
                    yield SSEFormatter.format_event(EventType.CHUNK, {"text": chunk})
                elif et == "task_cancelled":
                    log_event(
                        "agent_task_cancelled",
                        {
                            "conversation_id": context.conversation_id,
                            "task_id": ev.task_id,
                        },
                    )
                    task_id = ev.task_id or ""
                    event_data = ev.data if isinstance(ev.data, dict) else {}
                    reason = event_data.get("reason", "Cancelled")
                    progress_event = progress_tracker.cancel_task(task_id, reason)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "phase_cancelled":
                    log_event(
                        "agent_phase_cancelled",
                        {
                            "conversation_id": context.conversation_id,
                            "phase_id": ev.data.get("phase_id") if ev.data else None,
                        },
                    )
                    event_data = ev.data if isinstance(ev.data, dict) else {}
                    phase_id = event_data.get("phase_id", "")
                    reason = event_data.get("reason", "Cancelled")
                    progress_event = progress_tracker.cancel_phase(phase_id, reason)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "plan_cancelled":
                    log_event(
                        "agent_plan_cancelled",
                        {
                            "conversation_id": context.conversation_id,
                            "reason": ev.data.get("reason") if ev.data else None,
                        },
                    )
                    event_data = ev.data if isinstance(ev.data, dict) else {}
                    reason = event_data.get("reason", "Cancelled")
                    progress_event = progress_tracker.cancel_plan(reason)
                    yield SSEFormatter.format_event(
                        EventType.AGENT_PROGRESS, progress_event
                    )
                elif et == "cancelled":
                    log_event(
                        "agent_cancelled",
                        {
                            "conversation_id": context.conversation_id,
                            "reason": ev.data.get("reason") if ev.data else None,
                        },
                    )
                    event_data = ev.data if isinstance(ev.data, dict) else {}
                    latency_ms = int((time.time() - context.start_time) * 1000)
                    yield SSEFormatter.format_event(
                        EventType.CANCELLED,
                        {
                            "reason": event_data.get("reason", "User requested cancellation"),
                            "latency_ms": latency_ms,
                            "completed_phases": progress_tracker.completed_phases,
                        },
                    )
                    if processing_message_id:
                        await dsp._mark_message_failed(processing_message_id)
                        await dsp._broadcast_message_status(
                            context.conversation_id, processing_message_id, "cancelled"
                        )
                    return
                elif et == "error":
                    log_event(
                        "agent_error",
                        {
                            "conversation_id": context.conversation_id,
                            "error": getattr(ev, "data", {}),
                        },
                    )
                    yield SSEFormatter.format_event(EventType.ERROR, ev.data)
                elif et == "complete":
                    log_event(
                        "agent_complete", {"conversation_id": context.conversation_id}
                    )
                    break

            context.accumulated_text = "".join(accumulated)
            if processing_message_id:
                await dsp._finalize_processing_message(
                    processing_message_id, context.accumulated_text or ""
                )
                await dsp._broadcast_message_status(
                    context.conversation_id,
                    processing_message_id,
                    "completed",
                    content=context.accumulated_text,
                )

                msg_service = self.server.service_container.message_service
                msg_result = await msg_service.get_message_with_citations(
                    processing_message_id
                )
                assistant_message = (
                    msg_result.unwrap() if msg_result.is_success() else None
                )

                latency_ms = int((time.time() - context.start_time) * 1000)
                completion_data = {
                    "user_message": context.user_message,
                    "assistant_message": assistant_message,
                    "latency_ms": latency_ms,
                }
                yield SSEFormatter.format_event(EventType.COMPLETE, completion_data)

        except asyncio.CancelledError:
            log_event(
                "gateway_cancelled",
                {
                    "conversation_id": context.conversation_id,
                },
            )
            latency_ms = int((time.time() - context.start_time) * 1000)
            yield SSEFormatter.format_event(
                EventType.CANCELLED,
                {
                    "reason": "Request was cancelled",
                    "latency_ms": latency_ms,
                },
            )
            if processing_message_id:
                await dsp._mark_message_failed(processing_message_id)
                await dsp._broadcast_message_status(
                    context.conversation_id, processing_message_id, "cancelled"
                )

        except Exception as e:
            log_event(
                "gateway_route_error",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            if processing_message_id:
                await dsp._mark_message_failed(processing_message_id)
                await dsp._broadcast_message_status(
                    context.conversation_id, processing_message_id, "failed"
                )
            async for event in dsp._handle_error(e, context):
                yield event
