from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SummaryStyle(str, Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    NARRATIVE = "narrative"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"


class SummaryFocus(str, Enum):
    OVERVIEW = "overview"
    KEY_POINTS = "key_points"
    INSIGHTS = "insights"
    RECOMMENDATIONS = "recommendations"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"


class TextExtractionParams(BaseModel):
    """
    Parameters controlling free-form text extraction and summarization from documents.
    Unlike structured_extraction, this produces prose/narrative output rather than JSON.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Target documents to extract and summarize",
    )

    instructions: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language instructions for what to extract, summarize, or analyze",
    )

    style: SummaryStyle = Field(
        SummaryStyle.DETAILED,
        description="Output style: concise, detailed, bullet_points, narrative, technical, or executive",
    )

    focus: Optional[SummaryFocus] = Field(
        None,
        description="What to focus on: overview, key_points, insights, recommendations, analysis, or comparison",
    )

    max_output_length: int = Field(
        1000,
        ge=100,
        le=10000,
        description="Target maximum length for the output text (in words)",
    )

    include_citations: bool = Field(
        True,
        description="Whether to include document references/citations in the output",
    )

    max_chunks_per_doc: int = Field(
        100,
        ge=1,
        le=2000,
        description="Maximum chunks to fetch per document",
    )

    max_chars_per_chunk: int = Field(
        4000,
        ge=256,
        le=16000,
        description="Maximum characters per chunk",
    )

    max_total_chars: int = Field(
        200_000,
        ge=1024,
        le=2_000_000,
        description="Total character budget across all chunks",
    )

    fetch_concurrency: int = Field(
        8,
        ge=1,
        le=64,
        description="Maximum concurrent chunk fetches",
    )

    model: Optional[str] = Field(
        None,
        description="LLM model hint/override",
    )

    temperature: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature for generation (0=deterministic, 1=creative)",
    )

    max_tokens: int = Field(
        2000,
        ge=100,
        le=16000,
        description="Maximum tokens for LLM response",
    )

    @model_validator(mode="after")
    def _validate_params(self) -> "TextExtractionParams":
        if self.max_output_length < 100:
            raise ValueError("max_output_length must be at least 100 words")
        return self


@dataclass(slots=True)
class TextExtractionMetrics:
    documents_seen: int = 0
    chunks_used: int = 0
    chars_used: int = 0
    output_length_words: int = 0
    output_length_chars: int = 0
