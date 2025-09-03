"""
Factory for creating API response objects for testing.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class ResponseFactory:
    """Factory for creating API response objects for testing."""
    
    @classmethod
    def create_successful_upload_response(
        self,
        file_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_size: int = 1024,
        mime_type: str = "text/plain",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a successful file upload response."""
        if file_id is None:
            file_id = f"file_{uuid.uuid4().hex[:12]}"
        
        if file_hash is None:
            file_hash = f"hash_{uuid.uuid4().hex}"
        
        return {
            "file_id": file_id,
            "hash": file_hash,
            "size": file_size,
            "mime_type": mime_type,
            "status": "completed",
            "metadata": {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_time_ms": 1500,
            },
            **kwargs
        }
    
    @classmethod
    def create_ingest_response(
        self,
        file_id: Optional[str] = None,
        status: str = "completed",
        **kwargs
    ) -> Dict[str, Any]:
        """Create an ingest response."""
        if file_id is None:
            file_id = f"ingested_{uuid.uuid4().hex[:12]}"
        
        return {
            "file_id": file_id,
            "status": status,
            "ingestion_stats": {
                "text_extracted": True,
                "embeddings_created": True,
                "indexed": True,
            },
            **kwargs
        }
    
    @classmethod
    def create_bulk_ingest_response(
        self,
        total_files: int = 3,
        successful_count: int = 2,
        failed_count: int = 1,
        folder_path: str = "/tmp/test_folder",
    ) -> Dict[str, Any]:
        """Create a bulk ingest response."""
        results = []
        
        # Add successful results
        for i in range(successful_count):
            results.append({
                "file_path": f"{folder_path}/file_{i+1}.txt",
                "success": True,
                "file_id": f"bulk_file_{i+1}_{uuid.uuid4().hex[:8]}",
                "status": "completed",
            })
        
        # Add failed results
        for i in range(failed_count):
            results.append({
                "file_path": f"{folder_path}/failed_file_{i+1}.txt",
                "success": False,
                "error": "File processing failed",
            })
        
        return {
            "success": True,
            "total_files": total_files,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "folder_path": folder_path,
            "results": results,
        }
    
    @classmethod
    def create_search_response(
        self,
        results_count: int = 3,
        query: str = "test query",
        mode: str = "keyword",
        query_time_ms: int = 45,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a search response."""
        results = []
        
        for i in range(results_count):
            result = {
                "document_id": f"doc_{uuid.uuid4().hex[:12]}",
                "title": f"Test Document {i+1}",
                "snippet": f"This is a snippet from document {i+1} containing relevant content...",
                "score": 0.95 - (i * 0.1),  # Decreasing scores
                "metadata": {
                    "mime_type": "text/plain",
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "tags": ["test", f"doc{i+1}"],
                },
            }
            results.append(result)
        
        return {
            "results": results,
            "total": results_count,
            "query_time_ms": query_time_ms,
            "mode": mode,
            "query": query,
            **kwargs
        }
    
    @classmethod
    def create_ask_response(
        self,
        answer: str = "This is a test answer from the Q&A system.",
        confidence: float = 0.87,
        citations_count: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a Q&A response."""
        citations = []
        
        for i in range(citations_count):
            citation = {
                "doc_id": f"cited_doc_{uuid.uuid4().hex[:8]}",
                "title": f"Source Document {i+1}",
                "snippet": f"Relevant snippet from source document {i+1}...",
                "score": 0.9 - (i * 0.05),
            }
            citations.append(citation)
        
        return {
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "method": "llamaindex_tool",
            "context_length": citations_count,
            **kwargs
        }
    
    @classmethod
    def create_documents_list_response(
        self,
        documents_count: int = 5,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a documents list response."""
        documents = []
        
        for i in range(documents_count):
            document = {
                "document_id": f"list_doc_{uuid.uuid4().hex[:8]}",
                "title": f"Listed Document {i+1}",
                "mime_type": "text/plain",
                "file_size": 1024 + (i * 100),
                "created_date": datetime.now(timezone.utc).isoformat(),
                "status": "processed",
                "tags": ["listed", f"doc{i+1}"],
            }
            documents.append(document)
        
        return {
            "documents": documents,
            "total": documents_count,
            "limit": limit,
            "offset": offset,
            **kwargs
        }
    
    @classmethod
    def create_document_analysis_response(
        self,
        document_id: Optional[str] = None,
        chunks_count: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a document analysis response."""
        if document_id is None:
            document_id = f"analyzed_{uuid.uuid4().hex[:12]}"
        
        chunks_preview = []
        for i in range(min(chunks_count, 3)):  # Preview first 3 chunks
            chunk = {
                "chunk_id": f"chunk_{i+1}",
                "text": f"This is chunk {i+1} text content for analysis...",
                "chunk_index": i,
                "start_char": i * 200,
                "end_char": (i + 1) * 200,
            }
            chunks_preview.append(chunk)
        
        return {
            "document_id": document_id,
            "status": "processed",
            "total_chunks": chunks_count,
            "chunks_preview": chunks_preview,
            "processing_stats": {
                "text_extracted": True,
                "embeddings_created": True,
                "metadata_extracted": True,
                "processing_time_ms": 2500,
            },
            "content_stats": {
                "character_count": chunks_count * 200,
                "word_count": chunks_count * 35,
                "language": "en",
            },
            **kwargs
        }
    
    @classmethod
    def create_document_chunks_response(
        self,
        document_id: Optional[str] = None,
        chunks_count: int = 10,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a document chunks response."""
        if document_id is None:
            document_id = f"chunked_{uuid.uuid4().hex[:12]}"
        
        # Calculate actual returned chunks based on pagination
        available_chunks = max(0, chunks_count - offset)
        returned_chunks = min(available_chunks, limit)
        
        chunks = []
        for i in range(returned_chunks):
            chunk_index = offset + i
            chunk = {
                "chunk_id": f"chunk_{chunk_index + 1}",
                "document_id": document_id,
                "text": f"This is chunk {chunk_index + 1} content from the document...",
                "chunk_index": chunk_index,
                "start_char": chunk_index * 200,
                "end_char": (chunk_index + 1) * 200,
                "embedding_preview": [0.1, 0.2, 0.3],  # Short preview
            }
            chunks.append(chunk)
        
        return {
            "document_id": document_id,
            "chunks": chunks,
            "total": chunks_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + returned_chunks) < chunks_count,
            **kwargs
        }
    
    @classmethod
    def create_document_neighbors_response(
        self,
        document_id: Optional[str] = None,
        neighbors_count: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a document neighbors response."""
        if document_id is None:
            document_id = f"neighbor_doc_{uuid.uuid4().hex[:12]}"
        
        neighbors = []
        for i in range(neighbors_count):
            neighbor = {
                "document_id": f"similar_doc_{uuid.uuid4().hex[:8]}",
                "title": f"Similar Document {i+1}",
                "similarity_score": 0.85 - (i * 0.1),
                "snippet": f"This document is similar to the source document...",
                "metadata": {
                    "mime_type": "text/plain",
                    "created_date": datetime.now(timezone.utc).isoformat(),
                },
            }
            neighbors.append(neighbor)
        
        return {
            "document_id": document_id,
            "neighbors": neighbors,
            "query_text": f"Content from document {document_id} used for similarity matching",
            "similarity_threshold": 0.5,
            **kwargs
        }
    
    @classmethod
    def create_vault_info_response(self, **kwargs) -> Dict[str, Any]:
        """Create a vault info response."""
        return {
            "vault_path": "/tmp/test_vault",
            "total_files": 25,
            "total_size_bytes": 1024000,
            "total_size_mb": 1.0,
            "content_files": 20,
            "thumbnail_files": 5,
            "temp_files": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_vault_files_response(
        self,
        files_count: int = 5,
        directory: str = "content",
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a vault files response."""
        files = []
        
        for i in range(files_count):
            file_hash = f"hash{i+1}_{uuid.uuid4().hex[:16]}"
            file_info = {
                "path": f"{directory}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash[4:]}.txt",
                "full_path": f"/tmp/test_vault/{directory}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash[4:]}.txt",
                "hash": file_hash,
                "extension": "txt",
                "size_bytes": 1024 + (i * 100),
                "created_at": datetime.now(timezone.utc).timestamp(),
                "modified_at": datetime.now(timezone.utc).timestamp(),
            }
            files.append(file_info)
        
        return {
            "files": files,
            "total": files_count,
            "directory": directory,
            "limit": limit,
            "offset": offset,
            **kwargs
        }
    
    @classmethod
    def create_progress_response(
        self,
        file_id: Optional[str] = None,
        stage: str = "processing",
        percentage: int = 75,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a progress response."""
        if file_id is None:
            file_id = f"progress_{uuid.uuid4().hex[:12]}"
        
        return {
            "file_id": file_id,
            "stage": stage,
            "percentage": percentage,
            "message": f"File is currently in {stage} stage",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "estimated_completion": None if percentage < 100 else datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_clear_all_response(self, **kwargs) -> Dict[str, Any]:
        """Create a clear all documents response."""
        return {
            "success": True,
            "operation": "comprehensive_clear_all",
            "summary": {
                "total_files_deleted": 15,
                "total_bytes_reclaimed": 1536000,
                "total_mb_reclaimed": 1.5,
            },
            "vault_metrics": {
                "files_deleted": 10,
                "bytes_reclaimed": 1024000,
                "errors": [],
            },
            "llamaindex_metrics": {
                "storage_files_deleted": 5,
                "storage_bytes_reclaimed": 512000,
                "errors": [],
            },
            "progress_metrics": {
                "total_keys_deleted": 8,
                "errors": [],
            },
            "errors": [],
            **kwargs
        }
    
    @classmethod
    def create_tags_response(self, tags_count: int = 5, **kwargs) -> Dict[str, Any]:
        """Create a tags response."""
        tags = [f"tag{i+1}" for i in range(tags_count)]
        
        return {
            "tags": tags,
            "total": tags_count,
            **kwargs
        }
    
    @classmethod
    def create_topics_response(self, topics_count: int = 3, **kwargs) -> Dict[str, Any]:
        """Create a topics response."""
        topics = []
        
        for i in range(topics_count):
            topic = {
                "topic_id": f"topic_{i+1}",
                "name": f"Topic {i+1}",
                "document_count": 10 - (i * 2),
                "keywords": [f"keyword{i+1}a", f"keyword{i+1}b"],
            }
            topics.append(topic)
        
        return {
            "topics": topics,
            "total_topics": topics_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }


# Convenience functions for creating error responses
def create_error_responses() -> Dict[str, Dict[str, Any]]:
    """Create common error responses for testing."""
    return {
        "bad_request": {
            "detail": "Invalid request parameters",
            "status_code": 400,
        },
        "not_found": {
            "detail": "Resource not found",
            "status_code": 404,
        },
        "internal_error": {
            "detail": "Internal server error occurred",
            "status_code": 500,
        },
        "service_unavailable": {
            "detail": "Service temporarily unavailable",
            "status_code": 503,
        },
        "validation_error": {
            "detail": [
                {
                    "loc": ["body", "query"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
            "status_code": 422,
        },
    }


def create_websocket_responses() -> Dict[str, Dict[str, Any]]:
    """Create WebSocket responses for testing."""
    return {
        "tool_result": {
            "type": "tool_result",
            "id": "msg_123",
            "result": {
                "success": True,
                "result": {"file_id": "ws_file_123", "status": "completed"},
            },
        },
        "agent_result": {
            "type": "agent_result", 
            "id": "agent_msg_456",
            "result": {
                "answer": "WebSocket agent response",
                "confidence": 0.9,
                "sources": [],
            },
        },
        "error_result": {
            "type": "error",
            "id": "error_msg_789",
            "error": "Tool execution failed",
        },
    }