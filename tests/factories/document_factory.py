"""
Factory for creating document-related test objects.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class DocumentFactory:
    """Factory for creating document objects and metadata for testing."""
    
    @classmethod
    def create_document_metadata(
        self,
        document_id: Optional[str] = None,
        title: Optional[str] = None,
        content_preview: Optional[str] = None,
        mime_type: str = "text/plain",
        file_size: int = 1024,
        tags: Optional[List[str]] = None,
        created_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create document metadata for testing."""
        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        if title is None:
            title = f"Test Document {document_id[-6:]}"
        
        if content_preview is None:
            content_preview = "This is a sample document content preview for testing..."
        
        if created_date is None:
            created_date = datetime.now(timezone.utc).isoformat()
        
        return {
            "document_id": document_id,
            "title": title,
            "content_preview": content_preview,
            "mime_type": mime_type,
            "file_size": file_size,
            "tags": tags or [],
            "created_date": created_date,
            "status": "processed",
            "hash": f"hash_{document_id}",
            **kwargs
        }
    
    @classmethod
    def create_search_result_document(
        self,
        document_id: Optional[str] = None,
        title: Optional[str] = None,
        snippet: Optional[str] = None,
        score: float = 0.85,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a search result document."""
        if document_id is None:
            document_id = f"search_doc_{uuid.uuid4().hex[:8]}"
        
        if title is None:
            title = f"Search Result {document_id[-4:]}"
        
        if snippet is None:
            snippet = "This is a snippet from the search results showing relevant content..."
        
        base_doc = self.create_document_metadata(
            document_id=document_id,
            title=title,
            content_preview=snippet,
            **kwargs
        )
        
        return {
            **base_doc,
            "snippet": snippet,
            "score": score,
            "relevance": "high" if score > 0.8 else "medium" if score > 0.5 else "low",
        }
    
    @classmethod
    def create_document_chunk(
        self,
        chunk_id: Optional[str] = None,
        document_id: Optional[str] = None,
        text: Optional[str] = None,
        chunk_index: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a document chunk for testing."""
        if chunk_id is None:
            chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
        
        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        if text is None:
            text = f"This is chunk {chunk_index} of the document content. It contains relevant information for testing purposes."
        
        return {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "text": text,
            "chunk_index": chunk_index,
            "start_char": chunk_index * 200,
            "end_char": (chunk_index + 1) * 200,
            "embedding": [0.1 + (i * 0.01) for i in range(384)],  # Mock embedding
            **kwargs
        }
    
    @classmethod
    def create_multiple_documents(
        self,
        count: int = 3,
        base_title: str = "Test Document",
        **common_kwargs
    ) -> List[Dict[str, Any]]:
        """Create multiple documents for testing."""
        documents = []
        for i in range(count):
            doc = self.create_document_metadata(
                title=f"{base_title} {i+1}",
                **common_kwargs
            )
            documents.append(doc)
        return documents
    
    @classmethod
    def create_document_analysis(
        self,
        document_id: Optional[str] = None,
        status: str = "processed",
        chunk_count: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a document analysis response for testing."""
        if document_id is None:
            document_id = f"analyzed_doc_{uuid.uuid4().hex[:8]}"
        
        chunks_preview = []
        for i in range(min(chunk_count, 3)):  # Preview first 3 chunks
            chunks_preview.append(self.create_document_chunk(
                document_id=document_id,
                chunk_index=i,
            ))
        
        return {
            "document_id": document_id,
            "status": status,
            "total_chunks": chunk_count,
            "chunks_preview": chunks_preview,
            "processing_stats": {
                "text_extracted": True,
                "embeddings_created": True,
                "metadata_extracted": True,
                "processing_time_ms": 1500,
            },
            "content_stats": {
                "character_count": chunk_count * 200,
                "word_count": chunk_count * 35,
                "language": "en",
            },
            **kwargs
        }
    
    @classmethod
    def create_document_neighbors(
        self,
        document_id: Optional[str] = None,
        neighbor_count: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """Create document neighbors response for testing."""
        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        neighbors = []
        for i in range(neighbor_count):
            neighbor = self.create_search_result_document(
                title=f"Similar Document {i+1}",
                score=0.9 - (i * 0.1),  # Decreasing similarity scores
            )
            neighbors.append(neighbor)
        
        return {
            "document_id": document_id,
            "neighbors": neighbors,
            "query_text": f"Content from document {document_id} used for similarity search",
            "similarity_threshold": 0.5,
            **kwargs
        }


# Convenience functions for common scenarios
def create_medical_documents() -> List[Dict[str, Any]]:
    """Create medical-themed documents for domain-specific testing."""
    return [
        DocumentFactory.create_document_metadata(
            title="Patient Care Guidelines",
            content_preview="Comprehensive guidelines for patient care and treatment protocols...",
            tags=["medical", "patient-care", "guidelines"],
            mime_type="application/pdf",
            category="medical"
        ),
        DocumentFactory.create_document_metadata(
            title="Blood Pressure Monitoring Report",
            content_preview="Blood pressure readings show improvement after medication adjustment...",
            tags=["medical", "blood-pressure", "report"],
            mime_type="text/plain",
            category="medical"
        ),
        DocumentFactory.create_document_metadata(
            title="Lab Results Analysis",
            content_preview="Laboratory test results and analysis for patient diagnosis...",
            tags=["medical", "lab-results", "analysis"],
            mime_type="application/pdf",
            category="medical"
        ),
    ]


def create_financial_documents() -> List[Dict[str, Any]]:
    """Create financial-themed documents for domain-specific testing."""
    return [
        DocumentFactory.create_document_metadata(
            title="Bank of America Quarterly Report", 
            content_preview="Quarterly earnings report shows strong performance in lending sector...",
            tags=["financial", "earnings", "bank"],
            mime_type="application/pdf",
            category="financial"
        ),
        DocumentFactory.create_document_metadata(
            title="Mortgage Rate Information",
            content_preview="Current mortgage rates and home loan information for borrowers...",
            tags=["financial", "mortgage", "rates"],
            mime_type="text/plain", 
            category="financial"
        ),
    ]


def create_mixed_document_set() -> List[Dict[str, Any]]:
    """Create a mixed set of documents for comprehensive testing."""
    documents = []
    documents.extend(create_medical_documents()[:2])  # 2 medical docs
    documents.extend(create_financial_documents())    # 2 financial docs
    
    # Add a general document
    documents.append(
        DocumentFactory.create_document_metadata(
            title="General Information Document",
            content_preview="This document contains general information for testing purposes...",
            tags=["general", "testing"],
            category="general"
        )
    )
    
    return documents