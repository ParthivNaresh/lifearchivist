"""
Response models for timeline endpoints.
"""

from typing import Dict

from pydantic import BaseModel, Field

from .misc_models import DataQuality, DateRange, YearData


class TimelineDataResponse(BaseModel):
    """Response from timeline data endpoint."""

    total_documents: int = Field(..., description="Total documents in timeline")
    date_range: DateRange = Field(..., description="Date range of documents")
    by_year: Dict[str, YearData] = Field(
        ..., description="Documents grouped by year (YYYY)"
    )
    documents_without_dates: int = Field(
        ..., description="Number of documents without dates"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "date_range": {
                    "earliest": "2023-01-01",
                    "latest": "2024-12-31",
                },
                "by_year": {
                    "2024": {
                        "count": 45,
                        "months": {
                            "01": {
                                "count": 5,
                                "documents": [],
                            }
                        },
                    }
                },
                "documents_without_dates": 5,
            }
        }


class TimelineSummaryResponse(BaseModel):
    """Response from timeline summary endpoint."""

    total_documents: int = Field(..., description="Total documents")
    date_range: DateRange = Field(..., description="Date range of documents")
    by_year: Dict[str, int] = Field(..., description="Document count by year (YYYY)")
    data_quality: DataQuality = Field(..., description="Data quality metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 150,
                "date_range": {
                    "earliest": "2023-01-01",
                    "latest": "2024-12-31",
                },
                "by_year": {
                    "2023": 105,
                    "2024": 45,
                },
                "data_quality": {
                    "with_document_created_at": 120,
                    "with_platform_dates": 0,
                    "fallback_to_disk": 25,
                    "no_dates": 5,
                },
            }
        }
