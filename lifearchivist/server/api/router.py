"""
Main API router that aggregates all route modules.
"""

from fastapi import APIRouter

from lifearchivist.config import get_settings

from .routes import documents, search, tags, upload, vault
from .routes import settings as settings_routes


def get_api_router() -> APIRouter:
    """Get the API router with conditional route inclusion based on settings."""
    settings = get_settings()

    # Create the main API router
    api_router = APIRouter()

    # Always include core API routes
    api_router.include_router(upload.router)
    api_router.include_router(search.router)
    api_router.include_router(documents.router)
    api_router.include_router(tags.router)
    api_router.include_router(vault.router)
    api_router.include_router(settings_routes.router)

    # Conditionally include WebSocket routes
    if settings.enable_websockets:
        from .routes import websocket

        api_router.include_router(websocket.router)

    return api_router
