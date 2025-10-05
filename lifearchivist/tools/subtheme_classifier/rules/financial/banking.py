"""
Financial > Banking subtheme rules.

Defines precise, production-ready patterns for:
- Bank Statement
- Credit Card Statement
- Wire Transfer

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# Bank Statement
BANK_STATEMENT = SubthemeRule(
    name="bank_statement",
    display_name="Bank Statement",
    parent_theme="Financial",
    subtheme_category="Banking",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core statement sections
        (
            r"beginning\s*balance.*?ending\s*balance",
            0.92,
            "beginning_ending_balance_span",
        ),
        (
            r"(?:deposits\s*and\s*credits|credits\s*and\s*deposits)",
            0.90,
            "deposits_credits_section",
        ),
        (
            r"(?:withdrawals\s*and\s*debits|debits\s*and\s*withdrawals)",
            0.90,
            "withdrawals_debits_section",
        ),
        # Key account identifiers commonly shown on bank statements
        (r"routing\s*(?:number|no\.?):?\s*[0-9*\-]{5,}", 0.88, "routing_number_field"),
        (r"account\s*(?:number|no\.?):?\s*[0-9*\-]{5,}", 0.88, "account_number_field"),
        # Additional strong indicators
        (r"daily\s*ending\s*balance", 0.87, "daily_ending_balance"),
        (r"statement\s*period\s*:?\s*", 0.86, "statement_period"),
        (r"available\s*balance", 0.86, "available_balance_field"),
    ],
    definitive_phrases={
        "checking account statement": 0.95,
        "savings account statement": 0.95,
        "account summary": 0.85,
        "total deposits": 0.85,
        "total withdrawals": 0.85,
        "electronic deposits and withdrawals": 0.85,
        "ach credits": 0.80,
        "ach debits": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"account\s*summary", 0.50),
        (r"interest\s*paid\s*this\s*period", 0.40),
        (r"check\s*image", 0.40),
        (r"non[- ]sufficient\s*funds|overdraft\s*\(nsf\)", 0.30),
        (r"service\s*charge|monthly\s*maintenance\s*fee", 0.30),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "checking",
        "savings",
        "deposit",
        "withdrawal",
        "debit",
        "credit",
        "ach",
        "atm",
        "pos",
        "interest",
        "service",
        "charge",
        "nsf",
        "overdraft",
        "balance",
        "statement",
        "account",
        "routing",
    },
    filename_patterns={
        "checking": 0.70,
        "savings": 0.70,
        "bank": 0.60,
        "statement": 0.60,
        "stmt": 0.55,
    },
    # Exclusions to prevent confusion with other financial subthemes
    exclude_patterns={
        # Credit card-specific
        r"payment\s*due\s*date",
        r"minimum\s*payment",
        r"\bapr\b",
        r"credit\s*limit",
        r"balance\s*transfer",
        r"cash\s*advance",
        # Mortgage/loan-specific
        r"mortgage\s*statement",
        r"escrow",
        r"loan\s*number",
        # Brokerage-specific
        r"brokerage|trade\s*confirmation|prospectus|capital\s*gains",
        # Property tax
        r"property\s*tax",
    },
    exclude_phrases={
        "late payment warning",
    },
)

# Credit Card Statement
CREDIT_CARD_STATEMENT = SubthemeRule(
    name="credit_card_statement",
    display_name="Credit Card Statement",
    parent_theme="Financial",
    subtheme_category="Banking",
    # Primary identifiers (high confidence, specific to credit cards)
    unique_patterns=[
        (r"payment\s*due\s*date", 0.95, "payment_due_date"),
        (r"minimum\s*payment(?:\s*due)?", 0.95, "minimum_payment"),
        (r"statement\s*closing\s*date", 0.90, "closing_date"),
        (r"new\s*balance", 0.88, "new_balance"),
        (r"available\s*credit", 0.88, "available_credit"),
        (r"credit\s*limit", 0.92, "credit_limit"),
        (r"(?:purchase|purchases)\s*apr", 0.90, "purchase_apr"),
        (r"cash\s*advance\s*apr", 0.90, "cash_advance_apr"),
        (r"balance\s*transfer\s*apr", 0.90, "balance_transfer_apr"),
        # Masked card number patterns common on statements
        (
            r"(?:card|account)\s*(?:number|no\.?):?\s*(?:\*{4}|x{2,4}|•{4}|\u2022{4})[\s-]*\d{4}",
            0.88,
            "masked_card_number",
        ),
        # Regulatory/compliance warning specific to cards
        (r"late\s*payment\s*warning", 0.92, "late_payment_warning"),
    ],
    definitive_phrases={
        "statement balance": 0.88,
        "late payment warning": 0.92,
        "interest charge": 0.85,
        "fees charged": 0.82,
        "rewards summary": 0.78,
        "cash advance fee": 0.80,
    },
    # Secondary identifiers (weighted sections)
    structure_patterns=[
        (r"interest\s*charge[s]?", 0.55),
        (r"fees\s*charged", 0.50),
        (r"rewards?\s*summary", 0.45),
        (r"transactions?\s*summary", 0.45),
        (r"previous\s*balance", 0.40),
        (r"payments?\s*received", 0.40),
        (r"credits?\s*posted", 0.35),
        (r"cash\s*advance[s]?", 0.35),
        (r"balance\s*transfer[s]?", 0.35),
    ],
    # Tertiary indicators
    keywords={
        "apr",
        "credit",
        "limit",
        "available",
        "payment",
        "due",
        "minimum",
        "statement",
        "balance",
        "transaction",
        "merchant",
        "purchase",
        "cash",
        "advance",
        "transfer",
        "interest",
        "fee",
        "rewards",
        "points",
        "closing",
    },
    filename_patterns={
        "credit": 0.75,
        "card": 0.75,
        "statement": 0.60,
        # Common issuer hints
        "amex": 0.75,
        "americanexpress": 0.75,
        "visa": 0.70,
        "mastercard": 0.70,
        "discover": 0.70,
        "chase": 0.70,
        "citi": 0.70,
        "capitalone": 0.70,
        "boa": 0.65,
        "bankofamerica": 0.65,
    },
    # Exclusions to prevent overlap with bank statements, loans, brokerage, taxes, healthcare
    exclude_patterns={
        # Bank statement patterns
        r"routing\s*(?:number|no\.?):",
        r"ach\s*(?:credits|debits)",
        r"daily\s*ending\s*balance",
        r"beginning\s*balance.*?ending\s*balance",
        r"checking\s*account|savings\s*account",
        # Mortgage/loan
        r"mortgage\s*statement|escrow|loan\s*number",
        # Brokerage/investment
        r"brokerage|trade\s*confirmation|prospectus|capital\s*gains|dividend\s*reinvestment",
        # Retirement
        r"401\s*\(?\s*k\s*\)?|\bira\b|required\s*minimum\s*distribution",
        # Taxes
        r"form\s*10\d{2}|form\s*w-?2|form\s*1040|property\s*tax",
        # Healthcare (avoid EOB mislabel)
        r"explanation\s*of\s*benefits|patient\s*name|diagnosis\s*code",
    },
    exclude_phrases={
        "routing number:",
        "account number:",
        "non-sufficient funds",
        "overdraft",
    },
)


BANKING_SUBTHEME_RULES: list[SubthemeRule] = [
    BANK_STATEMENT,
    CREDIT_CARD_STATEMENT,
]

BANKING_SUBTHEME_RULES_DICT = {rule.name: rule for rule in BANKING_SUBTHEME_RULES}
