"""
Type definitions for RAG (Retrieval-Augmented Generation) system.

Provides structured types for configuration, streaming events, and citations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class StreamEventType(Enum):
    """Types of events emitted during RAG processing."""

    USER_MESSAGE = "user_message"
    CONTEXT = "context"
    TOKEN = "token"
    METADATA = "metadata"
    ERROR = "error"
    DONE = "done"
    INTENT = "intent"
    SOURCES = "sources"


@dataclass(frozen=True)
class ContextConfig:
    """
    Configuration for RAG context retrieval and processing.

    Attributes:
        enable_rag: Whether to enable RAG for this query
        similarity_top_k: Number of similar chunks to retrieve
        similarity_threshold: Minimum similarity score for retrieval
        max_context_tokens: Maximum tokens to include in context
        include_metadata: Whether to include document metadata
        filters: Metadata filters for document retrieval
        rerank: Whether to rerank retrieved documents
        include_conversation_history: Include recent messages for continuity
        conversation_history_limit: Number of previous messages to include
    """

    enable_rag: bool = True
    similarity_top_k: int = 5
    similarity_threshold: float = 0.45
    max_context_tokens: int = 4000
    include_metadata: bool = True
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = False
    include_conversation_history: bool = True
    conversation_history_limit: int = 10

    def __post_init__(self):
        if self.similarity_top_k < 1:
            raise ValueError("similarity_top_k must be at least 1")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if self.max_context_tokens < 100:
            raise ValueError("max_context_tokens must be at least 100")
        if self.conversation_history_limit < 0:
            raise ValueError("conversation_history_limit cannot be negative")


@dataclass
class Citation:
    """
    Reference to a source document chunk used in response generation.

    Attributes:
        document_id: Unique identifier of the source document
        chunk_id: Identifier of the specific chunk within the document
        relevance_score: Similarity/relevance score (0-1)
        text_snippet: Preview of the chunk content
        metadata: Document metadata (title, date, theme, etc.)
        start_char: Starting character position in original document
        end_char: Ending character position in original document
        confidence: Confidence that this citation supports the response
    """

    document_id: str
    chunk_id: str
    relevance_score: float
    text_snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    confidence: float = 0.0

    def __post_init__(self):
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError("relevance_score must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if len(self.text_snippet) > 500:
            self.text_snippet = self.text_snippet[:497] + "..."

    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "relevance_score": self.relevance_score,
            "text_snippet": self.text_snippet,
            "metadata": self.metadata,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
        }

    @classmethod
    def from_chunk(cls, chunk: Dict[str, Any]) -> "Citation":
        """
        Create citation from a document chunk.

        Args:
            chunk: Chunk dictionary from retrieval system

        Returns:
            Citation instance
        """
        return cls(
            document_id=chunk.get("document_id", "unknown"),
            chunk_id=chunk.get("node_id", chunk.get("chunk_id", "")),
            relevance_score=float(chunk.get("score", 0.0)),
            text_snippet=chunk.get("text", "")[:500],
            metadata=chunk.get("metadata", {}),
            start_char=chunk.get("start_char"),
            end_char=chunk.get("end_char"),
            confidence=float(chunk.get("score", 0.0)),
        )


@dataclass
class ContextData:
    """Data payload for context events."""

    citations: List[Citation]
    total_chunks: int
    context_length: int
    avg_relevance_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "citations": [c.to_dict() for c in self.citations],
            "total_chunks": self.total_chunks,
            "context_length": self.context_length,
            "avg_relevance_score": self.avg_relevance_score,
        }


@dataclass
class MetadataInfo:
    """Metadata about the RAG processing."""

    model: str
    provider_id: str
    confidence_score: float
    response_mode: str
    num_sources: int
    context_length: int
    answer_length: int
    unique_documents: int
    processing_time_ms: int
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model": self.model,
            "provider_id": self.provider_id,
            "confidence_score": self.confidence_score,
            "response_mode": self.response_mode,
            "num_sources": self.num_sources,
            "context_length": self.context_length,
            "answer_length": self.answer_length,
            "unique_documents": self.unique_documents,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }


@dataclass
class ErrorInfo:
    """Error information for error events."""

    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }


@dataclass
class IntentData:
    """Intent classification data."""

    is_document_query: bool
    requires_context: bool
    query_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_document_query": self.is_document_query,
            "requires_context": self.requires_context,
            "query_type": self.query_type,
        }


@dataclass
class StreamEvent:
    """
    Event emitted during RAG streaming processing.

    Attributes:
        type: Type of event
        data: Event payload (varies by type)
        timestamp: When the event occurred
        sequence_number: Order of event in stream
    """

    type: StreamEventType
    data: Union[ContextData, str, MetadataInfo, ErrorInfo, IntentData, List[Citation]]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data_dict: Any
        if isinstance(self.data, str):
            data_dict = self.data
        elif isinstance(self.data, list):
            data_dict = [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.data
            ]
        elif hasattr(self.data, "to_dict"):
            data_dict = self.data.to_dict()
        else:
            data_dict = self.data

        return {
            "type": self.type.value,
            "data": data_dict,
            "timestamp": self.timestamp.isoformat() + "Z",
            "sequence_number": self.sequence_number,
        }

    @classmethod
    def context(
        cls, citations: List[Citation], context_length: int, sequence: int = 0
    ) -> "StreamEvent":
        """Create a context event."""
        avg_score = (
            sum(c.relevance_score for c in citations) / len(citations)
            if citations
            else 0.0
        )
        return cls(
            type=StreamEventType.CONTEXT,
            data=ContextData(
                citations=citations,
                total_chunks=len(citations),
                context_length=context_length,
                avg_relevance_score=avg_score,
            ),
            sequence_number=sequence,
        )

    @classmethod
    def token(cls, content: str, sequence: int = 0) -> "StreamEvent":
        """Create a token event."""
        return cls(
            type=StreamEventType.TOKEN,
            data=content,
            sequence_number=sequence,
        )

    @classmethod
    def metadata(cls, info: MetadataInfo, sequence: int = 0) -> "StreamEvent":
        """Create a metadata event."""
        return cls(
            type=StreamEventType.METADATA,
            data=info,
            sequence_number=sequence,
        )

    @classmethod
    def error(
        cls,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        sequence: int = 0,
    ) -> "StreamEvent":
        """Create an error event."""
        return cls(
            type=StreamEventType.ERROR,
            data=ErrorInfo(
                error_type=error_type,
                message=message,
                details=details,
            ),
            sequence_number=sequence,
        )

    @classmethod
    def done(cls, sequence: int = 0) -> "StreamEvent":
        """Create a completion event."""
        return cls(
            type=StreamEventType.DONE,
            data="",
            sequence_number=sequence,
        )

    @classmethod
    def intent(
        cls, is_document_query: bool, requires_context: bool, sequence: int = 0
    ) -> "StreamEvent":
        """Create an intent classification event."""
        return cls(
            type=StreamEventType.INTENT,
            data=IntentData(
                is_document_query=is_document_query,
                requires_context=requires_context,
            ),
            sequence_number=sequence,
        )

    @classmethod
    def sources(cls, citations: List[Citation], sequence: int = 0) -> "StreamEvent":
        """Create a sources event."""
        return cls(
            type=StreamEventType.SOURCES,
            data=citations,
            sequence_number=sequence,
        )
