from typing import Any, AsyncGenerator, Mapping, Optional

from ...server.api.routes.conversations.misc_models import EventType, StreamContext
from ...server.api.routes.shared.exceptions import ServiceUnavailableError
from ...utils.logx import log_event, track
from ...utils.sse import SSEFormatter
from ..agent import (
    AgentToolRegistry,
    ComplexityClassifier,
)
from ..agent import ConversationContext as AgentConversationContext
from ..agent import (
    PromptBuilder,
)
from ..processors.base import StreamProcessor
from ..processors.direct import DirectStreamProcessor


class GatewayStreamProcessor(StreamProcessor):
    def __init__(self, server: Any):
        self.server = server
        self._validate_services()
        log_event("gateway_processor_initialized")

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

    @track(operation="gateway_process")
    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        log_event("gateway_route_started", {"conversation_id": context.conversation_id})
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
                log_event(
                    "gateway_route_simple", {"conversation_id": context.conversation_id}
                )
                await dsp._perform_search(context)
                yield SSEFormatter.format_event(EventType.SOURCES, context.sources)
                config = await dsp._get_stream_config(context)
                messages = dsp._build_messages(context, config)
                async for event in dsp._stream_response(context, messages, config):
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
                log_event(
                    "gateway_route_completed",
                    {"conversation_id": context.conversation_id, "path": "simple"},
                )
                return

            tool_registry = AgentToolRegistry(
                document_service=(
                    self.server.service_container.llamaindex_service.document_service
                    if self.server.service_container.llamaindex_service
                    else None
                ),
                search_service=self.server.service_container.llamaindex_service.search_service,
                metadata_service=self.server.service_container.llamaindex_service.metadata_service,
            )
            try:
                if (
                    not hasattr(self.server.service_container, "agent_orchestrator")
                    or not self.server.service_container.agent_orchestrator
                ):
                    log_event(
                        "agent_orchestrator_initializing",
                        {"conversation_id": context.conversation_id},
                    )
                    self.server.service_container.init_agent_orchestrator(tool_registry)
                orchestrator = self.server.service_container.agent_orchestrator
                log_event(
                    "agent_orchestrator_initialized",
                    {"conversation_id": context.conversation_id},
                )
            except Exception as e:
                log_event(
                    "agent_orchestrator_init_failed",
                    {
                        "conversation_id": context.conversation_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                async for ev in dsp._handle_generation_error(e, context):
                    yield ev
                return

            accumulated = []
            log_event(
                "gateway_route_agent", {"conversation_id": context.conversation_id}
            )
            yield SSEFormatter.format_event(
                EventType.CONTEXT, {"note": "agent_orchestration_started"}
            )
            async for ev in orchestrator.process_query(
                context.request.content, agent_ctx
            ):
                et = ev.type.value if hasattr(ev, "type") else str(ev)
                if et == "plan_created":
                    log_event(
                        "agent_plan_created",
                        {"conversation_id": context.conversation_id},
                    )
                    yield SSEFormatter.format_event(
                        EventType.METADATA, {"plan": ev.data}
                    )
                elif et == "plan_failed":
                    log_event(
                        "agent_plan_failed",
                        {
                            "conversation_id": context.conversation_id,
                            "error": getattr(ev, "data", {}),
                        },
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
                elif et == "synthesis_started":
                    log_event(
                        "agent_synthesis_started",
                        {"conversation_id": context.conversation_id},
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
            log_event(
                "gateway_route_completed",
                {"conversation_id": context.conversation_id, "path": "agent"},
            )

            async for event in dsp._finalize_response(
                context,
                context.accumulated_text or "",
                tokens=0,
                finish_reason="stop",
            ):
                yield event

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
