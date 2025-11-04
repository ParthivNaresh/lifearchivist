"""
Get conversation endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import success_response
from ..shared.utils import handle_service_result
from .utils import validate_conversation_service

router = APIRouter()


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    include_messages: bool = True,
    message_limit: int = 50,
):
    """
    Get a conversation by ID.

    Optionally includes message history.
    """
    server = get_server()
    conv_service, error_response = validate_conversation_service(server)
    if error_response:
        return error_response

    assert conv_service is not None

    conv_result = await conv_service.get_conversation(conversation_id)

    error_response = handle_service_result(conv_result)
    if error_response:
        return error_response

    conversation = conv_result.unwrap()

    if include_messages and server.service_container:
        msg_service = server.service_container.message_service
        if msg_service:
            msg_result = await msg_service.get_messages(
                conversation_id=conversation_id,
                limit=message_limit,
                offset=0,
                include_citations=True,
            )

            if msg_result.is_success():
                messages_data = msg_result.unwrap()
                conversation["messages"] = messages_data["messages"]
                conversation["message_count"] = messages_data["total"]
            else:
                conversation["messages"] = []
                conversation["message_count"] = 0

    return success_response(
        {
            "conversation": conversation,
        }
    )
