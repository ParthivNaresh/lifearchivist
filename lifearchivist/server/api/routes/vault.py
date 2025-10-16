"""
Vault management endpoints.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from lifearchivist.storage.vault_reconciliation import VaultReconciliationService

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["vault"])


@router.get("/vault/info")
async def get_vault_info():
    """
    Get vault information and statistics.

    Returns:
    - Total file count
    - Total storage size
    - File type distribution
    - Directory structure info

    Useful for:
    - Monitoring storage usage
    - Debugging storage issues
    - System health checks
    """
    server = get_server()

    if not server.vault:
        return JSONResponse(
            content={
                "success": False,
                "error": "Vault not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        stats = await server.vault.get_vault_statistics()
        return {"success": True, **stats}
    except AttributeError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Vault statistics unavailable: {str(e)}",
                "error_type": "ServiceError",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve vault info: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.get("/vault/files")
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

    # Validate parameters
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

        # Get all files in the directory
        all_files = []
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()

                # Extract hash from filename (remove extension)
                file_hash = file_path.stem
                if directory == "content":
                    # For content files, reconstruct the full hash from directory structure
                    # Path structure: content/93/31/eb7c1d80252e853314bfcb5eba2effb7b163378503f39be03f9dc66fc5d6.pdf
                    # Full hash: 9331eb7c1d80252e853314bfcb5eba2effb7b163378503f39be03f9dc66fc5d6
                    parent_dir = file_path.parent.name  # "31"
                    grandparent_dir = file_path.parent.parent.name  # "93"
                    full_hash = grandparent_dir + parent_dir + file_hash
                else:
                    full_hash = file_hash

                # Look up database record by file_hash
                database_record = None
                if server.llamaindex_service:
                    try:
                        # Query LlamaIndex for documents with this file hash
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
                        # If lookup fails, continue without database record
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

        # Sort by creation time (newest first)
        all_files.sort(key=lambda x: float(str(x.get("created_at", 0))), reverse=True)

        # Apply pagination
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


@router.post("/vault/reconcile")
async def reconcile_vault():
    """
    Reconcile vault files with metadata stores.

    Self-healing operation that:
    - Scans all documents in Redis metadata store
    - Checks if corresponding vault files exist
    - Removes orphaned metadata for missing files
    - Ensures data consistency across storage layers

    Vault files are the source of truth.

    Triggered by:
    - UI refresh button
    - Manual file operations
    - System maintenance

    Returns:
    - Documents checked
    - Orphaned metadata removed
    - Reconciliation statistics
    """
    server = get_server()

    if not server.vault:
        return JSONResponse(
            content={
                "success": False,
                "error": "Vault not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "LlamaIndex service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        # Create reconciliation service
        reconciliation_service = VaultReconciliationService(
            vault=server.vault,
            doc_tracker=server.llamaindex_service.doc_tracker,
            qdrant_client=server.llamaindex_service.qdrant_client,
        )

        # Run reconciliation
        result = await reconciliation_service.reconcile()

        return {
            "success": True,
            "reconciliation": result,
        }

    except AttributeError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Reconciliation service configuration error: {str(e)}",
                "error_type": "ConfigurationError",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Vault reconciliation failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.get("/vault/file/{file_hash}")
async def download_file_from_vault(file_hash: str):
    """
    Download or view a file from vault by its SHA256 hash.

    Args:
        file_hash: Full SHA256 hash of the file (64 characters)

    Returns:
        FileResponse with appropriate Content-Disposition:
        - inline: PDFs, images, text files (viewable in browser)
        - attachment: Office docs, other files (force download)

    Process:
    1. Validates hash format
    2. Locates file in content-addressed storage
    3. Retrieves original filename from metadata
    4. Sets appropriate MIME type
    5. Returns file with proper headers

    Vault structure: content/XX/YY/ZZZZ...{ext}
    where XXYYZZZZ... is the SHA256 hash split for directory sharding.
    """
    server = get_server()

    try:
        if not server.vault:
            raise HTTPException(status_code=503, detail="Vault not initialized")

        # Validate hash format
        if not file_hash or len(file_hash) < 4:
            raise HTTPException(
                status_code=400,
                detail="Invalid file hash format. Expected SHA256 hash (64 characters).",
            )

        if len(file_hash) != 64:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hash length: {len(file_hash)}. Expected 64 characters.",
            )

        content_dir = server.vault.content_dir

        # Parse hash into directory structure
        # First 2 chars for first directory level
        dir1 = file_hash[:2]
        # Next 2 chars for second directory level
        dir2 = file_hash[2:4]
        # Rest of the hash for filename (without extension)
        file_stem = file_hash[4:]

        # Look for any file with this hash pattern
        file_dir = content_dir / dir1 / dir2

        if not file_dir.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found for hash: {file_hash}"
            )

        # Find the file (we don't know the extension)
        matching_files = list(file_dir.glob(f"{file_stem}.*"))

        if not matching_files:
            raise HTTPException(
                status_code=404, detail=f"File not found for hash: {file_hash}"
            )

        # Use the first matching file
        file_path = matching_files[0]

        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found for hash: {file_hash}"
            )

        # Get the original filename from metadata if available
        filename = file_path.name
        if server.llamaindex_service:
            try:
                # Try to get original filename from metadata
                matching_docs_result = (
                    await server.llamaindex_service.query_documents_by_metadata(
                        filters={"file_hash": file_hash}, limit=1
                    )
                )
                matching_docs = (
                    matching_docs_result.value
                    if matching_docs_result.is_success()
                    else []
                )
                if matching_docs:
                    metadata = matching_docs[0].get("metadata", {})
                    original_path = metadata.get("original_path", "")
                    if original_path:
                        filename = Path(original_path).name
            except Exception:
                # If lookup fails, use the hash-based filename
                pass

        # Determine the correct media type based on file extension
        extension = file_path.suffix.lower()
        media_type = "application/octet-stream"  # default

        # Set appropriate media types for common formats
        if extension == ".pdf":
            media_type = "application/pdf"
        elif extension in [".jpg", ".jpeg"]:
            media_type = "image/jpeg"
        elif extension == ".png":
            media_type = "image/png"
        elif extension == ".gif":
            media_type = "image/gif"
        elif extension == ".webp":
            media_type = "image/webp"
        elif extension in [".txt", ".text"]:
            media_type = "text/plain"
        elif extension == ".rtf":
            media_type = "application/rtf"
        elif extension in [".doc", ".docx"]:
            media_type = "application/msword"
        elif extension in [".xls", ".xlsx"]:
            media_type = "application/vnd.ms-excel"

        # For PDFs, images, and text files, display inline in browser
        if extension in [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".txt",
            ".text",
            ".rtf",
        ]:
            return FileResponse(
                path=str(file_path),
                media_type=media_type,
                headers={"Content-Disposition": f'inline; filename="{filename}"'},
            )
        elif extension in [".doc", ".docx", ".xls", ".xlsx"]:
            # For Office files, force download
            return FileResponse(
                path=str(file_path),
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        else:
            # For other file types, allow download
            return FileResponse(
                path=str(file_path), filename=filename, media_type=media_type
            )

    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(
            status_code=403, detail=f"Permission denied accessing file: {str(e)}"
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve file: {str(e)}"
        ) from None
