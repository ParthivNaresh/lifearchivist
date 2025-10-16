"""
Financial > Insurance subtheme rules.

Defines precise, production-ready patterns for:
- Insurance Policy
- Insurance Claim
- Explanation of Benefits (EOB)

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# Insurance Policy
INSURANCE_POLICY = SubthemeRule(
    name="insurance_policy",
    display_name="Insurance Policy",
    parent_theme="Financial",
    subtheme_category="Insurance",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core policy identifiers
        (r"policy\s*(?:number|no\.?):?\s*[A-Z0-9\-]{5,}", 0.92, "policy_number_field"),
        (r"policy\s*effective\s*date", 0.90, "policy_effective_date"),
        (r"policy\s*expiration\s*date", 0.90, "policy_expiration_date"),
        (r"coverage\s*limits?", 0.88, "coverage_limits_section"),
        (r"declarations?\s*page", 0.95, "declarations_page"),
        # Premium and coverage patterns
        (r"(?:annual|monthly|quarterly)\s*premium", 0.88, "premium_amount"),
        (r"deductible\s*:?\s*\$", 0.86, "deductible_amount"),
        (r"liability\s*coverage", 0.85, "liability_coverage"),
        # Policy-specific sections
        (
            r"insured\s*property|insured\s*vehicle|insured\s*person",
            0.87,
            "insured_entity",
        ),
        (r"coverage\s*summary", 0.86, "coverage_summary_section"),
    ],
    definitive_phrases={
        "insurance policy": 0.95,
        "policy declarations": 0.95,
        "coverage effective": 0.90,
        "policy period": 0.88,
        "named insured": 0.88,
        "additional insured": 0.85,
        "coverage territory": 0.82,
        "policy provisions": 0.82,
        "exclusions and limitations": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"endorsements?", 0.50),
        (r"riders?", 0.45),
        (r"conditions\s*and\s*exclusions", 0.45),
        (r"definitions\s*section", 0.40),
        (r"cancellation\s*provisions", 0.40),
        (r"renewal\s*terms", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "policy",
        "coverage",
        "premium",
        "deductible",
        "liability",
        "insured",
        "declarations",
        "endorsement",
        "rider",
        "exclusions",
        "provisions",
        "effective",
        "expiration",
        "renewal",
    },
    filename_patterns={
        "policy": 0.75,
        "insurance": 0.70,
        "declarations": 0.70,
        "coverage": 0.65,
    },
    # Exclusions to prevent confusion with other insurance documents
    exclude_patterns={
        # EOB-specific patterns
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        r"patient\s*responsibility",
        r"allowed\s*amount",
        r"provider\s*charges",
        # Claim-specific patterns
        r"claim\s*number",
        r"date\s*of\s*loss",
        r"claim\s*status",
        r"settlement\s*amount",
        # Medical/healthcare specific
        r"diagnosis\s*code",
        r"procedure\s*code",
        r"cpt\s*code",
    },
    exclude_phrases={
        "claim form",
        "loss report",
    },
)

# Insurance Claim
INSURANCE_CLAIM = SubthemeRule(
    name="insurance_claim",
    display_name="Insurance Claim",
    parent_theme="Financial",
    subtheme_category="Insurance",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core claim identifiers
        (r"claim\s*(?:number|no\.?):?\s*[A-Z0-9\-]{5,}", 0.95, "claim_number_field"),
        (r"date\s*of\s*loss", 0.92, "date_of_loss"),
        (r"claim\s*status", 0.90, "claim_status"),
        (r"loss\s*description", 0.88, "loss_description"),
        # Settlement and payment patterns
        (r"settlement\s*amount", 0.90, "settlement_amount"),
        (r"claim\s*payment", 0.88, "claim_payment"),
        (r"reserve\s*amount", 0.85, "reserve_amount"),
        # Adjuster and investigation
        (r"adjuster\s*(?:name|assigned)", 0.86, "adjuster_info"),
        (r"investigation\s*(?:report|summary)", 0.85, "investigation_section"),
    ],
    definitive_phrases={
        "claim form": 0.95,
        "loss report": 0.92,
        "first notice of loss": 0.90,
        "proof of loss": 0.88,
        "claim settlement": 0.88,
        "claim denied": 0.85,
        "claim approved": 0.85,
        "supplemental claim": 0.82,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"incident\s*(?:report|details)", 0.50),
        (r"damages?\s*(?:assessment|estimate)", 0.45),
        (r"repair\s*estimate", 0.45),
        (r"witness\s*(?:statement|information)", 0.40),
        (r"police\s*report\s*(?:number|attached)", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "claim",
        "loss",
        "damage",
        "incident",
        "settlement",
        "adjuster",
        "estimate",
        "repair",
        "payment",
        "reserve",
        "investigation",
        "proof",
    },
    filename_patterns={
        "claim": 0.75,
        "loss": 0.65,
        "incident": 0.60,
        "settlement": 0.60,
    },
    # Exclusions to prevent confusion with policy and EOB documents
    exclude_patterns={
        # Policy-specific patterns
        r"declarations?\s*page",
        r"policy\s*effective\s*date",
        r"annual\s*premium",
        r"coverage\s*limits",
        # EOB-specific patterns
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        r"patient\s*responsibility",
        r"provider\s*charges",
        # Medical coding
        r"diagnosis\s*code",
        r"procedure\s*code",
    },
    exclude_phrases={
        "policy declarations",
        "coverage summary",
    },
)

# Explanation of Benefits (EOB)
INSURANCE_EOB = SubthemeRule(
    name="insurance_eob",
    display_name="Explanation of Benefits",
    parent_theme="Financial",
    subtheme_category="Insurance",
    # Primary identifiers (high confidence, specific to EOBs)
    unique_patterns=[
        # Definitive EOB header
        (r"explanation\s*of\s*benefits", 0.95, "eob_header"),
        (r"this\s*is\s*not\s*a\s*bill", 0.92, "not_a_bill_notice"),
        # Core EOB financial fields
        (r"patient\s*responsibility", 0.90, "patient_responsibility"),
        (r"allowed\s*amount", 0.88, "allowed_amount"),
        (r"provider\s*charges?", 0.88, "provider_charges"),
        (r"plan\s*(?:paid|pays)", 0.86, "plan_payment"),
        (r"(?:co-?pay|copayment)", 0.85, "copay_amount"),
        (r"(?:co-?insurance|coinsurance)", 0.85, "coinsurance_amount"),
        # Medical service identifiers
        (r"service\s*date", 0.86, "service_date"),
        (r"provider\s*name", 0.85, "provider_name"),
    ],
    definitive_phrases={
        "explanation of benefits": 0.95,
        "this is not a bill": 0.92,
        "amount you owe": 0.88,
        "amount you may owe": 0.88,
        "insurance paid": 0.85,
        "plan discount": 0.82,
        "in-network provider": 0.80,
        "out-of-network provider": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"claim\s*(?:details|information)", 0.50),
        (r"member\s*(?:id|number)", 0.45),
        (r"group\s*(?:number|name)", 0.45),
        (r"deductible\s*(?:met|applied)", 0.45),
        (r"out[- ]of[- ]pocket\s*maximum", 0.40),
        (r"appeal\s*(?:rights|information)", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "eob",
        "benefits",
        "explanation",
        "patient",
        "provider",
        "allowed",
        "copay",
        "coinsurance",
        "deductible",
        "claim",
        "service",
        "charges",
        "responsibility",
    },
    filename_patterns={
        "eob": 0.80,
        "explanation": 0.70,
        "benefits": 0.65,
    },
    # Exclusions to prevent confusion with medical bills and other documents
    exclude_patterns={
        # Actual bills
        r"payment\s*due\s*date",
        r"minimum\s*payment",
        r"account\s*balance",
        r"pay\s*this\s*amount",
        # Policy documents
        r"policy\s*number",
        r"declarations?\s*page",
        r"annual\s*premium",
        # Claim forms
        r"date\s*of\s*loss",
        r"loss\s*description",
        r"settlement\s*amount",
    },
    exclude_phrases={
        "invoice",
        "statement balance",
        "amount due",
    },
)


INSURANCE_SUBTHEME_RULES: list[SubthemeRule] = [
    INSURANCE_POLICY,
    INSURANCE_CLAIM,
    INSURANCE_EOB,
]


INSURANCE_SUBTHEME_RULES_DICT = {rule.name: rule for rule in INSURANCE_SUBTHEME_RULES}
