"""
Miscellaneous models for document endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ClearAllSummary(BaseModel):
    """Summary of clear all operation."""

    total_files_deleted: int = Field(..., description="Total files deleted")
    total_bytes_reclaimed: int = Field(..., description="Total bytes reclaimed")
    total_mb_reclaimed: float = Field(..., description="Total MB reclaimed")


class ThemeClassification(BaseModel):
    """Theme classification metadata."""

    theme: Optional[str] = Field(None, description="Primary theme")
    confidence: Optional[float] = Field(None, description="Classification confidence")
    confidence_level: Optional[str] = Field(None, description="Confidence level label")
    match_tier: Optional[str] = Field(None, description="Match tier classification")
    match_pattern: Optional[str] = Field(None, description="Pattern or phrase matched")
    subthemes: List[str] = Field(default_factory=list, description="Subthemes")
    primary_subtheme: Optional[str] = Field(None, description="Primary subtheme")
    subclassifications: List[str] = Field(
        default_factory=list, description="Subclassifications"
    )
    primary_subclassification: Optional[str] = Field(
        None, description="Primary subclassification"
    )
    subclassification_confidence: Optional[float] = Field(
        None, description="Subclassification confidence"
    )
    category_mapping: Dict[str, Any] = Field(
        default_factory=dict, description="Category mapping"
    )


class Document(BaseModel):
    """Document model with flattened metadata."""

    id: str = Field(..., description="Document identifier")
    file_hash: str = Field(..., description="File content hash")
    original_path: str = Field(..., description="Original file path")
    mime_type: Optional[str] = Field(None, description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    created_at: str = Field(..., description="Creation timestamp")
    modified_at: Optional[str] = Field(None, description="Modification timestamp")
    ingested_at: str = Field(..., description="Ingestion timestamp")
    status: str = Field(..., description="Processing status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    word_count: Optional[int] = Field(None, description="Word count")
    language: Optional[str] = Field(None, description="Detected language")
    extraction_method: Optional[str] = Field(None, description="Extraction method used")
    text_preview: str = Field(default="", description="Text preview")
    has_content: bool = Field(..., description="Whether document has content")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    tag_count: int = Field(..., description="Number of tags")
    theme: Optional[str] = Field(None, description="Primary theme")
    theme_confidence: Optional[float] = Field(None, description="Theme confidence")
    confidence_level: Optional[str] = Field(None, description="Confidence level")
    classification: Optional[str] = Field(None, description="Classification tier")
    pattern_or_phrase: Optional[str] = Field(None, description="Matched pattern")
    subthemes: List[str] = Field(default_factory=list, description="Subthemes")
    primary_subtheme: Optional[str] = Field(None, description="Primary subtheme")
    subclassifications: List[str] = Field(
        default_factory=list, description="Subclassifications"
    )
    primary_subclassification: Optional[str] = Field(
        None, description="Primary subclassification"
    )
    subclassification_confidence: Optional[float] = Field(
        None, description="Subclassification confidence"
    )
    category_mapping: Dict[str, Any] = Field(
        default_factory=dict, description="Category mapping"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_123",
                "file_hash": "abc123def456",
                "original_path": "/path/to/document.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 1024000,
                "created_at": "2025-01-08T14:30:00Z",
                "modified_at": "2025-01-08T14:30:00Z",
                "ingested_at": "2025-01-08T14:30:00Z",
                "status": "completed",
                "error_message": None,
                "word_count": 5000,
                "language": "en",
                "extraction_method": "pypdf",
                "text_preview": "This is a preview...",
                "has_content": True,
                "tags": ["work", "important"],
                "tag_count": 2,
                "theme": "Technology",
                "theme_confidence": 0.95,
                "confidence_level": "high",
                "classification": "tier_1",
                "pattern_or_phrase": "software development",
                "subthemes": ["AI", "Machine Learning"],
                "primary_subtheme": "AI",
                "subclassifications": [],
                "primary_subclassification": None,
                "subclassification_confidence": None,
                "category_mapping": {},
            }
        }


class DocumentChunk(BaseModel):
    """Document chunk model."""

    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    score: Optional[float] = Field(None, description="Relevance score if from search")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "chunk_1",
                "text": "This is the first chunk of the document...",
                "metadata": {"page": 1, "section": "Introduction"},
                "score": 0.85,
            }
        }


class DocumentNeighbor(BaseModel):
    """Similar document model."""

    document_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_456",
                "title": "Similar Document.pdf",
                "similarity_score": 0.85,
                "metadata": {"theme": "Technology", "tags": ["AI"]},
            }
        }
