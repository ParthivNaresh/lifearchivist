"""
Financial > Loan subtheme rules.

Defines precise, production-ready patterns for:
- Mortgage Statement
- Loan Agreement
- Student Loan

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# Mortgage Statement
MORTGAGE_STATEMENT = SubthemeRule(
    name="mortgage_statement",
    display_name="Mortgage Statement",
    parent_theme="Financial",
    subtheme_category="Loan",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core mortgage identifiers
        (r"mortgage\s*(?:statement|account)", 0.95, "mortgage_statement_header"),
        (r"loan\s*number\s*:?\s*[0-9\-]{5,}", 0.90, "loan_number_field"),
        (r"principal\s*and\s*interest", 0.90, "principal_interest"),
        (r"escrow\s*(?:account|balance|payment)", 0.88, "escrow_account"),
        # Payment breakdown patterns
        (r"principal\s*balance", 0.88, "principal_balance"),
        (r"interest\s*rate\s*:?\s*\d+\.?\d*\s*%", 0.87, "interest_rate"),
        (r"monthly\s*payment\s*(?:amount|due)", 0.86, "monthly_payment"),
        (r"payment\s*due\s*date", 0.86, "payment_due_date"),
        # Escrow components
        (r"property\s*tax(?:es)?", 0.85, "property_tax_escrow"),
        (r"(?:homeowner'?s?|hazard)\s*insurance", 0.85, "insurance_escrow"),
    ],
    definitive_phrases={
        "mortgage statement": 0.95,
        "home loan statement": 0.92,
        "mortgage account": 0.90,
        "principal and interest": 0.88,
        "escrow analysis": 0.88,
        "unpaid principal balance": 0.86,
        "maturity date": 0.85,
        "loan-to-value ratio": 0.82,
        "private mortgage insurance": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:pmi|mortgage\s*insurance)", 0.50),
        (r"late\s*(?:charge|fee|payment)", 0.45),
        (r"prepayment\s*(?:penalty|amount)", 0.45),
        (r"\b(?:arm|adjustable\s*rate)\b", 0.40),
        (r"(?:fixed|variable)\s*rate", 0.40),
        (r"amortization\s*schedule", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "mortgage",
        "loan",
        "principal",
        "interest",
        "escrow",
        "payment",
        "balance",
        "property",
        "insurance",
        "pmi",
        "amortization",
        "maturity",
        "apr",
    },
    filename_patterns={
        "mortgage": 0.80,
        "loan": 0.70,
        "statement": 0.65,
        "home": 0.60,
    },
    # Exclusions to prevent confusion with other loan and financial documents
    exclude_patterns={
        # Credit card patterns
        r"credit\s*(?:card|limit)",
        r"minimum\s*payment\s*due",
        r"cash\s*advance",
        r"balance\s*transfer",
        # Student loan specific
        r"(?:federal|private)\s*student\s*loan",
        r"(?:subsidized|unsubsidized)\s*loan",
        r"grace\s*period",
        r"deferment",
        # Auto loan specific
        r"(?:auto|vehicle|car)\s*loan",
        r"vehicle\s*identification\s*number",
        # Bank statements
        r"checking\s*account",
        r"savings\s*account",
        r"routing\s*number",
        # Property tax bills (not escrow)
        r"tax\s*parcel\s*number",
        r"assessed\s*value",
    },
    exclude_phrases={
        "credit card statement",
        "student loan",
        "auto loan",
        "personal loan",
    },
)

# Loan Agreement
LOAN_AGREEMENT = SubthemeRule(
    name="loan_agreement",
    display_name="Loan Agreement",
    parent_theme="Financial",
    subtheme_category="Loan",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core loan agreement identifiers
        (r"loan\s*agreement", 0.95, "loan_agreement_header"),
        (r"promissory\s*note", 0.92, "promissory_note"),
        (r"(?:borrower|lender)\s*(?:name|information)", 0.90, "party_information"),
        (r"loan\s*amount\s*:?\s*\$", 0.88, "loan_amount"),
        # Terms and conditions
        (r"(?:loan\s*)?terms\s*(?:and\s*conditions)?", 0.88, "loan_terms"),
        (r"(?:annual\s*percentage\s*rate|apr)", 0.87, "apr_field"),
        (r"repayment\s*(?:terms|schedule)", 0.86, "repayment_terms"),
        (r"(?:effective|closing)\s*date", 0.86, "effective_date"),
        # Legal language
        (r"(?:whereas|witnesseth|agreement\s*made)", 0.85, "legal_preamble"),
        (r"(?:default|breach)\s*(?:provisions?|clause)", 0.85, "default_provisions"),
    ],
    definitive_phrases={
        "loan agreement": 0.95,
        "promissory note": 0.92,
        "credit agreement": 0.90,
        "lending agreement": 0.88,
        "borrower agrees": 0.86,
        "lender agrees": 0.86,
        "truth in lending": 0.85,
        "finance charge": 0.82,
        "security interest": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"collateral\s*(?:description|security)", 0.50),
        (r"(?:personal\s*)?guarantee", 0.45),
        (r"(?:co-?borrower|co-?signer)", 0.45),
        (r"(?:origination|processing)\s*fee", 0.40),
        (r"(?:governing\s*law|jurisdiction)", 0.40),
        (r"(?:arbitration|dispute)\s*clause", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "loan",
        "agreement",
        "borrower",
        "lender",
        "promissory",
        "note",
        "terms",
        "apr",
        "repayment",
        "default",
        "collateral",
        "principal",
        "interest",
        "maturity",
    },
    filename_patterns={
        "loan": 0.75,
        "agreement": 0.75,
        "promissory": 0.70,
        "note": 0.65,
        "contract": 0.60,
    },
    # Exclusions to prevent confusion with statements and other documents
    exclude_patterns={
        # Mortgage-specific (separate from general loan)
        r"mortgage\s*(?:statement|account)",
        r"escrow\s*(?:account|analysis)",
        r"property\s*tax",
        # Credit card agreements
        r"credit\s*card\s*agreement",
        r"cardmember\s*agreement",
        r"credit\s*limit",
        # Lease agreements
        r"lease\s*agreement",
        r"rental\s*agreement",
        r"(?:landlord|tenant)",
        # Investment documents
        r"investment\s*agreement",
        r"subscription\s*agreement",
    },
    exclude_phrases={
        "mortgage statement",
        "credit card",
        "lease agreement",
        "rental agreement",
    },
)

# Student Loan
STUDENT_LOAN = SubthemeRule(
    name="student_loan",
    display_name="Student Loan",
    parent_theme="Financial",
    subtheme_category="Loan",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core student loan identifiers
        (
            r"student\s*(?:loan|aid)\s*(?:statement|account)",
            0.95,
            "student_loan_header",
        ),
        (r"(?:federal|private)\s*student\s*loan", 0.92, "loan_type"),
        (r"(?:subsidized|unsubsidized)\s*loan", 0.90, "subsidy_status"),
        (r"loan\s*servicer", 0.88, "loan_servicer"),
        # Student loan specific fields
        (r"(?:grace\s*period|in-?school\s*status)", 0.88, "grace_period"),
        (r"(?:deferment|forbearance)", 0.87, "deferment_forbearance"),
        (r"(?:enrollment\s*status|half-?time)", 0.86, "enrollment_status"),
        (r"(?:school|institution)\s*name", 0.86, "school_name"),
        # Repayment plans
        (r"(?:income[- ]driven|ibr|paye|repaye)", 0.85, "income_driven_plan"),
        (r"(?:standard|graduated|extended)\s*repayment", 0.85, "repayment_plan"),
    ],
    definitive_phrases={
        "student loan": 0.95,
        "education loan": 0.92,
        "stafford loan": 0.90,
        "plus loan": 0.90,
        "perkins loan": 0.88,
        "direct loan": 0.88,
        "loan forgiveness": 0.85,
        "public service loan forgiveness": 0.85,
        "consolidation loan": 0.82,
        "master promissory note": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:expected|actual)\s*graduation", 0.50),
        (r"academic\s*year", 0.45),
        (r"(?:entrance|exit)\s*counseling", 0.45),
        (r"capitalized\s*interest", 0.40),
        (r"(?:pell\s*grant|federal\s*aid)", 0.40),
        (r"(?:cosigner|endorser)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "student",
        "loan",
        "education",
        "federal",
        "subsidized",
        "unsubsidized",
        "deferment",
        "forbearance",
        "grace",
        "servicer",
        "repayment",
        "forgiveness",
        "consolidation",
        "stafford",
        "plus",
    },
    filename_patterns={
        "student": 0.80,
        "loan": 0.75,
        "education": 0.70,
        "federal": 0.65,
        "aid": 0.60,
    },
    # Exclusions to prevent confusion with other loan types and education documents
    exclude_patterns={
        # Mortgage loans
        r"mortgage\s*(?:statement|loan)",
        r"escrow\s*account",
        r"property\s*tax",
        # Auto loans
        r"(?:auto|vehicle|car)\s*loan",
        r"vehicle\s*identification",
        # Personal loans
        r"personal\s*loan",
        r"unsecured\s*loan",
        # Education savings (not loans)
        r"529\s*(?:plan|account)",
        r"coverdell\s*esa",
        r"education\s*savings",
        # Financial aid (grants, not loans)
        r"financial\s*aid\s*award",
        r"scholarship",
        r"grant\s*award",
        # Transcripts and enrollment
        r"(?:official|unofficial)\s*transcript",
        r"enrollment\s*verification",
    },
    exclude_phrases={
        "mortgage loan",
        "auto loan",
        "529 plan",
        "scholarship award",
        "grant award",
    },
)


LOAN_SUBTHEME_RULES: list[SubthemeRule] = [
    MORTGAGE_STATEMENT,
    LOAN_AGREEMENT,
    STUDENT_LOAN,
]


LOAN_SUBTHEME_RULES_DICT = {rule.name: rule for rule in LOAN_SUBTHEME_RULES}
