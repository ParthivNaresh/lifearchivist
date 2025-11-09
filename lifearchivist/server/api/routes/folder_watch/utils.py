"""
Utility functions for folder watch endpoints.
"""

from .misc_models import WatchedFolder
from .response_models import FolderResponse, FolderStatsResponse


def folder_to_response(folder: WatchedFolder) -> FolderResponse:
    """
    Convert WatchedFolder to FolderResponse.

    Centralizes the conversion logic to avoid duplication.

    Args:
        folder: WatchedFolder instance

    Returns:
        FolderResponse for API
    """
    stats_dict = folder.stats.to_dict()
    stats = FolderStatsResponse(**stats_dict)

    return FolderResponse(
        id=folder.id,
        path=str(folder.path),
        enabled=folder.enabled,
        created_at=folder.created_at.isoformat(),
        status=folder.status.value,
        health=folder.stats.get_health_status().value,
        is_active=folder.is_active(),
        success_rate=folder.stats.get_success_rate(),
        stats=stats,
    )
