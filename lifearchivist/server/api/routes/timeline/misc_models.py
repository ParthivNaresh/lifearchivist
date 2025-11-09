"""
Miscellaneous models for timeline endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    """Document summary for timeline."""

    id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    date: str = Field(..., description="ISO date string")
    mime_type: Optional[str] = Field(None, description="MIME type")
    theme: Optional[str] = Field(None, description="Document theme")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_123",
                "title": "Meeting Notes.pdf",
                "date": "2024-01-15T10:30:00Z",
                "mime_type": "application/pdf",
                "theme": "Work",
            }
        }


class MonthData(BaseModel):
    """Month data in timeline."""

    count: int = Field(..., description="Number of documents in this month")
    documents: List[DocumentSummary] = Field(
        ..., description="List of documents in this month"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "count": 5,
                "documents": [
                    {
                        "id": "doc_123",
                        "title": "Meeting Notes.pdf",
                        "date": "2024-01-15T10:30:00Z",
                        "mime_type": "application/pdf",
                        "theme": "Work",
                    }
                ],
            }
        }


class YearData(BaseModel):
    """Year data in timeline."""

    count: int = Field(..., description="Number of documents in this year")
    months: Dict[str, MonthData] = Field(
        ..., description="Documents grouped by month (MM)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "count": 45,
                "months": {
                    "01": {
                        "count": 5,
                        "documents": [],
                    },
                    "02": {
                        "count": 8,
                        "documents": [],
                    },
                },
            }
        }


class DateRange(BaseModel):
    """Date range model."""

    earliest: Optional[str] = Field(None, description="Earliest date (ISO)")
    latest: Optional[str] = Field(None, description="Latest date (ISO)")

    class Config:
        json_schema_extra = {
            "example": {
                "earliest": "2023-01-01",
                "latest": "2024-12-31",
            }
        }


class DataQuality(BaseModel):
    """Data quality metrics."""

    with_document_created_at: int = Field(
        ..., description="Documents with document_created_at"
    )
    with_platform_dates: int = Field(
        default=0, description="Documents with platform dates"
    )
    fallback_to_disk: int = Field(
        ..., description="Documents using file_modified_at_disk"
    )
    no_dates: int = Field(..., description="Documents without any dates")

    class Config:
        json_schema_extra = {
            "example": {
                "with_document_created_at": 120,
                "with_platform_dates": 0,
                "fallback_to_disk": 25,
                "no_dates": 5,
            }
        }
