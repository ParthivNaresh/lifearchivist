"""
Tool input/output schemas for MCP tools.
"""

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
