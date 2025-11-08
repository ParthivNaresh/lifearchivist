from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation information."""

    doc_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    snippet: str = Field(..., description="Text snippet")
    score: float = Field(..., description="Relevance score")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "doc_123",
                "title": "AI Overview.pdf",
                "snippet": "Artificial intelligence is...",
                "score": 0.92,
            }
        }


class SearchResult(BaseModel):
    """Search result model."""

    document_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    score: float = Field(..., description="Relevance score")
    snippet: Optional[str] = Field(None, description="Text snippet")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "title": "AI Overview.pdf",
                "score": 0.92,
                "snippet": "Artificial intelligence is...",
                "metadata": {
                    "mime_type": "application/pdf",
                    "status": "completed",
                    "tags": ["AI", "technology"],
                },
            }
        }
