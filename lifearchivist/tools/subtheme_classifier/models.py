"""
Models for subtheme classification.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SubthemeResult(BaseModel):
    """Result of subtheme classification."""

    primary_theme: str = Field(description="Primary theme of the document")

    # Subtheme level (e.g., Banking, Investment, Insurance)
    subthemes: List[str] = Field(
        default_factory=list,
        description="List of applicable subtheme categories (e.g., Banking, Investment)",
    )
    primary_subtheme: Optional[str] = Field(
        None, description="Primary subtheme category (e.g., Investment)"
    )

    # Subclassification level (e.g., Bank Statement, Brokerage Statement)
    subclassifications: List[str] = Field(
        default_factory=list,
        description="List of applicable subclassifications (e.g., Bank Statement, Brokerage Statement)",
    )
    primary_subclassification: Optional[str] = Field(
        None, description="Most likely subclassification"
    )
    subclassification_confidence: Optional[float] = Field(
        None, description="Confidence for primary subclassification"
    )

    # Confidence scores for subclassifications
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict, description="Confidence score for each subclassification"
    )

    # Category mapping (subclassification -> subtheme category)
    category_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of subclassifications to their subtheme categories",
    )

    matched_patterns: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed pattern matches for each subclassification",
    )
    subclassification_method: str = Field(
        default="rules", description="Tier of subclassification"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional classification metadata"
    )
