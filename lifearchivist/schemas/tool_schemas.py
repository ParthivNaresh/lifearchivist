"""
Tool input/output schemas for MCP tools.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContentDateExtractionInput(BaseModel):
    """Input schema for content date extraction."""

    document_id: str = Field(description="Document ID to extract dates from")
    text_content: str = Field(description="Text content to analyze")


class ContentDateExtractionOutput(BaseModel):
    """Output schema for content date extraction."""

    document_id: str = Field(description="Document ID")
    extracted_date: str = Field(description="Extracted date")
    total_dates_found: int = Field(description="Total number of dates extracted")


# Subtheme Classification Schemas
class SubthemeClassificationRequest(BaseModel):
    """Request model for subtheme classification."""

    text: str = Field(description="Document text to classify")
    primary_theme: str = Field(description="Already identified primary theme")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata (filename, mime_type, etc.)"
    )
    document_id: Optional[str] = Field(
        default=None, description="Optional document ID for tracking"
    )


class SubthemeClassificationResponse(BaseModel):
    """Response model for subtheme classification."""

    success: bool = Field(description="Whether classification was successful")
    primary_theme: str = Field(description="Primary theme of the document")
    subthemes: List[str] = Field(
        default_factory=list, description="List of applicable subthemes"
    )
    primary_subtheme: Optional[str] = Field(
        default=None, description="Most likely subtheme"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict, description="Confidence score for each subtheme"
    )
    classification_method: str = Field(
        default="rules", description="Method used for classification"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional classification metadata"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if classification failed"
    )
