"""
Mock service implementations for testing.

This module provides mock implementations of core services that can be used
in tests to isolate units of code and provide predictable behavior.
"""

from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock
from pathlib import Path

from lifearchivist.server.progress_manager import ProgressUpdate, ProcessingStage


class MockVault:
    """Mock implementation of Vault for testing."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self._files: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the mock vault."""
        self._initialized = True
        self.vault_path.mkdir(parents=True, exist_ok=True)
    
    async def store_file(
        self,
        file_path: Path,
        file_hash: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock file storage."""
        assert self._initialized, "Vault not initialized"
        
        # Simulate storage
        size = file_path.stat().st_size if file_path.exists() else 1024
        
        storage_info = {
            "file_hash": file_hash,
            "size": size,
            "stored_at": "2024-01-01T00:00:00Z",
            "storage_path": f"content/{file_hash[:2]}/{file_hash[2:4]}/{file_hash[4:]}.bin",
            "metadata": metadata or {},
        }
        
        self._files[file_hash] = storage_info
        return storage_info
    
    async def get_file_info(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get mock file information."""
        return self._files.get(file_hash)
    
    async def clear_all_files(self, file_hashes: List[str] = None) -> Dict[str, Any]:
        """Mock clearing all files."""
        if file_hashes is None:
            # Clear all files
            files_deleted = len(self._files)
            bytes_reclaimed = sum(f.get("size", 1024) for f in self._files.values())
            self._files.clear()
        else:
            # Clear specific files
            files_deleted = 0
            bytes_reclaimed = 0
            for file_hash in file_hashes:
                if file_hash in self._files:
                    bytes_reclaimed += self._files[file_hash].get("size", 1024)
                    del self._files[file_hash]
                    files_deleted += 1
        
        return {
            "files_deleted": files_deleted,
            "bytes_reclaimed": bytes_reclaimed,
            "errors": [],
        }
    
    async def get_vault_statistics(self) -> Dict[str, Any]:
        """Get mock vault statistics."""
        total_files = len(self._files)
        total_size = sum(f.get("size", 1024) for f in self._files.values())
        
        return {
            "vault_path": str(self.vault_path),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "content_files": total_files,
            "thumbnail_files": 0,
            "temp_files": 0,
            "last_updated": "2024-01-01T00:00:00Z",
        }


class MockLlamaIndexService:
    """Mock implementation of LlamaIndexService for testing."""
    
    def __init__(self, vault: MockVault = None):
        self.vault = vault
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._chunks: Dict[str, List[Dict[str, Any]]] = {}
    
    async def query_documents_by_metadata(
        self,
        filters: Dict[str, Any] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Mock document query."""
        documents = list(self._documents.values())
        
        # Apply simple filtering
        if filters:
            filtered_docs = []
            for doc in documents:
                matches = True
                for key, value in filters.items():
                    if key == "status" and doc.get("status") != value:
                        matches = False
                        break
                    elif key == "mime_type" and doc.get("mime_type") != value:
                        matches = False
                        break
                    elif key == "tags" and value:
                        doc_tags = doc.get("tags", [])
                        if not any(tag in doc_tags for tag in value):
                            matches = False
                            break
                
                if matches:
                    filtered_docs.append(doc)
            
            documents = filtered_docs
        
        # Apply pagination
        return documents[offset:offset + limit]
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        chunks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Mock document addition."""
        document = {
            "document_id": document_id,
            "content": content,
            "status": "processed",
            "created_at": "2024-01-01T00:00:00Z",
            **metadata
        }
        
        self._documents[document_id] = document
        
        if chunks:
            self._chunks[document_id] = chunks
        else:
            # Generate mock chunks
            chunk_size = 200
            mock_chunks = []
            for i in range(0, len(content), chunk_size):
                chunk = {
                    "chunk_id": f"chunk_{i // chunk_size + 1}",
                    "document_id": document_id,
                    "text": content[i:i + chunk_size],
                    "chunk_index": i // chunk_size,
                    "start_char": i,
                    "end_char": min(i + chunk_size, len(content)),
                }
                mock_chunks.append(chunk)
            self._chunks[document_id] = mock_chunks
        
        return {"success": True, "document_id": document_id}
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """Mock clearing all data."""
        files_deleted = len(self._documents)
        self._documents.clear()
        self._chunks.clear()
        
        return {
            "storage_files_deleted": files_deleted,
            "storage_bytes_reclaimed": files_deleted * 1024,
        }
    
    async def get_document_analysis(self, document_id: str) -> Dict[str, Any]:
        """Mock document analysis."""
        if document_id not in self._documents:
            return {"error": f"Document {document_id} not found"}
        
        doc = self._documents[document_id]
        chunks = self._chunks.get(document_id, [])
        
        return {
            "document_id": document_id,
            "status": doc.get("status", "processed"),
            "total_chunks": len(chunks),
            "chunks_preview": chunks[:3],  # First 3 chunks
            "processing_stats": {
                "text_extracted": True,
                "embeddings_created": True,
                "metadata_extracted": True,
                "processing_time_ms": 1500,
            },
            "content_stats": {
                "character_count": len(doc.get("content", "")),
                "word_count": len(doc.get("content", "").split()),
                "language": "en",
            },
        }
    
    async def get_document_chunks(
        self,
        document_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Mock document chunks retrieval."""
        if document_id not in self._documents:
            return {"error": f"Document {document_id} not found"}
        
        chunks = self._chunks.get(document_id, [])
        paginated_chunks = chunks[offset:offset + limit]
        
        return {
            "document_id": document_id,
            "chunks": paginated_chunks,
            "total": len(chunks),
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(paginated_chunks)) < len(chunks),
        }
    
    async def get_document_neighbors(
        self,
        document_id: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Mock document neighbors."""
        if document_id not in self._documents:
            return {"error": f"Document {document_id} not found"}
        
        # Mock similar documents
        neighbors = []
        doc_list = list(self._documents.keys())
        for i, other_id in enumerate(doc_list[:top_k]):
            if other_id != document_id:
                other_doc = self._documents[other_id]
                neighbor = {
                    "document_id": other_id,
                    "title": other_doc.get("title", f"Document {other_id[:8]}"),
                    "similarity_score": 0.9 - (i * 0.1),
                    "snippet": other_doc.get("content", "")[:100],
                    "metadata": {
                        "mime_type": other_doc.get("mime_type", "text/plain"),
                        "created_at": other_doc.get("created_at"),
                    },
                }
                neighbors.append(neighbor)
        
        return {
            "document_id": document_id,
            "neighbors": neighbors,
            "query_text": f"Content from document {document_id}",
            "similarity_threshold": 0.5,
        }
    
    async def retrieve_similar(
        self,
        query: str,
        mode: str = "semantic",
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Mock similarity search."""
        documents = await self.query_documents_by_metadata(filters or {})
        
        # Mock scoring based on simple text matching
        results = []
        for doc in documents[:top_k]:
            score = 0.8 if query.lower() in doc.get("content", "").lower() else 0.3
            result = {
                "document_id": doc["document_id"],
                "score": score,
                "text": doc.get("content", "")[:200],
                "metadata": {k: v for k, v in doc.items() if k not in ["content"]},
            }
            results.append(result)
        
        return results
    
    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize"
    ) -> Dict[str, Any]:
        """Mock Q&A query."""
        # Mock similar documents retrieval
        similar_docs = await self.retrieve_similar(question, top_k=similarity_top_k)
        
        # Mock answer generation
        sources = []
        for doc in similar_docs:
            source = {
                "document_id": doc["document_id"],
                "title": doc["metadata"].get("title", "Unknown Document"),
                "text": doc["text"],
                "score": doc["score"],
            }
            sources.append(source)
        
        return {
            "answer": f"Based on the available documents, here is information related to: {question}",
            "confidence": 0.85,
            "sources": sources,
            "method": "mock_llamaindex",
        }


class MockProgressManager:
    """Mock implementation of ProgressManager for testing."""
    
    def __init__(self, redis_url: str = None, session_manager=None):
        self.redis_url = redis_url
        self.session_manager = session_manager
        self._progress: Dict[str, ProgressUpdate] = {}
    
    async def get_progress(self, file_id: str) -> Optional[ProgressUpdate]:
        """Get mock progress."""
        return self._progress.get(file_id)
    
    async def update_progress(
        self,
        file_id: str,
        stage: ProcessingStage,
        progress: float,
        message: Optional[str] = None
    ) -> None:
        """Set mock progress."""
        import time
        progress_update = ProgressUpdate(
            file_id=file_id,
            stage=stage,
            progress=progress,
            message=message or stage.label,
            timestamp=time.time(),
        )
        self._progress[file_id] = progress_update
    
    async def clear_all_progress(self) -> Dict[str, Any]:
        """Clear all mock progress."""
        keys_deleted = len(self._progress)
        self._progress.clear()
        
        return {
            "total_keys_deleted": keys_deleted,
        }


class MockToolRegistry:
    """Mock implementation of ToolRegistry for testing."""
    
    def __init__(self, vault=None, llamaindex_service=None, progress_manager=None):
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.progress_manager = progress_manager
        self._tools = {}
    
    async def register_all(self):
        """Mock tool registration."""
        # Simulate registering common tools
        self._tools = {
            "file.import": AsyncMock(),
            "extract.text": AsyncMock(),
            "index.search": AsyncMock(),
            "llamaindex.query": AsyncMock(),
            "ollama.generate": AsyncMock(),
        }
    
    def get_tool(self, name: str):
        """Get mock tool."""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict[str, str]]:
        """List mock tools."""
        return {
            name: {
                "description": f"Mock {name} tool",
                "async": "true",
                "idempotent": "true",
            }
            for name in self._tools
        }