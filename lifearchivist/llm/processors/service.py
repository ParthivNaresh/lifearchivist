import time
from typing import Any, AsyncGenerator

from lifearchivist.server.api.routes.conversations.misc_models import StreamContext
from lifearchivist.server.api.routes.conversations.request_models import (
    SendMessageRequest,
)
from lifearchivist.server.api.routes.shared.exceptions import ServiceUnavailableError

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

    async def create_stream(
        self, conversation_id: str, request: SendMessageRequest
    ) -> AsyncGenerator[str, None]:
        """Create and process stream."""
        context = StreamContext(
            conversation_id=conversation_id,
            request=request,
            start_time=time.time(),
        )

        processor = self._get_processor()
        async for event in processor.process(context):
            yield event

    def _get_processor(self) -> StreamProcessor:
        """Get appropriate stream processor."""
        if self.server.service_container and self.server.service_container.rag_service:
            return GatewayStreamProcessor(self.server)
        return DirectStreamProcessor(self.server)
