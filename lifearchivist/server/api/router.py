"""
Main API router that aggregates all route modules.
"""

from fastapi import APIRouter

from lifearchivist.config import get_settings

from .routes.activity import router as activity_router
from .routes.conversations import router as conversations_router
from .routes.documents import router as documents_router
from .routes.enrichment import router as enrichment_router
from .routes.folder_watch import router as folder_watch_router
from .routes.providers import router as providers_router
from .routes.search import router as search_router
from .routes.search.ask import router as ask_router
from .routes.settings import router as settings_router
from .routes.tags import router as tags_router
from .routes.tags.topics import router as topics_router
from .routes.timeline import router as timeline_router
from .routes.upload import router as upload_router
from .routes.upload.bulk_ingest import router as bulk_ingest_router
from .routes.upload.ingest import router as ingest_router
from .routes.vault import router as vault_router


def get_api_router() -> APIRouter:
    """Get the API router with conditional route inclusion based on settings."""
    # Create the main API router
    api_router = APIRouter(prefix="/api")

    # Always include core API routes
    api_router.include_router(upload_router)
    api_router.include_router(ingest_router)
    api_router.include_router(bulk_ingest_router)
    api_router.include_router(search_router)
    api_router.include_router(ask_router)
    api_router.include_router(documents_router)
    api_router.include_router(conversations_router)
    api_router.include_router(tags_router)
    api_router.include_router(topics_router)
    api_router.include_router(vault_router)
    api_router.include_router(settings_router)
    api_router.include_router(enrichment_router)
    api_router.include_router(folder_watch_router)
    api_router.include_router(activity_router)
    api_router.include_router(timeline_router)
    api_router.include_router(providers_router)

    return api_router


def get_websocket_router() -> APIRouter:
    """Get the WebSocket router (separate from API routes)."""
    settings = get_settings()

    ws_router = APIRouter()

    if settings.enable_websockets:
        from .routes import websocket

        ws_router.include_router(websocket.router)

    return ws_router
