"""
Legal subtheme classification rules.

This module contains all Legal-specific subtheme rules organized by category:
- Contracts and Agreements: Lease agreements, employment agreements, service contracts, purchase agreements, NDAs
- Estate and Family: Wills, power of attorney, trust documents, divorce documents, marriage certificates
- Property and Real Estate: Property deeds, mortgage documents, title documents, HOA documents, property transfers
- Court and Legal Proceedings: Court orders, legal notices, court filings, settlement agreements, legal correspondence
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule
from lifearchivist.tools.subtheme_classifier.rules.legal.contracts_agreements import (
    CONTRACTS_AGREEMENTS_SUBTHEME_RULES,
    CONTRACTS_AGREEMENTS_SUBTHEME_RULES_DICT,
    EMPLOYMENT_AGREEMENT,
    LEASE_AGREEMENT,
    NDA,
    PURCHASE_AGREEMENT,
    SERVICE_CONTRACT,
)
from lifearchivist.tools.subtheme_classifier.rules.legal.court_proceedings import (
    COURT_FILING,
    COURT_ORDER,
    COURT_PROCEEDINGS_SUBTHEME_RULES,
    COURT_PROCEEDINGS_SUBTHEME_RULES_DICT,
    LEGAL_CORRESPONDENCE,
    LEGAL_NOTICE,
    SETTLEMENT_AGREEMENT,
)
from lifearchivist.tools.subtheme_classifier.rules.legal.estate_family import (
    DIVORCE_DOCUMENT,
    ESTATE_FAMILY_SUBTHEME_RULES,
    ESTATE_FAMILY_SUBTHEME_RULES_DICT,
    MARRIAGE_CERTIFICATE,
    POWER_OF_ATTORNEY,
    TRUST_DOCUMENT,
    WILL,
)
from lifearchivist.tools.subtheme_classifier.rules.legal.property_real_estate import (
    HOA_DOCUMENT,
    MORTGAGE_DOCUMENT,
    PROPERTY_DEED,
    PROPERTY_REAL_ESTATE_SUBTHEME_RULES,
    PROPERTY_REAL_ESTATE_SUBTHEME_RULES_DICT,
    PROPERTY_TRANSFER,
    TITLE_DOCUMENT,
)

# Combine all Legal subtheme rules
LEGAL_SUBTHEME_RULES: List[SubthemeRule] = (
    CONTRACTS_AGREEMENTS_SUBTHEME_RULES
    + ESTATE_FAMILY_SUBTHEME_RULES
    + PROPERTY_REAL_ESTATE_SUBTHEME_RULES
    + COURT_PROCEEDINGS_SUBTHEME_RULES
)

# Create lookup dictionary for quick access
LEGAL_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in LEGAL_SUBTHEME_RULES
}

# Export all rules and collections
__all__ = [
    # Contracts and Agreements
    "LEASE_AGREEMENT",
    "EMPLOYMENT_AGREEMENT",
    "SERVICE_CONTRACT",
    "PURCHASE_AGREEMENT",
    "NDA",
    "CONTRACTS_AGREEMENTS_SUBTHEME_RULES",
    "CONTRACTS_AGREEMENTS_SUBTHEME_RULES_DICT",
    # Estate and Family
    "WILL",
    "POWER_OF_ATTORNEY",
    "TRUST_DOCUMENT",
    "DIVORCE_DOCUMENT",
    "MARRIAGE_CERTIFICATE",
    "ESTATE_FAMILY_SUBTHEME_RULES",
    "ESTATE_FAMILY_SUBTHEME_RULES_DICT",
    # Property and Real Estate
    "PROPERTY_DEED",
    "MORTGAGE_DOCUMENT",
    "TITLE_DOCUMENT",
    "HOA_DOCUMENT",
    "PROPERTY_TRANSFER",
    "PROPERTY_REAL_ESTATE_SUBTHEME_RULES",
    "PROPERTY_REAL_ESTATE_SUBTHEME_RULES_DICT",
    # Court and Legal Proceedings
    "COURT_ORDER",
    "LEGAL_NOTICE",
    "COURT_FILING",
    "SETTLEMENT_AGREEMENT",
    "LEGAL_CORRESPONDENCE",
    "COURT_PROCEEDINGS_SUBTHEME_RULES",
    "COURT_PROCEEDINGS_SUBTHEME_RULES_DICT",
    # Combined rules
    "LEGAL_SUBTHEME_RULES",
    "LEGAL_SUBTHEME_RULES_DICT",
]
