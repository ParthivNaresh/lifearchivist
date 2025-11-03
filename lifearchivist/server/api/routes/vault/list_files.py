"""
List vault files endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/files")
async def list_vault_files(
    directory: str = "content", limit: int = 100, offset: int = 0
):
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
        return JSONResponse(
            content={
                "success": False,
                "error": "Vault path not configured",
                "error_type": "ConfigurationError",
            },
            status_code=500,
        )

    if limit < 1 or limit > 1000:
        return JSONResponse(
            content={
                "success": False,
                "error": "Limit must be between 1 and 1000",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if offset < 0:
        return JSONResponse(
            content={
                "success": False,
                "error": "Offset must be non-negative",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    try:
        target_dir = vault_path / directory

        if not target_dir.exists():
            return {
                "success": True,
                "files": [],
                "total": 0,
                "directory": directory,
                "limit": limit,
                "offset": offset,
            }

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
                            database_record = {
                                "id": doc.get("document_id"),
                                "original_path": metadata.get("original_path"),
                                "status": metadata.get("status"),
                            }
                    except Exception:
                        pass

                all_files.append(
                    {
                        "path": (
                            str(file_path.relative_to(vault_path))
                            if vault_path
                            else str(file_path)
                        ),
                        "full_path": str(file_path),
                        "hash": full_hash,
                        "extension": file_path.suffix.lstrip("."),
                        "size_bytes": stat.st_size,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime,
                        "database_record": database_record,
                    }
                )

        all_files.sort(key=lambda x: float(str(x.get("created_at", 0))), reverse=True)

        paginated_files = all_files[offset : offset + limit]

        return {
            "success": True,
            "files": paginated_files,
            "total": len(all_files),
            "directory": directory,
            "limit": limit,
            "offset": offset,
        }

    except PermissionError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Permission denied accessing vault directory: {str(e)}",
                "error_type": "PermissionError",
            },
            status_code=403,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to list vault files: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
