from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam
from pydantic import BaseModel

from .....utils.logx import log_event
from .cancellation_registry import get_cancellation_registry

router = APIRouter()


class CancelResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/{conversation_id}/messages/cancel",
    response_model=CancelResponse,
    responses={
        200: {
            "description": "Cancellation request processed",
            "content": {
                "application/json": {
                    "example": {"success": True, "message": "Request cancelled"}
                }
            },
        },
        404: {
            "description": "No active stream found for conversation",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No active stream found",
                    }
                }
            },
        },
    },
)
async def cancel_message_stream(
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> CancelResponse:
    registry = get_cancellation_registry()

    log_event(
        "cancel_request_received",
        {"conversation_id": conversation_id},
    )

    if not registry.is_active(conversation_id):
        log_event(
            "cancel_request_no_active_stream",
            {"conversation_id": conversation_id},
        )
        raise HTTPException(
            status_code=404,
            detail="No active stream found for this conversation",
        )

    success = registry.cancel(conversation_id, "User requested cancellation via API")

    if success:
        log_event(
            "cancel_request_success",
            {"conversation_id": conversation_id},
        )
        return CancelResponse(success=True, message="Request cancelled")

    log_event(
        "cancel_request_failed",
        {"conversation_id": conversation_id},
    )
    return CancelResponse(success=False, message="Failed to cancel request")
