"""
Vault reconciliation service for maintaining data consistency.

This module ensures that Redis/Qdrant metadata stays in sync with actual vault files.
The policy is simple: if a vault file is missing, remove the orphaned metadata.
"""

import logging
from typing import Any, Dict, List, Optional

from lifearchivist.utils.logging import log_event


class VaultReconciliationService:
    """
    Service for reconciling vault files with metadata stores.
    
    Policy: Vault files are the source of truth. If a file is missing,
    remove the corresponding metadata from Redis and Qdrant.
    """

    def __init__(self, vault, doc_tracker, qdrant_client):
        """
        Initialize the reconciliation service.
        
        Args:
            vault: Vault instance for file operations
            doc_tracker: Document tracker (Redis) for metadata
            qdrant_client: Qdrant client for vector operations
        """
        self.vault = vault
        self.doc_tracker = doc_tracker
        self.qdrant_client = qdrant_client

    async def reconcile(self) -> Dict[str, Any]:
        """
        Reconcile vault files with metadata stores.
        
        Checks all documents in Redis and removes metadata for any
        documents whose vault files are missing.
        
        Returns:
            Dict with reconciliation statistics:
                - checked: Number of documents checked
                - cleaned: Number of orphaned metadata entries removed
                - errors: Number of errors encountered
                - cleaned_documents: List of cleaned document info
        """
        cleaned_documents = []
        errors = []
        
        try:
            # Get all documents from Redis
            all_doc_ids = await self.doc_tracker.get_all_document_ids()
            
            log_event(
                "vault_reconciliation_started",
                {"total_documents": len(all_doc_ids)},
            )
            
            for doc_id in all_doc_ids:
                try:
                    # Check if this document's file exists
                    cleanup_result = await self._check_and_cleanup_document(doc_id)
                    
                    if cleanup_result:
                        cleaned_documents.append(cleanup_result)
                        
                except Exception as e:
                    errors.append({
                        "document_id": doc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    })
                    log_event(
                        "reconciliation_document_error",
                        {
                            "document_id": doc_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        level=logging.ERROR,
                    )
            
            result = {
                "checked": len(all_doc_ids),
                "cleaned": len(cleaned_documents),
                "errors": len(errors),
                "cleaned_documents": cleaned_documents,
                "error_details": errors if errors else None,
            }
            
            # Log completion
            if cleaned_documents:
                log_event(
                    "vault_reconciliation_completed_with_cleanup",
                    {
                        "checked": len(all_doc_ids),
                        "cleaned": len(cleaned_documents),
                        "errors": len(errors),
                    },
                    level=logging.WARNING,
                )
            else:
                log_event(
                    "vault_reconciliation_completed",
                    {
                        "checked": len(all_doc_ids),
                        "status": "consistent",
                        "errors": len(errors),
                    },
                )
            
            return result
            
        except Exception as e:
            log_event(
                "vault_reconciliation_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return {
                "checked": 0,
                "cleaned": 0,
                "errors": 1,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def _check_and_cleanup_document(
        self, doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a document's vault file exists and clean up if missing.
        
        Args:
            doc_id: Document ID to check
            
        Returns:
            Dict with cleanup info if document was cleaned, None otherwise
        """
        # Get metadata to find file hash
        metadata = await self.doc_tracker.get_full_metadata(doc_id)
        if not metadata:
            return None
        
        file_hash = metadata.get("file_hash")
        if not file_hash:
            log_event(
                "document_missing_file_hash",
                {"document_id": doc_id},
                level=logging.WARNING,
            )
            return None
        
        # Check if vault file exists
        file_exists = await self.vault.file_exists(file_hash)
        
        if file_exists:
            # File exists, no cleanup needed
            return None
        
        # File missing - clean up metadata
        log_event(
            "orphaned_metadata_detected",
            {
                "document_id": doc_id,
                "file_hash": file_hash,
                "title": metadata.get("title", "Unknown"),
                "action": "removing_metadata",
            },
            level=logging.WARNING,
        )
        
        # Delete from Qdrant
        qdrant_deleted = False
        if self.qdrant_client:
            try:
                from qdrant_client.models import FieldCondition, Filter, MatchValue
                
                self.qdrant_client.delete(
                    collection_name="lifearchivist",
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=doc_id),
                            )
                        ]
                    ),
                )
                qdrant_deleted = True
            except Exception as e:
                log_event(
                    "qdrant_cleanup_failed",
                    {
                        "document_id": doc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    level=logging.ERROR,
                )
        
        # Delete from Redis
        redis_deleted = False
        try:
            await self.doc_tracker.remove_document(doc_id)
            redis_deleted = True
        except Exception as e:
            log_event(
                "redis_cleanup_failed",
                {
                    "document_id": doc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
        
        return {
            "document_id": doc_id,
            "file_hash": file_hash,
            "title": metadata.get("title", "Unknown"),
            "original_path": metadata.get("original_path", "Unknown"),
            "redis_deleted": redis_deleted,
            "qdrant_deleted": qdrant_deleted,
        }

    async def get_orphaned_files(self) -> List[Dict[str, Any]]:
        """
        Find vault files that don't have corresponding metadata.
        
        This is the opposite check - files without metadata.
        These are harmless but waste disk space.
        
        Returns:
            List of orphaned file info dicts
        """
        orphaned_files = []
        
        try:
            # Get all file hashes from vault
            vault_files = await self.vault.list_all_files()
            
            # Get all file hashes from Redis
            all_doc_ids = await self.doc_tracker.get_all_document_ids()
            known_hashes = set()
            
            for doc_id in all_doc_ids:
                metadata = await self.doc_tracker.get_full_metadata(doc_id)
                if metadata and metadata.get("file_hash"):
                    known_hashes.add(metadata["file_hash"])
            
            # Find files not in Redis
            for file_info in vault_files:
                file_hash = file_info.get("hash")
                if file_hash and file_hash not in known_hashes:
                    orphaned_files.append(file_info)
            
            log_event(
                "orphaned_files_check_completed",
                {
                    "total_files": len(vault_files),
                    "orphaned_files": len(orphaned_files),
                },
            )
            
            return orphaned_files
            
        except Exception as e:
            log_event(
                "orphaned_files_check_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return []
