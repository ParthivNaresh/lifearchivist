"""
Conversation API routes.

Provides REST endpoints for conversation management:
- Create conversations
- List conversations
- Get conversation details
- Update conversations
- Archive conversations
- Send messages (standard and streaming)
"""

from fastapi import APIRouter

from . import (
    archive,
    create,
    get,
    list,
    messages_list,
    messages_send,
    messages_stream,
    update,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

router.include_router(create.router)
router.include_router(list.router)
router.include_router(get.router)
router.include_router(update.router)
router.include_router(archive.router)
router.include_router(messages_send.router)
router.include_router(messages_stream.router)
router.include_router(messages_list.router)

__all__ = ["router"]
