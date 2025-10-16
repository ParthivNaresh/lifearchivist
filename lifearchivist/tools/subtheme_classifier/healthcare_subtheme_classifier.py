"""
Healthcare subtheme classifier.

Uses the generic BaseSubthemeClassifier with Healthcare-specific rules.
"""

from typing import List

from lifearchivist.tools.subtheme_classifier.base_subtheme_classifier import (
    BaseSubthemeClassifier,
)
from lifearchivist.tools.subtheme_classifier.rules import (
    ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES,
    MEDICAL_RECORDS_SUBTHEME_RULES,
    PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES,
    TEST_RESULTS_SUBTHEME_RULES,
    SubthemeRule,
)


class HealthcareSubthemeClassifier(BaseSubthemeClassifier):
    """
    Healthcare document subtheme classifier.

    Inherits all classification logic from BaseSubthemeClassifier
    and provides Healthcare-specific rules for:
    - Medical Records (immunization records, medical history, discharge summaries, etc.)
    - Test Results (lab results, imaging reports, diagnostic tests, etc.)
    - Prescriptions and Medications (prescriptions, medication lists, prior authorizations, etc.)
    - Administrative and Insurance (medical bills, insurance cards, HIPAA forms, etc.)
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize Healthcare subtheme classifier.

        Args:
            max_workers: Maximum number of threads for parallel classification
        """
        # Combine all healthcare subtheme rules
        healthcare_rules: List[SubthemeRule] = (
            MEDICAL_RECORDS_SUBTHEME_RULES
            + TEST_RESULTS_SUBTHEME_RULES
            + PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES
            + ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES
        )

        # Initialize base classifier with Healthcare rules
        super().__init__(
            theme_name="Healthcare", rules=healthcare_rules, max_workers=max_workers
        )
