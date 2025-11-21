from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ExtractionFilters(BaseModel):
    # Extend as needed (mime types, date ranges, tags, etc.)
    mime_types: Optional[List[str]] = None
    date_from: Optional[str] = None  # ISO8601
    date_to: Optional[str] = None  # ISO8601
    sources: Optional[List[str]] = None


class StructuredExtractionParams(BaseModel):
    """
    Parameters controlling structured extraction from one or more documents.
    """

    document_ids: List[str] = Field(..., min_length=1, description="Target documents")

    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema defining the expected output structure. Takes precedence over fields.",
    )

    instructions: Optional[str] = Field(
        default=None,
        description="Natural language instructions for what to extract and how.",
    )

    fields: Optional[List[str]] = Field(
        default=None,
        description="Simple field list (legacy). Converted to output_schema if provided.",
        min_length=1,
    )
    queries: Optional[List[str]] = Field(
        default=None,
        description="Free-form information needs (legacy). Merged into instructions if provided.",
        min_length=1,
    )
    filters: Optional[ExtractionFilters] = None

    # Retrieval knobs
    top_k_chunks_per_doc: int = Field(20, ge=1, le=200)
    max_total_chunks: int = Field(200, ge=1, le=2000)
    max_concurrency: int = Field(16, ge=1, le=64, description="Parallel chunk fetches")

    # Budgeting knobs
    max_input_chars: int = Field(250_000, ge=10_000, le=2_000_000)
    require_provenance: bool = Field(True)

    # LLM steering knobs (hints; orchestrator may override)
    model: Optional[str] = Field(default=None, description="Model hint/override")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(800, ge=64, le=8192)

    max_chunks_per_doc: int = Field(
        100,
        ge=1,
        le=2000,
        description="Hard cap for chunks fetched per document.",
    )
    max_chars_per_chunk: int = Field(
        4000,
        ge=256,
        le=16000,
        description="Trim each chunk to this maximum length (characters).",
    )
    max_total_chars: int = Field(
        200_000,
        ge=1024,
        le=2_000_000,
        description="Aggregate character budget across all chunks (after per-chunk trimming).",
    )
    fetch_concurrency: int = Field(
        8,
        ge=1,
        le=64,
        description="Max concurrent chunk fetches from the document service.",
    )

    @model_validator(mode="after")
    def _at_least_one_guidance(self) -> "StructuredExtractionParams":
        if not (self.output_schema or self.fields or self.queries):
            raise ValueError(
                "Must provide at least one of: output_schema, fields, or queries"
            )
        return self


class ProvenanceItem(BaseModel):
    document_id: str
    chunk_id: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    score: Optional[float] = None
    page: Optional[int] = None


class StructuredExtractionOutput(BaseModel):
    """
    Strict JSON schema expected from the LLM.
    """

    extracted: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of field/query -> extracted value(s)",
    )
    provenance: List[ProvenanceItem] = Field(
        default_factory=list,
        description="Per-field citations to source chunks",
    )
    partial: bool = Field(
        False, description="True if any retrieval failed or truncated"
    )
    diagnostics: Dict[str, Any] = Field(
        default_factory=dict, description="Latency, counts, model, budgeting info"
    )


@dataclass(slots=True)
class ExtractionMetrics:
    documents_seen: int = 0
    chunks_used: int = 0
    chars_used: int = 0
