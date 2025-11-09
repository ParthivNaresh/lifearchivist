"""
Get aggregate status endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import AggregateStatusResponse
from .utils import folder_to_response

router = APIRouter()


@router.get(
    "/status",
    response_model=AggregateStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Folder watcher service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Folder watcher not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get status failed: <error message>"}
                }
            },
        },
    },
)
async def get_aggregate_status() -> AggregateStatusResponse:
    """
    Get aggregate status and statistics across all watched folders.

    Returns comprehensive system-wide statistics including totals across all folders,
    individual folder details, supported file types, and system configuration.

    ## Response Fields

    - **success**: Whether the request succeeded (always true for 200 responses)
    - **total_folders**: Total number of registered folders
    - **active_folders**: Number of folders currently actively watching
    - **total_pending**: Total pending files across all folders
    - **total_detected**: Total files detected (all-time, all folders)
    - **total_ingested**: Total files successfully ingested (all-time, all folders)
    - **total_failed**: Total files that failed ingestion (all-time, all folders)
    - **total_bytes_processed**: Total bytes processed (all-time, all folders)
    - **folders**: Array of individual folder details (same as list endpoint)
    - **supported_extensions**: List of supported file extensions
    - **ingestion_concurrency**: Maximum concurrent ingestions across all folders

    ## Example Response

    ```json
    {
        "success": true,
        "total_folders": 3,
        "active_folders": 2,
        "total_pending": 5,
        "total_detected": 150,
        "total_ingested": 142,
        "total_failed": 8,
        "total_bytes_processed": 78643200,
        "folders": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "path": "/Users/username/Documents/ToIngest",
                "enabled": true,
                "created_at": "2025-01-08T12:00:00Z",
                "status": "active",
                "health": "healthy",
                "is_active": true,
                "success_rate": 0.98,
                "stats": {...}
            },
            {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "path": "/Users/username/Downloads",
                "enabled": true,
                "created_at": "2025-01-07T10:00:00Z",
                "status": "active",
                "health": "healthy",
                "is_active": true,
                "success_rate": 0.95,
                "stats": {...}
            },
            {
                "id": "323e4567-e89b-12d3-a456-426614174002",
                "path": "/Users/username/Desktop/Scans",
                "enabled": false,
                "created_at": "2025-01-06T08:00:00Z",
                "status": "stopped",
                "health": "healthy",
                "is_active": false,
                "success_rate": 1.0,
                "stats": {...}
            }
        ],
        "supported_extensions": [
            ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
            ".xls", ".xlsx", ".csv", ".ppt", ".pptx",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
            ".md", ".html", ".xml", ".json"
        ],
        "ingestion_concurrency": 3
    }
    ```

    ## Use Cases

    - Monitor overall system health
    - View aggregate statistics across all folders
    - Check how many folders are actively watching
    - See total files processed system-wide
    - Verify supported file types
    - Check concurrency configuration
    - Dashboard overview display

    ## Aggregate Statistics

    All statistics are cumulative since folders were added:
    - **total_detected**: Sum of all files detected by watchdog across all folders
    - **total_ingested**: Sum of all successfully ingested files
    - **total_failed**: Sum of all failed ingestion attempts
    - **total_bytes_processed**: Sum of all bytes processed
    - **total_pending**: Current pending files waiting for ingestion

    ## Folder Details

    The `folders` array contains complete details for each folder:
    - Same format as individual folder GET endpoint
    - Includes all statistics and health metrics
    - Shows current status and activity
    - Ordered by folder (no guaranteed order)

    ## System Configuration

    - **supported_extensions**: All file types the system can process
    - **ingestion_concurrency**: Max files processed simultaneously across all folders

    ## Performance Notes

    - Fast operation - just aggregates existing data
    - No file system scanning
    - No heavy computation
    - Safe to call frequently for monitoring
    - Suitable for dashboard polling

    ## Notes

    - Returns empty folders array if no folders registered
    - All statistics are cumulative (never reset)
    - Pending count is current snapshot
    - Active folders are those currently watching
    - Concurrency applies across all folders (not per-folder)
    - Supported extensions are system-wide configuration
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        aggregate = await server.folder_watcher.get_aggregate_status()
        folders = await server.folder_watcher.list_folders()
        folder_responses = [folder_to_response(folder) for folder in folders]

        return AggregateStatusResponse(
            success=True,
            total_folders=aggregate["total_folders"],
            active_folders=aggregate["active_folders"],
            total_pending=aggregate["total_pending"],
            total_detected=aggregate["total_detected"],
            total_ingested=aggregate["total_ingested"],
            total_failed=aggregate["total_failed"],
            total_bytes_processed=aggregate["total_bytes_processed"],
            folders=folder_responses,
            supported_extensions=aggregate["supported_extensions"],
            ingestion_concurrency=aggregate["ingestion_concurrency"],
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Get status", e) from e
