import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import Request
from fastapi.responses import StreamingResponse

from .....llm.agent.cancellation import CancellationReason, CancellationToken
from .....llm.processors.service import StreamingService
from .....utils.logx import log_event
from ..shared.dependencies import get_server
from .cancellation_registry import get_cancellation_registry
from .request_models import SendMessageRequest

router = APIRouter()
logger = logging.getLogger(__name__)


async def _stream_with_disconnect_detection(
    service: StreamingService,
    conversation_id: str,
    request_body: SendMessageRequest,
    http_request: Request,
) -> AsyncGenerator[str, None]:
    cancellation_token = CancellationToken()
    registry = get_cancellation_registry()

    registry.register(conversation_id, cancellation_token)

    async def monitor_disconnect() -> None:
        try:
            while not cancellation_token.is_cancelled:
                if await http_request.is_disconnected():
                    log_event(
                        "client_disconnected",
                        {"conversation_id": conversation_id},
                    )
                    cancellation_token.cancel(
                        CancellationReason.USER_REQUESTED,
                        "Client disconnected",
                    )
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            log_event(
                "disconnect_monitor_error",
                {"conversation_id": conversation_id, "error": str(e)},
            )

    monitor_task = asyncio.create_task(monitor_disconnect())

    try:
        async for event in service.create_stream_with_token(
            conversation_id, request_body, cancellation_token
        ):
            if cancellation_token.is_cancelled:
                log_event(
                    "stream_cancelled_by_token",
                    {"conversation_id": conversation_id},
                )
                break
            yield event
    except asyncio.CancelledError:
        log_event(
            "stream_cancelled_error",
            {"conversation_id": conversation_id},
        )
        cancellation_token.cancel(
            CancellationReason.USER_REQUESTED,
            "Stream cancelled",
        )
    finally:
        registry.unregister(conversation_id)
        cancellation_token.cancel(
            CancellationReason.USER_REQUESTED,
            "Stream ended",
        )
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


@router.post(
    "/{conversation_id}/messages/stream",
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        503: {
            "description": "Required service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Service container not available"}
                }
            },
        },
    },
)
async def send_message_streaming(
    request: SendMessageRequest,
    http_request: Request,
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> StreamingResponse:
    server = get_server()
    service = StreamingService(server)

    return StreamingResponse(
        _stream_with_disconnect_detection(
            service, conversation_id, request, http_request
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
