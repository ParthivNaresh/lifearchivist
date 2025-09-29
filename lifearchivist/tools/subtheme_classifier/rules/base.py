"""
Base classes for subtheme classification rules.

Simple data structure for subtheme rules, following the same pattern as ThemeRule.
The cascade logic lives in the classifier, not in the rule itself.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class SubthemeRule:
    """
    Data structure for subtheme classification rules.

    Similar to ThemeRule but organized for the cascade approach:
    - Primary identifiers (unique patterns, forms, definitive phrases)
    - Secondary identifiers (structural patterns)
    - Tertiary identifiers (keywords, filename hints)
    """

    # Core identification
    name: str  # Internal identifier (e.g., "retirement_401k")
    display_name: str  # User-friendly name (e.g., "401(k) Statement")
    parent_theme: str  # Primary theme this belongs to
    subtheme_category: str = (
        ""  # Optional category within parent theme (e.g., "Retirement", "Banking")
    )

    # Primary identifiers (highest confidence 0.85-0.95)
    # These are unique, definitive patterns that strongly indicate this subtheme
    unique_patterns: List[Tuple[str, float, str]] = field(
        default_factory=list
    )  # [(pattern, confidence, name), ...]
    definitive_phrases: Dict[str, float] = field(
        default_factory=dict
    )  # {phrase: confidence, ...}
    form_numbers: Dict[str, float] = field(
        default_factory=dict
    )  # {form_id: confidence, ...}

    # Secondary identifiers (medium confidence 0.60-0.80)
    # Document structure and field patterns
    structure_patterns: List[Tuple[str, float]] = field(
        default_factory=list
    )  # [(pattern, weight), ...]

    # Tertiary identifiers (lower confidence 0.40-0.70)
    # Statistical keyword analysis and filename hints
    keywords: Set[str] = field(
        default_factory=set
    )  # Important keywords for this subtheme
    filename_patterns: Dict[str, float] = field(
        default_factory=dict
    )  # {pattern: confidence, ...}

    # Exclusion rules (veto matches)
    exclude_patterns: Set[str] = field(
        default_factory=set
    )  # Regex patterns that disqualify
    exclude_phrases: Set[str] = field(default_factory=set)  # Phrases that disqualify
