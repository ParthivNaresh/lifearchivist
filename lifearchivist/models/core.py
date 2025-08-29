"""
Core data models for Life Archivist.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    NATIVE = "native"
    OCR = "ocr"
    TRANSCRIPTION = "transcription"


class EntityType(str, Enum):
    PERSON = "person"
    ORG = "org"
    PLACE = "place"
    DATE = "date"
    CUSTOM = "custom"


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"


class Document(BaseModel):
    """Core document model."""

    id: str = Field(description="Unique document ID (UUID)")
    file_hash: str = Field(description="SHA256 hash of file content")
    original_path: Optional[str] = Field(description="Original file path")
    mime_type: str = Field(description="MIME type of document")
    size_bytes: int = Field(description="File size in bytes")
    created_at: datetime = Field(description="File creation timestamp")
    modified_at: Optional[datetime] = Field(description="File modification timestamp")
    ingested_at: datetime = Field(description="Ingestion timestamp")
    status: DocumentStatus = Field(description="Processing status")
    error_message: Optional[str] = Field(description="Error message if failed")

    # Content fields
    text_content: Optional[str] = Field(description="Extracted text content")
    summary: Optional[str] = Field(description="Generated summary")
    key_points: Optional[List[str]] = Field(description="Key points from document")
    word_count: Optional[int] = Field(description="Word count")
    language: Optional[str] = Field(description="Detected language")
    extraction_method: Optional[ExtractionMethod] = Field(
        description="How text was extracted"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Document tags")
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(description="Search query")
    mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Search filters"
    )
    limit: int = Field(default=20, description="Maximum results")
    offset: int = Field(default=0, description="Result offset")
    include_content: bool = Field(default=False, description="Include full content")


class SearchResult(BaseModel):
    """Search result model."""

    document_id: str = Field(description="Document ID")
    score: float = Field(description="Relevance score 0-1")
    title: str = Field(description="Document title or filename")
    snippet: str = Field(description="Highlighted snippet")
    created_at: datetime = Field(description="Document creation time")
    tags: List[str] = Field(description="Document tags")
    match_type: str = Field(description="Type of match (semantic/keyword/both)")
    document: Optional[Document] = Field(
        default=None, description="Full document if requested"
    )


class IngestRequest(BaseModel):
    """Document ingestion request."""

    path: str = Field(description="File path to ingest")
    mime_hint: Optional[str] = Field(default=None, description="MIME type hint")
    tags: Optional[List[str]] = Field(default=None, description="Initial tags")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom metadata"
    )
    session_id: Optional[str] = Field(
        default=None, description="WebSocket session ID for progress tracking"
    )


class JobStatus(BaseModel):
    """Background job status."""

    job_id: str = Field(description="Job ID")
    status: str = Field(description="Job status")
    progress: float = Field(description="Progress 0-1")
    stage: str = Field(description="Current processing stage")
    estimated_time: Optional[int] = Field(
        description="Estimated completion time in seconds"
    )
    result: Optional[Dict[str, Any]] = Field(description="Job result when complete")
