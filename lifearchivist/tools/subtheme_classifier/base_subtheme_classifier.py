"""
Base subtheme classifier with generic classification logic.

This classifier can be used for any theme by providing the appropriate rules.
Follows DRY principles by centralizing all classification logic.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from lifearchivist.tools.subtheme_classifier.models import SubthemeResult
from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule
from lifearchivist.utils.logging import log_event


class BaseSubthemeClassifier:
    """
    Generic high-performance subtheme classifier.

    This base classifier implements all classification logic and can be used
    for any theme by providing the appropriate rules. Follows DRY principles
    by avoiding code duplication across theme-specific classifiers.

    Features:
    - Pre-compiled regex patterns for speed
    - Cascade approach: fast filters first, expensive processing only when needed
    - Parallel classification for multiple subthemes
    - Exclusion rules to prevent false positives
    """

    def __init__(
        self, theme_name: str, rules: List[SubthemeRule], max_workers: int = 4
    ):
        """
        Initialize classifier with theme-specific rules.

        Args:
            theme_name: Name of the primary theme (e.g., "Financial", "Healthcare")
            rules: List of SubthemeRule objects for this theme
            max_workers: Maximum number of threads for parallel classification
        """
        self.theme_name = theme_name
        self.max_workers = max_workers
        self.all_rules = rules

        # Build rule lookup by category for faster filtering
        self.rules_by_category: Dict[str, List[SubthemeRule]] = {}
        for rule in self.all_rules:
            category = rule.subtheme_category
            if category not in self.rules_by_category:
                self.rules_by_category[category] = []
            self.rules_by_category[category].append(rule)

        # Pre-compile all patterns for performance
        self._compile_patterns()

    def _compile_unique_patterns(
        self, rule: SubthemeRule, rule_patterns: Dict[str, List[Any]]
    ) -> None:
        """
        Compile unique patterns for a rule.

        Args:
            rule: SubthemeRule to compile patterns for
            rule_patterns: Dictionary to store compiled patterns
        """
        for pattern, confidence, name in rule.unique_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                rule_patterns["unique"].append((compiled, confidence, name))
            except re.error as e:
                log_event(
                    "pattern_compilation_error",
                    {
                        "theme": self.theme_name,
                        "rule": rule.name,
                        "pattern": pattern,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

    def _compile_structure_patterns(
        self, rule: SubthemeRule, rule_patterns: Dict[str, List[Any]]
    ) -> None:
        """
        Compile structure patterns for a rule.

        Args:
            rule: SubthemeRule to compile patterns for
            rule_patterns: Dictionary to store compiled patterns
        """
        for pattern, weight in rule.structure_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                rule_patterns["structure"].append((compiled, weight))
            except re.error as e:
                log_event(
                    "pattern_compilation_error",
                    {
                        "theme": self.theme_name,
                        "rule": rule.name,
                        "pattern": pattern,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

    def _compile_exclusion_patterns(
        self, rule: SubthemeRule, rule_patterns: Dict[str, List[Any]]
    ) -> None:
        """
        Compile exclusion patterns for a rule.

        Args:
            rule: SubthemeRule to compile patterns for
            rule_patterns: Dictionary to store compiled patterns
        """
        for pattern in rule.exclude_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                rule_patterns["exclude"].append(compiled)
            except re.error as e:
                log_event(
                    "pattern_compilation_error",
                    {
                        "theme": self.theme_name,
                        "rule": rule.name,
                        "pattern": pattern,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

    def _compile_filename_patterns(
        self, rule: SubthemeRule, rule_patterns: Dict[str, List[Any]]
    ) -> None:
        """
        Compile filename patterns for a rule.

        Args:
            rule: SubthemeRule to compile patterns for
            rule_patterns: Dictionary to store compiled patterns
        """
        for pattern in rule.filename_patterns.keys():
            try:
                rule_patterns["filename"].append(pattern.lower())
            except Exception as e:
                log_event(
                    "filename_pattern_error",
                    {
                        "theme": self.theme_name,
                        "rule": rule.name,
                        "pattern": pattern,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

    def _compile_patterns(self):
        """Pre-compile all regex patterns for each rule."""
        self.compiled_patterns: Dict[str, Dict] = {}

        for rule in self.all_rules:
            rule_patterns: Dict[str, List[Any]] = {
                "unique": [],
                "structure": [],
                "exclude": [],
                "filename": [],
            }

            self._compile_unique_patterns(rule, rule_patterns)
            self._compile_structure_patterns(rule, rule_patterns)
            self._compile_exclusion_patterns(rule, rule_patterns)
            self._compile_filename_patterns(rule, rule_patterns)

            self.compiled_patterns[rule.name] = rule_patterns

    def _create_empty_result(self, reason: str) -> SubthemeResult:
        """
        Create an empty SubthemeResult with a reason.

        Args:
            reason: Reason for empty result

        Returns:
            Empty SubthemeResult
        """
        return SubthemeResult(
            primary_theme=self.theme_name,
            subthemes=[],
            primary_subtheme=None,
            subclassifications=[],
            primary_subclassification=None,
            subclassification_confidence=None,
            confidence_scores={},
            metadata={"reason": reason},
        )

    def _run_parallel_classification(
        self, text_lower: str, filename_lower: str
    ) -> Dict[str, Tuple[float, Dict[str, Any]]]:
        """
        Run classification for all rules in parallel.

        Args:
            text_lower: Lowercase document text
            filename_lower: Lowercase filename

        Returns:
            Dictionary mapping rule names to (confidence, pattern) tuples
        """
        results: Dict[str, Tuple[float, Dict[str, Any]]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._classify_single_rule, rule, text_lower, filename_lower
                ): rule
                for rule in self.all_rules
            }

            for future in futures:
                rule = futures[future]
                try:
                    confidence, matched_pattern = future.result(timeout=1.0)
                    if confidence > 0:
                        results[rule.name] = (confidence, matched_pattern)
                except Exception as e:
                    log_event(
                        "subtheme_classification_error",
                        {"theme": self.theme_name, "rule": rule.name, "error": str(e)},
                        level=logging.DEBUG,
                    )

        return results

    def _filter_and_sort_results(
        self, results: Dict[str, Tuple[float, Dict[str, Any]]]
    ) -> List[Tuple[str, Tuple[float, Dict[str, Any]]]]:
        """
        Filter results by confidence threshold and sort by confidence.

        Args:
            results: Raw classification results

        Returns:
            Filtered and sorted list of (name, (confidence, pattern)) tuples
        """
        sorted_results = sorted(results.items(), key=lambda x: x[1][0], reverse=True)
        confidence_threshold = 0.4
        return [
            (name, conf_pattern)
            for name, conf_pattern in sorted_results
            if conf_pattern[0] >= confidence_threshold
        ]

    def _build_classification_data(
        self, filtered_results: List[Tuple[str, Tuple[float, Dict[str, Any]]]]
    ) -> Tuple[List[str], Dict[str, str], set, Dict[str, float], Dict[str, Dict]]:
        """
        Build classification data structures from filtered results.

        Args:
            filtered_results: Filtered and sorted results

        Returns:
            Tuple of (subclassifications, category_mapping, subtheme_categories,
                     confidence_scores, matched_patterns)
        """
        rule_lookup = {rule.name: rule for rule in self.all_rules}
        subclassifications = []
        category_mapping = {}
        subtheme_categories = set()
        confidence_scores = {}
        matched_patterns = {}

        for name, (conf, pattern) in filtered_results:
            rule = rule_lookup[name]
            display_name = rule.display_name

            subclassifications.append(display_name)
            category_mapping[display_name] = rule.subtheme_category
            subtheme_categories.add(rule.subtheme_category)
            confidence_scores[display_name] = conf
            matched_patterns[display_name] = pattern

        return (
            subclassifications,
            category_mapping,
            subtheme_categories,
            confidence_scores,
            matched_patterns,
        )

    def _determine_classification_method(self, highest_confidence: float) -> str:
        """
        Determine classification method based on confidence level.

        Args:
            highest_confidence: Highest confidence score

        Returns:
            Classification method string
        """
        if highest_confidence >= 0.85:
            return "primary"
        elif highest_confidence >= 0.60:
            return "secondary"
        else:
            return "tertiary"

    def classify(self, text: str, metadata: Optional[Dict] = None) -> SubthemeResult:
        """
        Classify document into subthemes using cascade approach.

        Args:
            text: Document text content
            metadata: Optional metadata (filename, etc.)

        Returns:
            SubthemeResult with classified subthemes and confidence scores
        """
        if not text or len(text.strip()) < 10:
            return self._create_empty_result("insufficient_text")

        text_lower = text.lower()
        filename_lower = metadata.get("filename", "").lower() if metadata else ""

        results = self._run_parallel_classification(text_lower, filename_lower)

        if not results:
            return self._create_empty_result("no_matches")

        filtered_results = self._filter_and_sort_results(results)

        if not filtered_results:
            return self._create_empty_result("below_threshold")

        (
            subclassifications,
            category_mapping,
            subtheme_categories,
            confidence_scores,
            matched_patterns,
        ) = self._build_classification_data(filtered_results)

        primary_subclassification = (
            subclassifications[0] if subclassifications else None
        )
        primary_subtheme = (
            category_mapping.get(primary_subclassification)
            if primary_subclassification
            else None
        )
        subclassification_confidence = (
            confidence_scores.get(primary_subclassification)
            if primary_subclassification
            else None
        )

        highest_confidence = filtered_results[0][1][0]
        subclassification_method = self._determine_classification_method(
            highest_confidence
        )

        return SubthemeResult(
            primary_theme=self.theme_name,
            subthemes=sorted(subtheme_categories),
            primary_subtheme=primary_subtheme,
            subclassifications=subclassifications,
            primary_subclassification=primary_subclassification,
            subclassification_confidence=subclassification_confidence,
            confidence_scores=confidence_scores,
            category_mapping=category_mapping,
            matched_patterns=matched_patterns,
            subclassification_method=subclassification_method,
            metadata={
                "total_matches": len(results),
                "filtered_matches": len(filtered_results),
                "highest_confidence": highest_confidence,
            },
        )

    def _classify_single_rule(
        self, rule: SubthemeRule, text_lower: str, filename_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Classify text against a single subtheme rule using cascade approach.

        Args:
            rule: SubthemeRule to check against
            text_lower: Lowercase document text
            filename_lower: Lowercase filename

        Returns:
            Tuple of (confidence score, detailed match information)
        """
        # Check exclusion rules first (fast rejection)
        if self._check_exclusions(rule, text_lower):
            return 0.0, {}

        # Collect all matches from all levels
        all_matches: Dict[str, Dict[str, Any]] = {
            "primary": {},
            "secondary": {},
            "tertiary": {},
        }

        # Primary identifiers (highest confidence)
        primary_confidence, primary_matches = self._check_primary_identifiers(
            rule, text_lower
        )
        if primary_matches:
            all_matches["primary"] = primary_matches

        # Secondary identifiers (structure patterns)
        secondary_confidence, secondary_matches = self._check_secondary_identifiers(
            rule, text_lower
        )
        if secondary_matches:
            all_matches["secondary"] = secondary_matches

        # Tertiary identifiers (keywords and filename)
        tertiary_confidence, tertiary_matches = self._check_tertiary_identifiers(
            rule, text_lower, filename_lower
        )
        if tertiary_matches:
            all_matches["tertiary"] = tertiary_matches

        # Determine final confidence based on cascade approach
        final_confidence = 0.0
        subclassification_match_tier = ""

        if primary_confidence >= 0.85:
            final_confidence = primary_confidence
            subclassification_match_tier = "primary"
        elif secondary_confidence >= 0.60:
            final_confidence = secondary_confidence
            subclassification_match_tier = "secondary"
        elif primary_confidence > 0 and secondary_confidence > 0:
            # Weighted combination
            final_confidence = min(
                0.95, primary_confidence * 0.7 + secondary_confidence * 0.3
            )
            subclassification_match_tier = "combined_primary_secondary"
        elif primary_confidence > 0:
            final_confidence = primary_confidence
            subclassification_match_tier = "primary"
        elif secondary_confidence > 0 and tertiary_confidence > 0:
            # Boost secondary if tertiary also matches
            final_confidence = min(
                0.80, secondary_confidence * 0.8 + tertiary_confidence * 0.2
            )
            subclassification_match_tier = "combined_secondary_tertiary"
        elif secondary_confidence > 0:
            final_confidence = secondary_confidence
            subclassification_match_tier = "secondary"
        else:
            final_confidence = tertiary_confidence
            subclassification_match_tier = "tertiary" if tertiary_confidence > 0 else ""

        # Build detailed match info
        match_details = {
            "confidence": final_confidence,
            "classification_level": subclassification_match_tier,
            "matches": all_matches,
        }

        return final_confidence, match_details

    def _check_exclusions(self, rule: SubthemeRule, text_lower: str) -> bool:
        """
        Check if text contains exclusion patterns or phrases.

        Returns:
            True if document should be excluded from this subtheme
        """
        # Check exclusion patterns
        patterns = self.compiled_patterns.get(rule.name, {}).get("exclude", [])
        for pattern in patterns:
            if pattern.search(text_lower):
                return True

        # Check exclusion phrases
        for phrase in rule.exclude_phrases:
            if phrase.lower() in text_lower:
                return True

        return False

    def _check_primary_identifiers(
        self, rule: SubthemeRule, text_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Check primary identifiers (unique patterns and definitive phrases)."""
        max_confidence = 0.0
        all_matches: Dict[str, List[Dict[str, Any]]] = {
            "unique_patterns": [],
            "definitive_phrases": [],
            "form_numbers": [],
        }

        # Check unique patterns
        patterns = self.compiled_patterns.get(rule.name, {}).get("unique", [])
        for pattern, confidence, name in patterns:
            if pattern.search(text_lower):
                all_matches["unique_patterns"].append(
                    {
                        "name": name,
                        "confidence": confidence,
                        "pattern": pattern.pattern[:100],  # First 100 chars of regex
                    }
                )
                max_confidence = max(max_confidence, confidence)

        # Check definitive phrases
        for phrase, confidence in rule.definitive_phrases.items():
            if phrase.lower() in text_lower:
                all_matches["definitive_phrases"].append(
                    {"phrase": phrase, "confidence": confidence}
                )
                max_confidence = max(max_confidence, confidence)

        # Check form numbers if any
        for form_number, confidence in rule.form_numbers.items():
            if form_number.lower() in text_lower:
                all_matches["form_numbers"].append(
                    {"form": form_number, "confidence": confidence}
                )
                max_confidence = max(max_confidence, confidence)

        # Clean up empty lists
        all_matches = {k: v for k, v in all_matches.items() if v}

        return max_confidence, all_matches

    def _check_secondary_identifiers(
        self, rule: SubthemeRule, text_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Check secondary identifiers (structure patterns)."""
        patterns = self.compiled_patterns.get(rule.name, {}).get("structure", [])

        if not patterns:
            return 0.0, {}

        total_weight = sum(weight for _, weight in patterns)
        matched_weight = 0.0
        matched_patterns = []

        for pattern, weight in patterns:
            if pattern.search(text_lower):
                matched_weight += weight
                matched_patterns.append(
                    {
                        "pattern": pattern.pattern[:100],  # First 100 chars of regex
                        "weight": weight,
                        "confidence": weight
                        / total_weight,  # Individual pattern confidence
                    }
                )

        if matched_weight == 0:
            return 0.0, {}

        # Scale to 0.60-0.80 range for secondary identifiers
        raw_score = matched_weight / total_weight
        confidence = 0.60 + (raw_score * 0.20)

        # Return detailed match information
        match_info = {
            "structure_patterns": matched_patterns,
            "total_matched": len(matched_patterns),
            "total_patterns": len(patterns),
            "combined_confidence": confidence,
        }

        return confidence, match_info

    def _check_filename_patterns(
        self, rule: SubthemeRule, filename_lower: str
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Check filename patterns for matches.

        Args:
            rule: SubthemeRule to check against
            filename_lower: Lowercase filename

        Returns:
            Tuple of (max_confidence, matched_patterns_list)
        """
        max_confidence = 0.0
        matched_patterns: List[Dict[str, Any]] = []

        if not filename_lower:
            return max_confidence, matched_patterns

        for pattern, pattern_confidence in rule.filename_patterns.items():
            if pattern.lower() in filename_lower:
                scaled_confidence = pattern_confidence * 0.7
                matched_patterns.append(
                    {"pattern": pattern, "confidence": scaled_confidence}
                )
                max_confidence = max(max_confidence, scaled_confidence)

        return max_confidence, matched_patterns

    def _calculate_keyword_confidence(
        self, keyword_match_count: int, match_ratio: float
    ) -> float:
        """
        Calculate keyword confidence based on match count and ratio.

        Args:
            keyword_match_count: Number of keywords matched
            match_ratio: Ratio of matched keywords to total keywords

        Returns:
            Calculated confidence score
        """
        if keyword_match_count >= 10:
            base_confidence = 0.70
        elif keyword_match_count >= 7:
            base_confidence = 0.60
        elif keyword_match_count >= 5:
            base_confidence = 0.50
        elif keyword_match_count >= 3:
            base_confidence = 0.45
        else:
            base_confidence = 0.40

        adjusted_confidence = base_confidence * (1 + match_ratio * 0.2)
        return min(0.70, adjusted_confidence)

    def _check_keyword_matches(
        self, rule: SubthemeRule, text_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Check keyword matches in text.

        Args:
            rule: SubthemeRule to check against
            text_lower: Lowercase document text

        Returns:
            Tuple of (confidence, keyword_match_info)
        """
        words = set(re.findall(r"\b[a-z]{3,}\b", text_lower))

        if not words:
            return 0.0, {}

        keyword_matches = words & rule.keywords
        if not keyword_matches:
            return 0.0, {}

        match_ratio = len(keyword_matches) / len(rule.keywords)
        keyword_confidence = self._calculate_keyword_confidence(
            len(keyword_matches), match_ratio
        )

        keyword_info = {
            "matched": list(keyword_matches),
            "count": len(keyword_matches),
            "total_keywords": len(rule.keywords),
            "match_ratio": match_ratio,
            "confidence": keyword_confidence,
        }

        return keyword_confidence, keyword_info

    def _check_tertiary_identifiers(
        self, rule: SubthemeRule, text_lower: str, filename_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Check tertiary identifiers (keywords and filename patterns)."""
        all_matches: Dict[str, Any] = {}

        filename_confidence, filename_patterns = self._check_filename_patterns(
            rule, filename_lower
        )
        if filename_patterns:
            all_matches["filename_patterns"] = filename_patterns

        keyword_confidence, keyword_info = self._check_keyword_matches(rule, text_lower)
        if keyword_info:
            all_matches["keywords"] = keyword_info

        max_confidence = max(filename_confidence, keyword_confidence)

        return max_confidence, all_matches

    def get_supported_subthemes(self) -> List[str]:
        """Get list of all supported subthemes for this theme."""
        return [rule.display_name for rule in self.all_rules]

    def get_subthemes_by_category(self, category: str) -> List[str]:
        """Get subthemes for a specific category."""
        if category in self.rules_by_category:
            return [rule.display_name for rule in self.rules_by_category[category]]
        return []

    def get_categories(self) -> List[str]:
        """Get list of all subtheme categories."""
        return list(self.rules_by_category.keys())
