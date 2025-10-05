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
    """Get vault information for development/debugging."""
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
        return stats
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.get("/vault/files")
async def list_vault_files(
    directory: str = "content", limit: int = 100, offset: int = 0
):
    """List files in vault for development/debugging with database record linking."""
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

    try:
        target_dir = vault_path / directory

        if not target_dir.exists():
            return {"files": [], "total": 0, "directory": directory}

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
                            matching_docs_result.unwrap()
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
            "files": paginated_files,
            "total": len(all_files),
            "directory": directory,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.post("/vault/reconcile")
async def reconcile_vault():
    """
    Reconcile vault files with metadata stores.
    
    Checks all documents in Redis and removes metadata for any documents
    whose vault files are missing. This ensures data consistency.
    
    Called by the UI refresh button to sync state after manual file operations.
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

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.get("/vault/file/{file_hash}")
async def download_file_from_vault(file_hash: str):
    """Download a file from vault by its hash."""
    server = get_server()

    try:
        if not server.vault:
            raise HTTPException(status_code=500, detail="Vault not initialized")

        # Build the path where the file should be stored
        # Files are stored in content/XX/YY/ZZZZ... format
        if len(file_hash) < 4:
            raise HTTPException(status_code=400, detail="Invalid file hash")

        content_dir = server.vault.content_dir
        # First 2 chars for first directory level
        dir1 = file_hash[:2]
        # Next 2 chars for second directory level
        dir2 = file_hash[2:4]
        # Rest of the hash for filename (without extension)
        file_stem = file_hash[4:]

        # Look for any file with this hash pattern
        file_dir = content_dir / dir1 / dir2

        if not file_dir.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Find the file (we don't know the extension)
        matching_files = list(file_dir.glob(f"{file_stem}.*"))

        if not matching_files:
            raise HTTPException(status_code=404, detail="File not found")

        # Use the first matching file
        file_path = matching_files[0]

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

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
                    matching_docs_result.unwrap()
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

        # For PDFs, images, and text files, we want to display inline
        # RTF files can sometimes display inline depending on browser
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
            # For Office files, browsers will download them
            # Use attachment disposition to ensure proper download
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
