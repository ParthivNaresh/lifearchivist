PRIMARY_UNIQUE_PATTERN_DEFINITIONS = [
    # Financial - Tax
    ("Financial", 0.95, "tax_1040", r"\bform\s+1040\b"),
    ("Financial", 0.95, "tax_w2", r"\b(?:form\s+)?w-?2\s+wage"),
    ("Financial", 0.95, "tax_1099", r"\bform\s+1099"),
    (
        "Financial",
        0.90,
        "tax_return",
        r"(?:federal|state)\s+(?:income\s+)?tax\s+return",
    ),
    # Financial - Other
    (
        "Financial",
        0.90,
        "bank_statement",
        r"(?:checking|savings)\s+account\s+statement",
    ),
    ("Financial", 0.85, "credit_card", r"credit\s+card\s+(?:statement|account)"),
    ("Financial", 0.90, "mortgage", r"mortgage\s+(?:statement|payment)"),
    (
        "Financial",
        0.85,
        "investment",
        r"(?:investment|brokerage)\s+(?:account\s+)?statement",
    ),
    # Healthcare
    ("Healthcare", 0.95, "eob", r"explanation\s+of\s+benefits"),
    ("Healthcare", 0.90, "prescription", r"\brx\s+(?:number|#):\s*\d+"),
    ("Healthcare", 0.90, "lab_results", r"(?:lab|laboratory)\s+results"),
    ("Healthcare", 0.85, "medical_record", r"medical\s+record\s+(?:number|#)"),
    # Legal
    ("Legal", 0.95, "lease", r"(?:residential|commercial)\s+lease\s+agreement"),
    (
        "Legal",
        0.90,
        "contract",
        r"(?:this\s+)?(?:agreement|contract)\s+(?:is\s+)?(?:entered|made)\s+(?:into\s+)?(?:by\s+and\s+)?between",
    ),
    ("Legal", 0.95, "will", r"last\s+will\s+and\s+testament"),
    ("Legal", 0.90, "power_attorney", r"power\s+of\s+attorney"),
    # Professional
    ("Professional", 0.95, "resume", r"(?:curriculum\s+vitae|resume|cv)\b"),
    ("Professional", 0.90, "transcript", r"(?:official\s+)?(?:academic\s+)?transcript"),
    (
        "Professional",
        0.85,
        "certification",
        r"(?:certificate|certification)\s+of\s+(?:completion|achievement)",
    ),
]


PRIMARY_DEFINITIVE_PHRASE_DEFINITIONS = {
    "Financial": [
        ("annual percentage rate", 0.85),
        ("account statement", 0.80),
        ("investment portfolio", 0.85),
        ("tax return", 0.90),
        ("invoice number", 0.85),
        ("payment due", 0.75),
    ],
    "Healthcare": [
        ("medical record", 0.85),
        ("patient information", 0.80),
        ("prescription medication", 0.85),
        ("insurance claim", 0.75),
        ("diagnosis code", 0.85),
    ],
    "Legal": [
        ("law firm", 0.90),
        ("power of attorney", 0.90),
        ("last will and testament", 0.95),
        ("court order", 0.85),
        ("legal agreement", 0.80),
        ("terms and conditions", 0.75),
    ],
    "Professional": [
        ("curriculum vitae", 0.90),
        ("letter of recommendation", 0.85),
        ("performance review", 0.80),
        ("job description", 0.75),
    ],
}
