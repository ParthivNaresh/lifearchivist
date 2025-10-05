"""
Financial subtheme classifier.

Uses the generic BaseSubthemeClassifier with Financial-specific rules.
"""

from typing import List

from lifearchivist.tools.subtheme_classifier.base_subtheme_classifier import (
    BaseSubthemeClassifier,
)
from lifearchivist.tools.subtheme_classifier.rules import (
    BANKING_SUBTHEME_RULES,
    INSURANCE_SUBTHEME_RULES,
    INVESTMENT_SUBTHEME_RULES,
    LOAN_SUBTHEME_RULES,
    OTHER_FINANCIAL_SUBTHEME_RULES,
    RETIREMENT_SUBTHEME_RULES,
    TAX_SUBTHEME_RULES,
    SubthemeRule,
)


class FinancialSubthemeClassifier(BaseSubthemeClassifier):
    """
    Financial document subtheme classifier.

    Inherits all classification logic from BaseSubthemeClassifier
    and provides Financial-specific rules.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize Financial subtheme classifier.

        Args:
            max_workers: Maximum number of threads for parallel classification
        """
        # Combine all financial subtheme rules
        financial_rules: List[SubthemeRule] = (
            BANKING_SUBTHEME_RULES
            + INSURANCE_SUBTHEME_RULES
            + INVESTMENT_SUBTHEME_RULES
            + LOAN_SUBTHEME_RULES
            + OTHER_FINANCIAL_SUBTHEME_RULES
            + RETIREMENT_SUBTHEME_RULES
            + TAX_SUBTHEME_RULES
        )

        # Initialize base classifier with Financial rules
        super().__init__(
            theme_name="Financial", rules=financial_rules, max_workers=max_workers
        )
