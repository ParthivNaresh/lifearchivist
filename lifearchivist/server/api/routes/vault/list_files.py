"""
List vault files endpoint.
"""

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError
from .constants import (
    DEFAULT_DIRECTORY,
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    MAX_LIMIT,
    MIN_LIMIT,
)
from .misc_models import DatabaseRecord, VaultFile
from .response_models import ListVaultFilesResponse

router = APIRouter()


@router.get(
    "/files",
    response_model=ListVaultFilesResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Limit must be between 1 and 1000"}
                }
            },
        },
        403: {
            "description": "Permission denied",
            "content": {
                "application/json": {
                    "example": {"detail": "Permission denied accessing vault directory"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "List vault files failed: <error>"}
                }
            },
        },
    },
)
async def list_vault_files(
    directory: str = Query(
        default=DEFAULT_DIRECTORY, description="Vault subdirectory to list"
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum files to return",
    ),
    offset: int = Query(default=DEFAULT_OFFSET, ge=0, description="Pagination offset"),
) -> ListVaultFilesResponse:
    """
    List files in vault with database record linking.

    Args:
        directory: Vault subdirectory to list (default: "content")
        limit: Maximum files to return (default: 100, max: 1000)
        offset: Pagination offset (default: 0)

    Returns:
        List of files with:
        - File path and hash
        - Size and timestamps
        - Linked database record (if exists)
        - Extension and metadata

    Useful for:
    - Debugging storage issues
    - Verifying file-to-record mappings
    - Identifying orphaned files
    """
    server = get_server()

    vault_path = server.settings.vault_path
    if not vault_path:
        raise InternalServerError(
            "List vault files", RuntimeError("Vault path not configured")
        )

    try:
        target_dir = vault_path / directory

        if not target_dir.exists():
            return ListVaultFilesResponse(
                files=[],
                total=0,
                directory=directory,
                limit=limit,
                offset=offset,
            )

        all_files = []
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()

                file_hash = file_path.stem
                if directory == "content":
                    parent_dir = file_path.parent.name
                    grandparent_dir = file_path.parent.parent.name
                    full_hash = grandparent_dir + parent_dir + file_hash
                else:
                    full_hash = file_hash

                database_record = None
                if server.llamaindex_service:
                    try:
                        matching_docs_result = (
                            await server.llamaindex_service.query_documents_by_metadata(
                                filters={"file_hash": full_hash}, limit=1
                            )
                        )
                        matching_docs = (
                            matching_docs_result.value
                            if matching_docs_result.is_success()
                            else []
                        )
                        if matching_docs:
                            doc = matching_docs[0]
                            metadata = doc.get("metadata", {})
                            database_record = DatabaseRecord(
                                id=doc.get("document_id", ""),
                                original_path=metadata.get("original_path"),
                                status=metadata.get("status"),
                            )
                    except Exception:
                        pass

                all_files.append(
                    VaultFile(
                        path=(
                            str(file_path.relative_to(vault_path))
                            if vault_path
                            else str(file_path)
                        ),
                        full_path=str(file_path),
                        hash=full_hash,
                        extension=file_path.suffix.lstrip("."),
                        size_bytes=stat.st_size,
                        created_at=stat.st_ctime,
                        modified_at=stat.st_mtime,
                        database_record=database_record,
                    )
                )

        all_files.sort(key=lambda x: x.created_at, reverse=True)

        paginated_files = all_files[offset : offset + limit]

        return ListVaultFilesResponse(
            files=paginated_files,
            total=len(all_files),
            directory=directory,
            limit=limit,
            offset=offset,
        )

    except PermissionError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied accessing vault directory: {str(e)}",
        ) from e
    except Exception as e:
        raise InternalServerError("List vault files", e) from e
