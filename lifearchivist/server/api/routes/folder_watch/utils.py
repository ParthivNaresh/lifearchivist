"""
Utility functions for folder watch endpoints.
"""

from lifearchivist.models.folder_watch import FolderResponse, WatchedFolder


def folder_to_response(folder: WatchedFolder) -> FolderResponse:
    """
    Convert WatchedFolder to FolderResponse.

    Centralizes the conversion logic to avoid duplication.

    Args:
        folder: WatchedFolder instance

    Returns:
        FolderResponse for API
    """
    return FolderResponse(
        id=folder.id,
        path=str(folder.path),
        enabled=folder.enabled,
        created_at=folder.created_at.isoformat(),
        status=folder.status.value,
        health=folder.stats.get_health_status().value,
        is_active=folder.is_active(),
        success_rate=folder.stats.get_success_rate(),
        stats=folder.stats.to_dict(),
    )
