"""
Response models for tags endpoints.
"""

from typing import List

from pydantic import BaseModel, Field

from .misc_models import Tag, Topic


class TagsListResponse(BaseModel):
    """Response from listing tags."""

    tags: List[Tag] = Field(..., description="List of tags with counts")
    total: int = Field(..., description="Total number of tags")
    min_count: int = Field(..., description="Minimum count filter applied")
    limit: int = Field(..., description="Limit applied")
    note: str = Field(
        default="", description="Implementation note (temporary for placeholders)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tags": [
                    {"name": "AI", "count": 42, "metadata": {}},
                    {"name": "technology", "count": 38, "metadata": {}},
                ],
                "total": 2,
                "min_count": 1,
                "limit": 100,
                "note": "",
            }
        }


class TopicLandscapeResponse(BaseModel):
    """Response from topic landscape endpoint."""

    topics: List[Topic] = Field(..., description="List of topics")
    total_topics: int = Field(..., description="Total number of topics")
    total_documents: int = Field(..., description="Total documents across all topics")
    generated_at: str = Field(..., description="ISO timestamp when data was generated")
    min_documents: int = Field(..., description="Minimum documents filter applied")
    max_topics: int = Field(..., description="Maximum topics limit applied")
    note: str = Field(
        default="", description="Implementation note (temporary for placeholders)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topics": [
                    {
                        "id": "topic_ai",
                        "name": "Artificial Intelligence",
                        "document_count": 150,
                        "subtopics": ["Machine Learning"],
                        "parent_topic": None,
                        "metadata": {},
                    }
                ],
                "total_topics": 1,
                "total_documents": 150,
                "generated_at": "2025-01-08T14:30:00Z",
                "min_documents": 1,
                "max_topics": 50,
                "note": "",
            }
        }
