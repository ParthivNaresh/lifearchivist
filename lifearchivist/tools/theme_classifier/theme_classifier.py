"""
Production-grade theme classifier for Life Archivist.

Fast, accurate document classification using cascade approach.
"""

import logging
import re
from typing import Optional, Tuple

from lifearchivist.tools.theme_classifier.rules import (
    PRIMARY_DEFINITIVE_PHRASE_DEFINITIONS,
    PRIMARY_UNIQUE_PATTERN_DEFINITIONS,
    SECONDARY_STRUCTURE_PATTERN_DEFINITIONS,
    TERTIARY_FILENAME_KEYWORD_DEFINITIONS,
    TERTIARY_STATISTICAL_KEYWORD_DEFINITIONS,
)
from lifearchivist.utils.logging import log_event


class ThemeClassifier:
    """
    Fast, accurate document classifier.
    Uses cascade approach: fast filters first, expensive processing only when needed.
    """

    def __init__(self):
        """Initialize classifier with pre-compiled patterns and lookup tables."""
        self._compile_patterns()
        self._build_lookup_tables()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for speed."""
        self.primary_unique_patterns: dict[tuple[str, float, str], re.Pattern] = {
            (theme, confidence, name): re.compile(pattern, re.IGNORECASE)
            for theme, confidence, name, pattern in PRIMARY_UNIQUE_PATTERN_DEFINITIONS
        }

        self.secondary_structure_patterns: dict[str, list[tuple[re.Pattern, float]]] = {
            theme: [
                (
                    re.compile(
                        pattern,
                        re.IGNORECASE | flags if "flags" in locals() else re.IGNORECASE,
                    ),
                    confidence,
                )
                for pattern, confidence, *flags_list in patterns
                for flags in [flags_list[0] if flags_list else 0]
            ]
            for theme, patterns in SECONDARY_STRUCTURE_PATTERN_DEFINITIONS.items()
        }

    def _build_lookup_tables(self):
        """Build hash tables."""
        self.primary_definitive_phrases: dict[str, Tuple[str, float]] = {
            phrase: (theme, confidence)
            for theme, phrases in PRIMARY_DEFINITIVE_PHRASE_DEFINITIONS.items()
            for phrase, confidence in phrases
        }

        self.tertiary_statistical_keywords: dict[str, set] = (
            TERTIARY_STATISTICAL_KEYWORD_DEFINITIONS
        )

    def classify(self, text: str, filename: str = "") -> Tuple[str, float, str, str]:
        """
        Classify document with cascade approach.

        Args:
            text: Document text content
            filename: Optional filename for additional context

        Returns:
            Tuple of (theme, confidence, matched_pattern, classification_type)
        """
        if not text or len(text.strip()) < 10:
            return "Unclassified", 0.0, "", ""

        text_lower = text.lower()
        filename_lower = filename.lower()

        result = self._check_primary_identifiers(text_lower)
        if result:
            theme, confidence, pattern_or_phrase = result
            return theme, confidence, pattern_or_phrase, "primary"

        result = self._check_secondary_identifiers(text_lower)
        if result and result[1] >= 0.6:
            theme, confidence, pattern_or_phrase = result
            return theme, confidence, pattern_or_phrase, "secondary"

        result = self._check_tertiary_identifiers(filename_lower, text_lower)
        if result:
            theme, confidence, pattern_or_phrase = result
            return theme, confidence, pattern_or_phrase, "tertiary"

        return "Unclassified", 0.0, "", ""

    def _check_primary_identifiers(self, text: str) -> Optional[Tuple[str, float, str]]:
        """Check for unique identifying patterns."""

        for (
            theme,
            confidence,
            pattern_name,
        ), pattern in self.primary_unique_patterns.items():
            if pattern.search(text):
                log_event(
                    "unique_pattern_matched",
                    {"pattern": pattern_name, "theme": theme, "confidence": confidence},
                    level=logging.DEBUG,
                )
                return theme, confidence, pattern_name

        for phrase, (theme, confidence) in self.primary_definitive_phrases.items():
            if phrase in text:
                log_event(
                    "definitive_phrase_matched",
                    {"phrase": phrase, "theme": theme, "confidence": confidence},
                    level=logging.DEBUG,
                )
                return theme, confidence, phrase

        return None

    def _check_secondary_identifiers(self, text_lower: str) -> Tuple[str, float, str]:
        """Check document structure patterns."""

        best_match = None
        best_confidence = 0
        best_patterns = []

        for theme, patterns in self.secondary_structure_patterns.items():
            total_weight = 0
            matched_weight = 0
            matched_patterns = []

            for pattern, weight in patterns:
                total_weight += weight
                if pattern.search(text_lower):
                    matched_weight += weight
                    matched_patterns.append(pattern)

            if matched_weight > 0:
                confidence = (matched_weight / total_weight) * 0.8
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = theme
                    best_patterns = matched_patterns

        if best_match and best_confidence >= 0.4:
            return best_match, best_confidence, str(best_patterns)

        return best_match, best_confidence, str(best_patterns)

    def _check_tertiary_identifiers(
        self, filename: str, text_lower: str
    ) -> Tuple[str, float, str]:
        """Quick filename-based classification."""
        filename_patterns: dict[str, dict] = TERTIARY_FILENAME_KEYWORD_DEFINITIONS

        for theme, config in filename_patterns.items():
            for keyword in config["keywords"]:
                if keyword in filename:
                    return theme, config["confidence"], keyword

        words = set(re.findall(r"\b[a-z]{3,}\b", text_lower))

        if not words:
            return "Unclassified", 0.0, ""

        theme_scores = {}
        for theme, theme_words in self.tertiary_statistical_keywords.items():
            matches = words & theme_words
            if matches:
                raw_score = len(matches)
                proportion = len(matches) / len(theme_words)
                theme_scores[theme] = raw_score * (1 + proportion)

        if not theme_scores:
            return "Unclassified", 0.0, ""

        best_theme = max(theme_scores, key=theme_scores.get)
        best_score = theme_scores[best_theme]

        if best_score >= 10:
            confidence = 0.7
        elif best_score >= 7:
            confidence = 0.6
        elif best_score >= 5:
            confidence = 0.5
        elif best_score >= 3:
            confidence = 0.4
        else:
            confidence = 0.3

        return best_theme, confidence, str(theme_scores)
