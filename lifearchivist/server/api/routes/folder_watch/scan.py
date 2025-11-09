"""
Scan folder endpoint.
"""

import logging

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .response_models import FolderScanResponse

router = APIRouter()
logger = logging.getLogger(__name__)

HIDDEN_FILE_PREFIXES = (".", "~", "__")


@router.post(
    "/folders/{folder_id}/scan",
    response_model=FolderScanResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Folder not enabled or not accessible",
            "content": {
                "application/json": {
                    "example": {"detail": "Folder must be enabled to scan"}
                }
            },
        },
        404: {
            "description": "Folder not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Folder not found: invalid-uuid"}
                }
            },
        },
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
                    "example": {"detail": "Scan folder failed: <error message>"}
                }
            },
        },
    },
)
async def scan_folder(
    folder_id: str = PathParam(..., description="Unique folder UUID"),
) -> FolderScanResponse:
    """
    Manually trigger a recursive scan of a watched folder.

    Scans the folder for all supported document types and queues them for ingestion.
    This is useful for processing existing files in a folder or re-scanning after
    adding new files while watching was disabled.

    ## Path Parameters

    - **folder_id**: Unique UUID of the watched folder to scan

    ## Response Fields

    - **success**: Whether the scan completed successfully
    - **folder_id**: UUID of the scanned folder
    - **folder_path**: Absolute path of the scanned folder
    - **files_found**: Total number of supported files found
    - **files_queued**: Number of files successfully queued for ingestion
    - **files_failed**: Number of files that failed to queue
    - **message**: Summary message

    ## Example Response

    ```json
    {
        "success": true,
        "folder_id": "123e4567-e89b-12d3-a456-426614174000",
        "folder_path": "/Users/username/Documents/ToIngest",
        "files_found": 25,
        "files_queued": 23,
        "files_failed": 2,
        "message": "Scan completed: 23 files queued for ingestion"
    }
    ```

    ## Scan Process

    1. **Verify Folder**: Check folder exists and is enabled
    2. **Recursive Search**: Find all files with supported extensions
    3. **Filter Hidden**: Exclude files starting with `.`, `~`, or `__`
    4. **Queue Files**: Schedule each file for ingestion
    5. **Deduplication**: System automatically skips already-ingested files
    6. **Return Results**: Report files found, queued, and failed

    ## Supported File Types

    The scan looks for these document types:
    - **Documents**: .pdf, .doc, .docx, .txt, .rtf, .odt
    - **Spreadsheets**: .xls, .xlsx, .csv
    - **Presentations**: .ppt, .pptx
    - **Images**: .jpg, .jpeg, .png, .gif, .bmp, .tiff
    - **Other**: .md, .html, .xml, .json

    ## Use Cases

    - Process existing files in a newly added folder
    - Re-scan folder after adding files while watching was disabled
    - Force re-check for new files
    - Recover from missed file events
    - Bulk import documents

    ## Important Notes

    - **Folder Must Be Enabled**: Returns 400 if folder is disabled
    - **Folder Must Exist**: Returns 400 if folder path is inaccessible
    - **Recursive Scan**: Searches all subdirectories
    - **Hidden Files Excluded**: Files starting with `.`, `~`, or `__` are skipped
    - **Deduplication**: Already-ingested files are automatically skipped
    - **Async Processing**: Files are queued, not processed immediately
    - **Debounce Applied**: Files are queued with configured debounce delay
    - **Partial Failures**: Some files may fail to queue (reported in files_failed)

    ## Performance Considerations

    - Large folders may take time to scan
    - Files are queued asynchronously for processing
    - Ingestion happens in background with concurrency limits
    - Scan operation itself is fast (just queuing)
    - Actual ingestion time depends on file count and size

    ## Error Handling

    - Returns 404 if folder UUID doesn't exist
    - Returns 400 if folder is disabled
    - Returns 400 if folder path is inaccessible
    - Individual file queueing failures are logged but don't fail the scan
    - Returns 200 with files_failed count if some files couldn't be queued

    ## Notes

    - Scan is idempotent - safe to run multiple times
    - Already-ingested files are automatically skipped
    - Enable folder first if currently disabled
    - Check folder health before scanning
    - Monitor files_failed count for issues
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", folder_id)

        if not folder.enabled:
            raise ValidationError("Folder must be enabled to scan")

        if not folder.path.exists() or not folder.path.is_dir():
            raise ValidationError(f"Folder path is not accessible: {folder.path}")

        files_found = []
        for ext in server.folder_watcher.SUPPORTED_EXTENSIONS:
            files_found.extend(folder.path.rglob(f"*{ext}"))

        files_found = [
            f
            for f in files_found
            if not any(f.name.startswith(prefix) for prefix in HIDDEN_FILE_PREFIXES)
        ]

        files_queued = 0
        files_failed = 0
        for file_path in files_found:
            try:
                await server.folder_watcher.schedule_ingestion(folder_id, file_path)
                files_queued += 1
            except Exception as e:
                logger.warning(
                    f"Failed to queue file {file_path.name} for ingestion: {e}"
                )
                files_failed += 1

        return FolderScanResponse(
            success=True,
            folder_id=folder_id,
            folder_path=str(folder.path),
            files_found=len(files_found),
            files_queued=files_queued,
            files_failed=files_failed,
            message=f"Scan completed: {files_queued} files queued for ingestion",
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Scan folder", e) from e
