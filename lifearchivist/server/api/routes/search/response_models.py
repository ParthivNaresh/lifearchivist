from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .misc_models import Citation, SearchResult


class AskQuestionResponse(BaseModel):
    """Response from asking a question."""

    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., description="Confidence score")
    citations: List[Citation] = Field(..., description="Source citations")
    method: str = Field(..., description="Method used for generation")
    context_length: int = Field(..., description="Number of context documents used")
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Query statistics"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Based on the documents, AI is...",
                "confidence": 0.85,
                "citations": [
                    {
                        "doc_id": "doc_123",
                        "title": "AI Overview",
                        "snippet": "AI is artificial intelligence...",
                        "score": 0.92,
                    }
                ],
                "method": "llamaindex_rag",
                "context_length": 3,
                "statistics": {"tokens_used": 150},
            }
        }


class SearchDocumentsResponse(BaseModel):
    """Response from searching documents."""

    results: List[SearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")
    mode: str = Field(..., description="Search mode used")
    query: str = Field(..., description="Search query")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "document_id": "doc_123",
                        "title": "Example Document.pdf",
                        "score": 0.85,
                        "snippet": "This document discusses...",
                        "metadata": {
                            "mime_type": "application/pdf",
                            "status": "completed",
                        },
                    }
                ],
                "count": 1,
                "mode": "semantic",
                "query": "artificial intelligence",
            }
        }
