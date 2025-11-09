"""
List vault files endpoint.
"""

from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

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


class VaultFileProcessor:
    """Processes vault files and their database records."""

    def __init__(self, server: Any, vault_path: Path, directory: str):
        self.server = server
        self.vault_path = vault_path
        self.directory = directory
        self.target_dir = vault_path / directory

    def validate_vault_path(self) -> None:
        """Validate vault path is configured."""
        if not self.vault_path:
            raise InternalServerError(
                "List vault files", RuntimeError("Vault path not configured")
            )

    def directory_exists(self) -> bool:
        """Check if target directory exists."""
        return self.target_dir.exists()

    async def collect_files(self) -> List[VaultFile]:
        """Collect all files from the target directory."""
        all_files = []
        for file_path in self.target_dir.rglob("*"):
            if file_path.is_file():
                vault_file = await self._process_single_file(file_path)
                all_files.append(vault_file)
        return all_files

    async def _process_single_file(self, file_path: Path) -> VaultFile:
        """Process a single file and create VaultFile object."""
        stat = file_path.stat()
        full_hash = self._compute_file_hash(file_path)
        database_record = await self._fetch_database_record(full_hash)

        return VaultFile(
            path=str(file_path.relative_to(self.vault_path)),
            full_path=str(file_path),
            hash=full_hash,
            extension=file_path.suffix.lstrip("."),
            size_bytes=stat.st_size,
            created_at=stat.st_ctime,
            modified_at=stat.st_mtime,
            database_record=database_record,
        )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute the full hash for a file based on its path."""
        file_hash = file_path.stem

        if self.directory != "content":
            return file_hash

        parent_dir = file_path.parent.name
        grandparent_dir = file_path.parent.parent.name
        return grandparent_dir + parent_dir + file_hash

    async def _fetch_database_record(self, full_hash: str) -> Optional[DatabaseRecord]:
        """Fetch database record for a file hash if available."""
        if not self.server.llamaindex_service:
            return None

        try:
            return await self._query_database_record(full_hash)
        except Exception:
            return None

    async def _query_database_record(self, full_hash: str) -> Optional[DatabaseRecord]:
        """Query database for a matching record."""
        matching_docs_result = (
            await self.server.llamaindex_service.query_documents_by_metadata(
                filters={"file_hash": full_hash}, limit=1
            )
        )

        matching_docs = (
            matching_docs_result.value if matching_docs_result.is_success() else []
        )

        if not matching_docs:
            return None

        doc = matching_docs[0]
        metadata = doc.get("metadata", {})

        return DatabaseRecord(
            id=doc.get("document_id", ""),
            original_path=metadata.get("original_path"),
            status=metadata.get("status"),
        )

    def sort_and_paginate(
        self, files: List[VaultFile], limit: int, offset: int
    ) -> List[VaultFile]:
        """Sort files by creation time and apply pagination."""
        files.sort(key=lambda x: x.created_at, reverse=True)
        return files[offset : offset + limit]


class VaultFileHandler:
    """Handles the vault file listing workflow."""

    def __init__(self, server: Any, directory: str, limit: int, offset: int):
        self.server = server
        self.directory = directory
        self.limit = limit
        self.offset = offset
        self.vault_path = server.settings.vault_path

    async def list_files(self) -> ListVaultFilesResponse:
        """List vault files with database record linking."""
        processor = VaultFileProcessor(self.server, self.vault_path, self.directory)
        processor.validate_vault_path()

        if not processor.directory_exists():
            return self._empty_response()

        try:
            all_files = await processor.collect_files()
            paginated_files = processor.sort_and_paginate(
                all_files, self.limit, self.offset
            )

            return self._create_response(paginated_files, len(all_files))

        except PermissionError as e:
            self._handle_permission_error(e)
            raise  # This line will never be reached but satisfies mypy

    def _empty_response(self) -> ListVaultFilesResponse:
        """Create an empty response when directory doesn't exist."""
        return ListVaultFilesResponse(
            files=[],
            total=0,
            directory=self.directory,
            limit=self.limit,
            offset=self.offset,
        )

    def _create_response(
        self, files: List[VaultFile], total: int
    ) -> ListVaultFilesResponse:
        """Create the final response with files."""
        return ListVaultFilesResponse(
            files=files,
            total=total,
            directory=self.directory,
            limit=self.limit,
            offset=self.offset,
        )

    def _handle_permission_error(self, error: PermissionError) -> None:
        """Handle permission errors when accessing vault directory."""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied accessing vault directory: {str(error)}",
        ) from error


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
    try:
        server = get_server()
        handler = VaultFileHandler(server, directory, limit, offset)
        return await handler.list_files()

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError("List vault files", e) from e
