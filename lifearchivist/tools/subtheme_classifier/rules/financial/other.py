"""
Financial > Other subtheme rules.

Defines precise, production-ready patterns for:
- Pay Stub
- Invoice

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# Pay Stub
PAY_STUB = SubthemeRule(
    name="pay_stub",
    display_name="Pay Stub",
    parent_theme="Financial",
    subtheme_category="Other",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core pay stub identifiers
        (
            r"(?:pay\s*stub|paycheck\s*stub|earnings\s*statement)",
            0.95,
            "pay_stub_header",
        ),
        (r"pay\s*period\s*:?\s*\d{1,2}[/-]\d{1,2}", 0.92, "pay_period"),
        (r"(?:gross\s*pay|gross\s*earnings)", 0.90, "gross_pay"),
        (r"net\s*pay", 0.90, "net_pay"),
        # Earnings and deductions sections
        (r"(?:regular\s*)?(?:hours|hrs)\s*worked", 0.88, "hours_worked"),
        (r"(?:hourly\s*)rate\s*:?\s*\$?\d+", 0.87, "hourly_rate"),
        (r"year[- ]to[- ]date\s*(?:earnings|ytd)", 0.86, "ytd_earnings"),
        (r"(?:federal|state)\s*(?:tax|withholding)", 0.86, "tax_withholding"),
        # Employee information
        (r"employee\s*(?:id|number)", 0.85, "employee_id"),
        (r"(?:social\s*security|fica)", 0.85, "social_security_deduction"),
    ],
    definitive_phrases={
        "pay stub": 0.95,
        "earnings statement": 0.92,
        "paycheck stub": 0.90,
        "gross pay": 0.88,
        "net pay": 0.88,
        "current earnings": 0.85,
        "deductions": 0.85,
        "employer contributions": 0.82,
        "direct deposit": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:overtime|ot)\s*(?:hours|pay)", 0.50),
        (r"(?:vacation|sick|pto)\s*(?:hours|time)", 0.45),
        (r"(?:medicare|medical)\s*(?:deduction|withholding)", 0.45),
        (r"(?:401k|retirement)\s*(?:contribution|deduction)", 0.40),
        (r"(?:health|dental|vision)\s*insurance", 0.40),
        (r"(?:bonus|commission)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "pay",
        "stub",
        "paycheck",
        "earnings",
        "gross",
        "net",
        "deductions",
        "withholding",
        "hours",
        "rate",
        "ytd",
        "fica",
        "medicare",
        "salary",
        "wages",
    },
    filename_patterns={
        "paystub": 0.80,
        "pay_stub": 0.80,
        "paycheck": 0.75,
        "earnings": 0.70,
        "payroll": 0.65,
    },
    # Exclusions to prevent confusion with other financial documents
    exclude_patterns={
        # W-2 forms (annual, not per pay period)
        r"form\s*w-?2",
        r"wage\s*and\s*tax\s*statement",
        r"box\s*\d+\s*[:\-]?\s*wages",
        # 1099 forms
        r"form\s*1099",
        r"nonemployee\s*compensation",
        # Bank statements
        r"account\s*balance",
        r"beginning\s*balance.*?ending\s*balance",
        # Invoices
        r"invoice\s*(?:number|#)",
        r"payment\s*due",
        r"bill\s*to",
    },
    exclude_phrases={
        "form w-2",
        "tax return",
        "invoice",
        "bank statement",
    },
)

# Invoice
INVOICE = SubthemeRule(
    name="invoice",
    display_name="Invoice",
    parent_theme="Financial",
    subtheme_category="Other",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core invoice identifiers
        (r"invoice\s*(?:number|#|no\.?)?:?\s*[A-Z0-9\-]+", 0.95, "invoice_number"),
        (r"(?:bill\s*to|billing\s*address)", 0.90, "bill_to"),
        (r"(?:invoice\s*)?date\s*:?\s*\d{1,2}[/-]\d{1,2}", 0.88, "invoice_date"),
        (r"(?:payment\s*)?due\s*(?:date|on)", 0.88, "payment_due"),
        # Line items and totals
        (r"(?:quantity|qty)\s*(?:x\s*)?(?:unit\s*)?price", 0.87, "quantity_price"),
        (r"(?:sub-?total|subtotal)", 0.86, "subtotal"),
        (r"(?:total\s*)?amount\s*due", 0.86, "amount_due"),
        (r"(?:item\s*)?description", 0.85, "item_description"),
        # Tax and payment terms
        (r"(?:sales\s*)?tax\s*:?\s*\$?\d+", 0.85, "sales_tax"),
        (r"(?:payment\s*)?terms\s*:?\s*(?:net\s*\d+|due\s*on)", 0.85, "payment_terms"),
    ],
    definitive_phrases={
        "invoice": 0.95,
        "bill to": 0.90,
        "remit payment": 0.88,
        "amount due": 0.88,
        "payment terms": 0.85,
        "net 30": 0.85,
        "due upon receipt": 0.82,
        "past due": 0.80,
        "remittance advice": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:ship\s*to|shipping\s*address)", 0.50),
        (r"(?:p\.?o\.?\s*(?:box|number)|purchase\s*order)", 0.45),
        (r"(?:discount|credit)", 0.45),
        (r"(?:shipping|handling)\s*(?:fee|charge)", 0.40),
        (r"(?:service\s*)?charge", 0.40),
        (r"(?:account\s*)?number", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "invoice",
        "bill",
        "billing",
        "payment",
        "due",
        "amount",
        "total",
        "subtotal",
        "tax",
        "quantity",
        "price",
        "description",
        "terms",
        "remit",
    },
    filename_patterns={
        "invoice": 0.85,
        "inv": 0.70,
        "bill": 0.65,
        "billing": 0.60,
    },
    # Exclusions to prevent confusion with other financial documents
    exclude_patterns={
        # Receipts (already paid)
        r"(?:payment\s*)?received",
        r"thank\s*you\s*for\s*your\s*(?:payment|purchase)",
        r"transaction\s*complete",
        # Statements (multiple transactions)
        r"statement\s*period",
        r"beginning\s*balance",
        r"account\s*summary",
        # Estimates/quotes (not final)
        r"(?:quote|estimate|proposal)",
        r"(?:valid\s*until|quote\s*expires)",
        # Pay stubs
        r"pay\s*stub",
        r"gross\s*pay",
        r"net\s*pay",
    },
    exclude_phrases={
        "bank statement",
        "credit card statement",
        "estimate",
    },
)


OTHER_FINANCIAL_SUBTHEME_RULES: list[SubthemeRule] = [
    PAY_STUB,
    INVOICE,
]


OTHER_FINANCIAL_SUBTHEME_RULES_DICT = {
    rule.name: rule for rule in OTHER_FINANCIAL_SUBTHEME_RULES
}
