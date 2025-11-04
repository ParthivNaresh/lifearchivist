"""
Utility functions for conversation endpoints.
"""

from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import UUID

from fastapi.responses import JSONResponse

from ..shared.responses import service_unavailable_response


def serialize_for_json(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable types.

    Handles:
    - UUID -> str
    - datetime -> ISO format str
    - dict -> recursively serialize values
    - list -> recursively serialize items
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


def validate_conversation_service(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate conversation service availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        return None, service_unavailable_response("Conversation service")

    return server.service_container.conversation_service, None


def validate_message_service(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate message service availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not server.service_container or not server.service_container.message_service:
        return None, service_unavailable_response("Message service")

    return server.service_container.message_service, None


def validate_llamaindex_service(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate LlamaIndex service availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not server.service_container or not server.service_container.llamaindex_service:
        return None, service_unavailable_response("LlamaIndex service")

    return server.service_container.llamaindex_service, None
