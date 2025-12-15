from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SearchMethod(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    METADATA = "metadata"


class DateFilter(BaseModel):
    after: Optional[str] = Field(None, description="ISO8601 date string (YYYY-MM-DD)")
    before: Optional[str] = Field(None, description="ISO8601 date string (YYYY-MM-DD)")


class DocumentSearchParams(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language search query or keywords",
    )

    search_method: SearchMethod = Field(
        SearchMethod.HYBRID,
        description="Search method: semantic (vector), keyword (BM25), hybrid (both), or metadata (filters only)",
    )

    top_k: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of documents to return",
    )

    instructions: Optional[str] = None

    @classmethod
    def get_priority_params(cls) -> List[str]:
        return ["query", "search_method", "top_k", "instructions"]

    similarity_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic/hybrid search (0-1)",
    )

    semantic_weight: float = Field(
        0.6,
        ge=0.0,
        le=1.0,
        description="Weight for semantic search in hybrid mode (0-1, higher = more semantic)",
    )

    mime_types: Optional[List[str]] = Field(
        None,
        description="Filter by document types (e.g., ['application/pdf', 'text/plain'])",
    )

    themes: Optional[List[str]] = Field(
        None,
        description="Filter by document themes/categories",
    )

    date_filter: Optional[DateFilter] = Field(
        None,
        description="Filter by upload date range",
    )

    status: Optional[str] = Field(
        None,
        description="Filter by document status (e.g., 'indexed', 'processing')",
    )

    include_metadata: bool = Field(
        True,
        description="Include full document metadata in results",
    )

    include_text_preview: bool = Field(
        True,
        description="Include text preview/snippet in results",
    )

    allow_query_expansion: bool = True
    allow_filter_synthesis: bool = True
    allow_rerank: bool = True
    rerank_top_k: int = 50
    model: Optional[str] = None

    @model_validator(mode="after")
    def _validate_search_params(self) -> "DocumentSearchParams":
        if self.search_method == SearchMethod.METADATA and not any(
            [
                self.mime_types,
                self.themes,
                self.date_filter,
                self.status,
            ]
        ):
            raise ValueError(
                "Metadata search requires at least one filter (mime_types, themes, date_filter, or status)"
            )
        return self


@dataclass(slots=True)
class SearchMetrics:
    documents_found: int = 0
    search_method_used: str = ""
    avg_score: float = 0.0
    filters_applied: int = 0
