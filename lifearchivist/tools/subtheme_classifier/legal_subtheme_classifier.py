"""
Legal subtheme classifier.

Uses the generic BaseSubthemeClassifier with Legal-specific rules.
"""

from typing import List

from lifearchivist.tools.subtheme_classifier.base_subtheme_classifier import (
    BaseSubthemeClassifier,
)
from lifearchivist.tools.subtheme_classifier.rules import (
    CONTRACTS_AGREEMENTS_SUBTHEME_RULES,
    COURT_PROCEEDINGS_SUBTHEME_RULES,
    ESTATE_FAMILY_SUBTHEME_RULES,
    PROPERTY_REAL_ESTATE_SUBTHEME_RULES,
    SubthemeRule,
)


class LegalSubthemeClassifier(BaseSubthemeClassifier):
    """
    Legal document subtheme classifier.

    Inherits all classification logic from BaseSubthemeClassifier
    and provides Legal-specific rules.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize Legal subtheme classifier.

        Args:
            max_workers: Maximum number of threads for parallel classification
        """
        # Combine all legal subtheme rules
        legal_rules: List[SubthemeRule] = (
            CONTRACTS_AGREEMENTS_SUBTHEME_RULES
            + ESTATE_FAMILY_SUBTHEME_RULES
            + PROPERTY_REAL_ESTATE_SUBTHEME_RULES
            + COURT_PROCEEDINGS_SUBTHEME_RULES
        )

        # Initialize base classifier with Legal rules
        super().__init__(theme_name="Legal", rules=legal_rules, max_workers=max_workers)
