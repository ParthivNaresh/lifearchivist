from abc import ABC, abstractmethod
from typing import AsyncGenerator

from lifearchivist.server.api.routes.conversations.misc_models import StreamContext


class StreamProcessor(ABC):
    """Abstract base class for stream processors."""

    @abstractmethod
    def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        """Process the stream."""
        ...
