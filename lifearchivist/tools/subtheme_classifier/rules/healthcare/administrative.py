"""
Healthcare > Administrative and Insurance subtheme rules.

Defines precise, production-ready patterns for:
- Medical Bill
- Insurance Card
- HIPAA Forms

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Medical Bill - Healthcare billing statements and invoices
MEDICAL_BILL = SubthemeRule(
    name="medical_bill",
    display_name="Medical Bill",
    parent_theme="Healthcare",
    subtheme_category="Administrative and Insurance",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core billing patterns
        (
            r"(?:medical|healthcare)\s*(?:bill|invoice|statement)",
            0.95,
            "medical_bill_header",
        ),
        (r"(?:amount|balance)\s*due:?\s*\$?[\d,]+\.?\d*", 0.93, "amount_due"),
        (r"(?:total|current)\s*charges?:?\s*\$?[\d,]+\.?\d*", 0.91, "total_charges"),
        (
            r"payment\s*due\s*(?:date|by):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.90,
            "payment_due_date",
        ),
        (r"account\s*(?:number|#):?\s*[A-Z0-9\-]{5,}", 0.88, "account_number"),
        (r"statement\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.87, "statement_date"),
        (r"billing\s*(?:code|id):?\s*[A-Z0-9\-]{4,}", 0.86, "billing_code"),
        # CPT codes for medical billing
        (r"cpt\s*(?:code)?:?\s*\d{5}", 0.89, "cpt_code"),
        (r"procedure\s*code:?\s*\d{5}", 0.88, "procedure_code"),
        (r"revenue\s*code:?\s*\d{3,4}", 0.86, "revenue_code"),
        # Payment information
        (r"insurance\s*paid:?\s*\$?[\d,]+\.?\d*", 0.87, "insurance_payment"),
        (
            r"patient\s*(?:responsibility|balance):?\s*\$?[\d,]+\.?\d*",
            0.88,
            "patient_responsibility",
        ),
        (r"(?:co-?pay|copayment):?\s*\$?[\d,]+\.?\d*", 0.85, "copay_amount"),
    ],
    definitive_phrases={
        # Billing phrases
        "medical bill": 0.95,
        "healthcare invoice": 0.93,
        "billing statement": 0.91,
        "patient statement": 0.90,
        "amount due": 0.91,
        "pay this amount": 0.89,
        "payment due": 0.89,
        "account balance": 0.87,
        "past due": 0.86,
        # Service charges
        "professional services": 0.86,
        "facility charges": 0.85,
        "emergency room": 0.85,
        "outpatient services": 0.84,
        # Payment terms
        "payment options": 0.85,
        "financial assistance": 0.84,
        "payment plan": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Billing structure
        (r"service\s*date", 0.52),
        (r"date\s*of\s*service", 0.52),
        (r"provider\s*name", 0.47),
        (r"facility\s*name", 0.45),
        (r"tax\s*id", 0.42),
        # Payment information
        (r"payment\s*methods", 0.47),
        (r"payment\s*history", 0.44),
        (r"adjustments", 0.42),
        (r"credits", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Billing terms
        "bill",
        "invoice",
        "statement",
        "charge",
        "payment",
        "due",
        "balance",
        "account",
        "owe",
        "pay",
        "remit",
        "billing",
        # Service terms
        "service",
        "procedure",
        "visit",
        "encounter",
        "emergency",
        # Code terms
        "cpt",
        "icd",
        "diagnosis",
        "revenue",
        "drg",
        # Payment terms
        "insurance",
        "copay",
        "deductible",
        "coinsurance",
    },
    filename_patterns={
        "bill": 0.76,
        "invoice": 0.76,
        "statement": 0.72,
        "medical_bill": 0.78,
        "billing": 0.70,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # EOB patterns (these go to Financial)
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        r"plan\s*discount",
        r"allowed\s*amount",
        # Insurance card patterns
        r"member\s*(?:id|number):?\s*[A-Z0-9\-]{6,}",
        r"group\s*(?:number|#):?\s*[A-Z0-9\-]{4,}",
        r"(?:rx\s*)?bin:?\s*\d{6}",
        # HIPAA patterns
        r"hipaa\s*(?:notice|authorization|form)",
        r"notice\s*of\s*privacy\s*practices",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        # Test result patterns
        r"lab(?:oratory)?\s*results?",
        r"test\s*results?",
    },
    exclude_phrases={
        "explanation of benefits",
        "not a bill",
        "insurance card",
        "member id",
        "hipaa authorization",
        "privacy practices",
        "medical history",
        "lab results",
    },
)

# Insurance Card - Health insurance identification cards
INSURANCE_CARD = SubthemeRule(
    name="insurance_card",
    display_name="Insurance Card",
    parent_theme="Healthcare",
    subtheme_category="Administrative and Insurance",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core insurance card patterns
        (r"(?:health|medical)\s*insurance\s*card", 0.95, "insurance_card_header"),
        (r"member\s*(?:id|number):?\s*[A-Z0-9\-]{6,}", 0.93, "member_id"),
        (r"group\s*(?:number|#):?\s*[A-Z0-9\-]{4,}", 0.91, "group_number"),
        (r"(?:rx\s*)?bin:?\s*\d{6}", 0.89, "rx_bin_number"),
        (r"(?:rx\s*)?pcn:?\s*[A-Z0-9]{2,}", 0.88, "rx_pcn"),
        (r"(?:payer|payor)\s*id:?\s*\d{5,}", 0.87, "payer_id"),
        (
            r"effective\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.86,
            "coverage_effective_date",
        ),
        # Plan information
        (r"(?:ppo|hmo|epo|pos)\s*plan", 0.87, "plan_type"),
        (r"(?:in[- ]network|out[- ]of[- ]network)", 0.85, "network_type"),
        (r"(?:copay|co-pay):?\s*\$\d+", 0.86, "copay_amounts"),
    ],
    definitive_phrases={
        # Card phrases
        "insurance card": 0.95,
        "member id": 0.92,
        "group number": 0.90,
        "subscriber id": 0.89,
        "policy number": 0.88,
        # Coverage phrases
        "in network": 0.86,
        "out of network": 0.86,
        "copay amount": 0.85,
        "deductible": 0.84,
        "coinsurance": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Card information
        (r"subscriber\s*name", 0.50),
        (r"dependent", 0.45),
        (r"plan\s*name", 0.47),
        (r"insurance\s*company", 0.47),
        # Contact information
        (r"customer\s*service", 0.42),
        (r"claims\s*address", 0.42),
        (r"provider\s*phone", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Insurance terms
        "insurance",
        "card",
        "member",
        "subscriber",
        "group",
        "coverage",
        "plan",
        "policy",
        "network",
        # ID terms
        "id",
        "number",
        "bin",
        "pcn",
        "payer",
        # Coverage terms
        "copay",
        "deductible",
        "coinsurance",
        "ppo",
        "hmo",
    },
    filename_patterns={
        "insurance": 0.74,
        "insurance_card": 0.78,
        "member_card": 0.75,
        "health_card": 0.72,
        "id_card": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Billing patterns
        r"(?:amount|balance)\s*due",
        r"payment\s*(?:due|required)",
        r"billing\s*statement",
        r"total\s*charges",
        # HIPAA patterns
        r"hipaa\s*(?:notice|authorization|form)",
        r"notice\s*of\s*privacy\s*practices",
        r"release\s*of\s*information",
        # EOB patterns
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        # Medical record patterns
        r"medical\s*history",
        r"chief\s*complaint",
    },
    exclude_phrases={
        "amount due",
        "billing statement",
        "hipaa authorization",
        "privacy notice",
        "explanation of benefits",
        "medical history",
    },
)

# HIPAA Forms - Privacy notices and authorization forms
HIPAA_FORMS = SubthemeRule(
    name="hipaa_forms",
    display_name="HIPAA Forms",
    parent_theme="Healthcare",
    subtheme_category="Administrative and Insurance",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core HIPAA patterns
        (r"hipaa\s*(?:notice|authorization|form)", 0.95, "hipaa_document"),
        (r"notice\s*of\s*privacy\s*practices", 0.94, "privacy_notice"),
        (
            r"(?:release|disclosure)\s*of\s*(?:information|records)",
            0.92,
            "release_of_information",
        ),
        (r"patient\s*(?:consent|authorization)\s*form", 0.90, "patient_consent"),
        (r"protected\s*health\s*information", 0.89, "phi_reference"),
        (
            r"confidential(?:ity)?\s*(?:notice|agreement)",
            0.88,
            "confidentiality_notice",
        ),
        # Authorization patterns
        (r"authorization\s*to\s*(?:release|disclose)", 0.89, "authorization_release"),
        (r"medical\s*records?\s*release", 0.88, "medical_records_release"),
        (r"patient\s*rights", 0.87, "patient_rights"),
    ],
    definitive_phrases={
        # HIPAA phrases
        "hipaa authorization": 0.95,
        "privacy practices": 0.93,
        "protected health information": 0.91,
        "phi": 0.86,
        "release of information": 0.91,
        "medical records release": 0.89,
        "patient rights": 0.87,
        "confidential information": 0.86,
        "disclosure authorization": 0.88,
        # Consent phrases
        "patient consent": 0.89,
        "informed consent": 0.88,
        "consent to treatment": 0.87,
        "consent form": 0.87,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Form structure
        (r"patient\s*signature", 0.48),
        (r"date\s*signed", 0.45),
        (r"witness\s*signature", 0.42),
        (r"expiration\s*date", 0.42),
        # Authorization details
        (r"purpose\s*of\s*disclosure", 0.45),
        (r"information\s*to\s*be\s*released", 0.45),
        (r"authorized\s*recipient", 0.43),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # HIPAA terms
        "hipaa",
        "privacy",
        "confidential",
        "protected",
        "phi",
        "disclosure",
        "release",
        "consent",
        "authorization",
        "rights",
        # Form terms
        "form",
        "notice",
        "agreement",
        "signature",
        "witness",
        # Medical records terms
        "records",
        "medical",
        "health",
    },
    filename_patterns={
        "hipaa": 0.78,
        "privacy": 0.72,
        "consent": 0.70,
        "release": 0.70,
        "authorization": 0.72,
        "roi": 0.68,  # Release of Information
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Billing patterns
        r"(?:amount|balance)\s*due",
        r"payment\s*(?:due|required)",
        r"total\s*charges",
        # Insurance card patterns
        r"member\s*(?:id|number)",
        r"group\s*(?:number|#)",
        r"(?:rx\s*)?bin:?\s*\d{6}",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"physical\s*exam",
        # Referral patterns
        r"referral\s*(?:form|authorization)",
        r"specialist\s*referral",
    },
    exclude_phrases={
        "amount due",
        "billing statement",
        "insurance card",
        "member id",
        "medical history",
        "referral form",
        "lab results",
    },
)


# Export rules
ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES: List[SubthemeRule] = [
    MEDICAL_BILL,
    INSURANCE_CARD,
    HIPAA_FORMS,
]

ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in ADMINISTRATIVE_INSURANCE_SUBTHEME_RULES
}
