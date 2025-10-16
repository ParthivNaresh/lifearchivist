"""
Healthcare subtheme classification rules.

This module contains all Healthcare-specific subtheme rules organized by category:
- Medical Records: Medical history, discharge summaries, immunization records
- Test Results: Lab results, imaging reports, diagnostic tests
- Prescriptions and Medications: Prescription labels, medication lists, prior authorizations
- Administrative and Insurance: Medical bills, insurance cards, HIPAA forms
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule
from lifearchivist.tools.subtheme_classifier.rules.healthcare.administrative import (
    ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES,
    ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES_DICT,
    HIPAA_FORMS,
    INSURANCE_CARD,
    MEDICAL_BILL,
)
from lifearchivist.tools.subtheme_classifier.rules.healthcare.medical_records import (
    DISCHARGE_SUMMARY,
    IMMUNIZATION_RECORD,
    MEDICAL_HISTORY,
    MEDICAL_RECORDS_SUBTHEME_RULES,
    MEDICAL_RECORDS_SUBTHEME_RULES_DICT,
)
from lifearchivist.tools.subtheme_classifier.rules.healthcare.prescriptions import (
    MEDICATION_LIST,
    PRESCRIPTION_LABEL,
    PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES,
    PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES_DICT,
    PRIOR_AUTHORIZATION,
)
from lifearchivist.tools.subtheme_classifier.rules.healthcare.test_results import (
    DIAGNOSTIC_TEST,
    IMAGING_REPORT,
    LAB_RESULTS,
    TEST_RESULTS_SUBTHEME_RULES,
    TEST_RESULTS_SUBTHEME_RULES_DICT,
)

# Combine all Healthcare subtheme rules
HEALTHCARE_SUBTHEME_RULES: List[SubthemeRule] = (
    MEDICAL_RECORDS_SUBTHEME_RULES
    + TEST_RESULTS_SUBTHEME_RULES
    + PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES
    + ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES
)

# Create lookup dictionary for quick access
HEALTHCARE_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in HEALTHCARE_SUBTHEME_RULES
}

# Export all rules and collections
__all__ = [
    # Medical Records
    "MEDICAL_HISTORY",
    "DISCHARGE_SUMMARY",
    "IMMUNIZATION_RECORD",
    "MEDICAL_RECORDS_SUBTHEME_RULES",
    "MEDICAL_RECORDS_SUBTHEME_RULES_DICT",
    # Test Results
    "LAB_RESULTS",
    "IMAGING_REPORT",
    "DIAGNOSTIC_TEST",
    "TEST_RESULTS_SUBTHEME_RULES",
    "TEST_RESULTS_SUBTHEME_RULES_DICT",
    # Prescriptions and Medications
    "PRESCRIPTION_LABEL",
    "MEDICATION_LIST",
    "PRIOR_AUTHORIZATION",
    "PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES",
    "PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES_DICT",
    # Administrative and Insurance
    "MEDICAL_BILL",
    "INSURANCE_CARD",
    "HIPAA_FORMS",
    "ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES",
    "ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES_DICT",
    # Combined rules
    "HEALTHCARE_SUBTHEME_RULES",
    "HEALTHCARE_SUBTHEME_RULES_DICT",
]
