import json
from typing import Any

from lifearchivist.server.api.routes.conversations.misc_models import EventType
from lifearchivist.server.api.routes.conversations.utils import serialize_for_json


class SSEFormatter:
    """Formats data as Server-Sent Events."""

    @staticmethod
    def format_event(event_type: EventType, data: Any) -> str:
        """Format data as SSE event."""
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(serialize_for_json(data))
        else:
            data_str = json.dumps(data)
        return f"event: {event_type.value}\ndata: {data_str}\n\n"

    @staticmethod
    def format_error(error: str, error_type: str) -> str:
        """Format error as SSE event."""
        return SSEFormatter.format_event(
            EventType.ERROR, {"error": error, "error_type": error_type}
        )
