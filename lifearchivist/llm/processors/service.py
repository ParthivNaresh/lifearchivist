import asyncio


import time
from typing import Any, AsyncGenerator

from lifearchivist.llm.agent.cancellation import CancellationReason, CancellationToken
from lifearchivist.server.api.routes.conversations.misc_models import StreamContext
from lifearchivist.server.api.routes.conversations.request_models import (
    SendMessageRequest,
)
from lifearchivist.server.api.routes.shared.exceptions import ServiceUnavailableError
from lifearchivist.utils.logx import log_event

from .base import StreamProcessor
from .direct import DirectStreamProcessor
from .gateway import GatewayStreamProcessor


class StreamingService:
    """Main service for handling streaming."""

    def __init__(self, server: Any):
        self.server = server
        self._validate_base_services()

    def _validate_base_services(self) -> None:
        if not self.server.service_container:
            raise ServiceUnavailableError("Service Container")

    async def create_stream_with_token(
        self,
        conversation_id: str,
        request: SendMessageRequest,
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[str, None]:
        """
        Create and process stream with external cancellation token.

        This method allows the caller to provide a cancellation token that can be
        triggered externally (e.g., when client disconnects).
        """
        context = StreamContext(
            conversation_id=conversation_id,
            request=request,
            start_time=time.time(),
            cancellation_token=cancellation_token,
        )

        processor = self._get_processor()

        try:
            async for event in processor.process(context):
                if cancellation_token.is_cancelled:
                    log_event(
                        "streaming_service_token_cancelled",
                        {"conversation_id": conversation_id},
                    )
                    break
                yield event
        except asyncio.CancelledError:
            log_event(
                "streaming_service_cancelled",
                {"conversation_id": conversation_id},
            )
            cancellation_token.cancel(
                CancellationReason.USER_REQUESTED,
                "Stream cancelled",
            )
            raise
        except GeneratorExit:
            log_event(
                "streaming_service_generator_exit",
                {"conversation_id": conversation_id},
            )
            cancellation_token.cancel(
                CancellationReason.USER_REQUESTED,
                "Client disconnected",
            )
            raise

    def _get_processor(self) -> StreamProcessor:
        """Get appropriate stream processor."""
        if self.server.service_container and self.server.service_container.rag_service:
            return GatewayStreamProcessor(self.server)
        return DirectStreamProcessor(self.server)
