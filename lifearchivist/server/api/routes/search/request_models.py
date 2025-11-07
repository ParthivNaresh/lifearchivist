from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import (
    DEFAULT_CONTEXT_LIMIT,
    MAX_CONTEXT_LIMIT,
    MIN_CONTEXT_LIMIT,
    MIN_QUESTION_LENGTH,
)


class AskQuestionRequest(BaseModel):
    """Request to ask a question."""

    question: str = Field(
        ..., description="Question to ask", min_length=MIN_QUESTION_LENGTH
    )
    context_limit: int = Field(
        default=DEFAULT_CONTEXT_LIMIT,
        ge=MIN_CONTEXT_LIMIT,
        le=MAX_CONTEXT_LIMIT,
        description="Maximum context documents to retrieve",
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional filters for document search"
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        return v.strip()
