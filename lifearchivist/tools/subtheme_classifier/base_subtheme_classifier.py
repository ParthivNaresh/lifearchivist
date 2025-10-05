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

    def _compile_patterns(self):
        """Pre-compile all regex patterns for each rule."""
        self.compiled_patterns: Dict[str, Dict] = {}

        for rule in self.all_rules:
            rule_patterns = {
                "unique": [],
                "structure": [],
                "exclude": [],
                "filename": [],
            }

            # Compile unique patterns
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

            # Compile structure patterns
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

            # Compile exclusion patterns
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

            # Compile filename patterns (simple substring matches)
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

            self.compiled_patterns[rule.name] = rule_patterns

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
            return SubthemeResult(
                primary_theme=self.theme_name,
                subthemes=[],
                primary_subtheme=None,
                subclassifications=[],
                primary_subclassification=None,
                confidence_scores={},
                metadata={"reason": "insufficient_text"},
            )

        # Preprocess text once
        text_lower = text.lower()
        filename_lower = metadata.get("filename", "").lower() if metadata else ""

        # Run cascade classification for all rules in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit classification tasks for each rule
            futures = {
                executor.submit(
                    self._classify_single_rule, rule, text_lower, filename_lower
                ): rule
                for rule in self.all_rules
            }

            # Collect results (now includes matched pattern)
            results: Dict[str, Tuple[float, Dict[str, Any]]] = {}
            for future in futures:
                rule = futures[future]
                try:
                    confidence, matched_pattern = future.result(
                        timeout=1.0
                    )  # 1 second timeout per rule
                    if confidence > 0:
                        results[rule.name] = (confidence, matched_pattern)
                except Exception as e:
                    log_event(
                        "subtheme_classification_error",
                        {"theme": self.theme_name, "rule": rule.name, "error": str(e)},
                        level=logging.DEBUG,
                    )

        # Filter and sort results
        if not results:
            return SubthemeResult(
                primary_theme=self.theme_name,
                subthemes=[],
                primary_subtheme=None,
                subclassifications=[],
                primary_subclassification=None,
                confidence_scores={},
                metadata={"reason": "no_matches"},
            )

        # Sort by confidence (x[1][0] is the confidence in the tuple)
        sorted_results = sorted(results.items(), key=lambda x: x[1][0], reverse=True)

        # Apply confidence threshold
        confidence_threshold = 0.4
        filtered_results = [
            (name, conf_pattern)
            for name, conf_pattern in sorted_results
            if conf_pattern[0] >= confidence_threshold
        ]

        if not filtered_results:
            return SubthemeResult(
                primary_theme=self.theme_name,
                subthemes=[],
                primary_subtheme=None,
                subclassifications=[],
                primary_subclassification=None,
                confidence_scores={},
                metadata={"reason": "below_threshold"},
            )

        # Get display names and categories for results
        rule_lookup = {rule.name: rule for rule in self.all_rules}

        # Build subclassifications list and category mapping
        subclassifications = []
        category_mapping = {}
        subtheme_categories = set()

        for name, _ in filtered_results:
            rule = rule_lookup[name]
            display_name = rule.display_name
            category = rule.subtheme_category

            subclassifications.append(display_name)
            category_mapping[display_name] = category
            subtheme_categories.add(category)

        primary_subclassification = (
            subclassifications[0] if subclassifications else None
        )
        primary_subtheme = (
            category_mapping.get(primary_subclassification)
            if primary_subclassification
            else None
        )

        # Build confidence scores and matched patterns with display names
        confidence_scores = {}
        matched_patterns = {}
        for name, (conf, pattern) in filtered_results:
            display_name = rule_lookup[name].display_name
            confidence_scores[display_name] = conf
            matched_patterns[display_name] = pattern

        # Get confidence for primary subclassification
        subclassification_confidence = (
            confidence_scores.get(primary_subclassification)
            if primary_subclassification
            else None
        )

        # Determine classification method based on highest confidence
        highest_confidence = filtered_results[0][1][0]  # First item's confidence
        if highest_confidence >= 0.85:
            subclassification_method = "primary"
        elif highest_confidence >= 0.60:
            subclassification_method = "secondary"
        else:
            subclassification_method = "tertiary"

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
        all_matches = {"primary": {}, "secondary": {}, "tertiary": {}}

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
        all_matches = {
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

    def _check_tertiary_identifiers(
        self, rule: SubthemeRule, text_lower: str, filename_lower: str
    ) -> Tuple[float, Dict[str, Any]]:
        """Check tertiary identifiers (keywords and filename patterns)."""
        max_confidence = 0.0
        all_matches = {"filename_patterns": [], "keywords": {}}

        # Check filename patterns first (quick check)
        if filename_lower:
            for pattern, pattern_confidence in rule.filename_patterns.items():
                if pattern.lower() in filename_lower:
                    scaled_confidence = (
                        pattern_confidence * 0.7
                    )  # Scale down filename confidence
                    all_matches["filename_patterns"].append(
                        {"pattern": pattern, "confidence": scaled_confidence}
                    )
                    max_confidence = max(max_confidence, scaled_confidence)

        # Extract words for keyword matching
        words = set(re.findall(r"\b[a-z]{3,}\b", text_lower))

        if words:
            # Calculate keyword match score
            keyword_matches = words & rule.keywords
            if keyword_matches:
                match_ratio = len(keyword_matches) / len(rule.keywords)

                # Scale based on number of matches and ratio
                if len(keyword_matches) >= 10:
                    keyword_confidence = 0.70
                elif len(keyword_matches) >= 7:
                    keyword_confidence = 0.60
                elif len(keyword_matches) >= 5:
                    keyword_confidence = 0.50
                elif len(keyword_matches) >= 3:
                    keyword_confidence = 0.45
                else:
                    keyword_confidence = 0.40

                # Adjust by match ratio
                keyword_confidence *= 1 + match_ratio * 0.2
                keyword_confidence = min(0.70, keyword_confidence)

                all_matches["keywords"] = {
                    "matched": list(keyword_matches),
                    "count": len(keyword_matches),
                    "total_keywords": len(rule.keywords),
                    "match_ratio": match_ratio,
                    "confidence": keyword_confidence,
                }

                max_confidence = max(max_confidence, keyword_confidence)

        # Clean up empty entries
        if not all_matches["filename_patterns"]:
            del all_matches["filename_patterns"]
        if not all_matches.get("keywords", {}).get("matched"):
            all_matches.pop("keywords", None)

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
