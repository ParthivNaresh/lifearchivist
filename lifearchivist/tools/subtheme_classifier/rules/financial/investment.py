"""
Financial > Investment subtheme rules.

Defines precise, production-ready patterns for:
- Brokerage Statement
- Trade Confirmation
- Investment Prospectus

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# Brokerage Statement
BROKERAGE_STATEMENT = SubthemeRule(
    name="brokerage_statement",
    display_name="Brokerage Statement",
    parent_theme="Financial",
    subtheme_category="Investment",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core brokerage statement sections
        (r"portfolio\s*(?:value|summary)", 0.92, "portfolio_value_section"),
        (r"account\s*(?:value|balance)\s*summary", 0.90, "account_value_summary"),
        (r"investment\s*(?:holdings|positions)", 0.90, "investment_holdings"),
        (r"market\s*value", 0.88, "market_value_field"),
        (r"unrealized\s*(?:gain|loss)", 0.88, "unrealized_gain_loss"),
        # Asset allocation and performance
        (r"asset\s*allocation", 0.87, "asset_allocation_section"),
        (
            r"(?:ytd|year[- ]to[- ]date)\s*(?:performance|return)",
            0.86,
            "ytd_performance",
        ),
        (r"cost\s*basis", 0.86, "cost_basis_field"),
        # Transaction summary patterns
        (r"(?:buy|sell)\s*transactions?", 0.85, "buy_sell_transactions"),
        (r"dividend\s*(?:income|reinvestment)", 0.85, "dividend_activity"),
    ],
    definitive_phrases={
        "brokerage statement": 0.95,
        "investment account statement": 0.92,
        "portfolio summary": 0.90,
        "holdings detail": 0.88,
        "securities held": 0.88,
        "total portfolio value": 0.86,
        "change in account value": 0.85,
        "income summary": 0.82,
        "capital gains distribution": 0.82,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:stocks?|equities)\s*holdings?", 0.50),
        (r"(?:bonds?|fixed\s*income)", 0.45),
        (r"mutual\s*funds?", 0.45),
        (r"etfs?|exchange[- ]traded\s*funds?", 0.45),
        (r"options?\s*(?:positions?|contracts?)", 0.40),
        (r"margin\s*(?:balance|requirement)", 0.40),
        (r"cash\s*(?:balance|sweep)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "brokerage",
        "portfolio",
        "holdings",
        "securities",
        "stocks",
        "bonds",
        "mutual",
        "etf",
        "dividend",
        "shares",
        "market",
        "value",
        "unrealized",
        "realized",
        "basis",
        "allocation",
        "investment",
    },
    filename_patterns={
        "brokerage": 0.75,
        "statement": 0.70,
        "portfolio": 0.70,
        "investment": 0.65,
        # Common brokerage firms
        "fidelity": 0.70,
        "schwab": 0.70,
        "vanguard": 0.70,
        "etrade": 0.70,
        "ameritrade": 0.70,
        "merrill": 0.65,
    },
    # Exclusions to prevent confusion with other financial documents
    exclude_patterns={
        # Bank statement patterns
        r"checking\s*account|savings\s*account",
        r"routing\s*(?:number|no\.?)",
        r"daily\s*ending\s*balance",
        # Credit card patterns
        r"payment\s*due\s*date",
        r"minimum\s*payment",
        r"credit\s*limit",
        # Retirement-specific (401k, IRA)
        r"401\s*\(?\s*k\s*\)?",
        r"\bira\b|individual\s*retirement",
        r"required\s*minimum\s*distribution",
        r"employer\s*(?:match|contribution)",
        # Trade confirmation specific
        r"trade\s*confirmation",
        r"execution\s*(?:time|price)",
        r"settlement\s*date",
        # Prospectus specific
        r"investment\s*objectives",
        r"risk\s*factors",
        r"fund\s*expenses",
    },
    exclude_phrases={
        "trade executed",
        "order confirmation",
    },
)

# Trade Confirmation
TRADE_CONFIRMATION = SubthemeRule(
    name="trade_confirmation",
    display_name="Trade Confirmation",
    parent_theme="Financial",
    subtheme_category="Investment",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core trade confirmation identifiers
        (r"trade\s*confirmation", 0.95, "trade_confirmation_header"),
        (r"(?:order|trade)\s*(?:number|id)", 0.92, "order_number"),
        (r"execution\s*(?:time|date)", 0.90, "execution_time"),
        (r"settlement\s*date", 0.90, "settlement_date"),
        (r"execution\s*price", 0.88, "execution_price"),
        # Transaction details
        (
            r"(?:bought|sold|buy|sell)\s*\d+\s*(?:shares?|units?)",
            0.88,
            "transaction_quantity",
        ),
        (r"(?:symbol|ticker)\s*:?\s*[A-Z]{1,5}", 0.86, "ticker_symbol"),
        (r"cusip\s*(?:number|no\.?)?:?\s*[A-Z0-9]{9}", 0.85, "cusip_number"),
        # Fees and commissions
        (r"(?:commission|brokerage\s*fee)", 0.86, "commission_fee"),
        (r"(?:total|net)\s*(?:amount|proceeds)", 0.85, "total_amount"),
    ],
    definitive_phrases={
        "trade confirmation": 0.95,
        "order confirmation": 0.92,
        "trade executed": 0.90,
        "your order has been executed": 0.88,
        "transaction details": 0.85,
        "as of trade date": 0.82,
        "settlement instructions": 0.80,
        "contra broker": 0.78,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"order\s*type\s*:?\s*(?:market|limit|stop)", 0.50),
        (r"(?:principal|agency)\s*(?:trade|transaction)", 0.45),
        (r"accrued\s*interest", 0.40),
        (r"regulatory\s*fee", 0.40),
        (r"sec\s*fee", 0.35),
        (r"clearing\s*(?:firm|broker)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "trade",
        "confirmation",
        "executed",
        "settlement",
        "execution",
        "bought",
        "sold",
        "shares",
        "symbol",
        "ticker",
        "cusip",
        "commission",
        "proceeds",
        "principal",
        "agency",
    },
    filename_patterns={
        "trade": 0.75,
        "confirmation": 0.75,
        "confirm": 0.70,
        "execution": 0.65,
        "transaction": 0.60,
    },
    # Exclusions to prevent confusion with statements and other documents
    exclude_patterns={
        # Brokerage statement patterns
        r"portfolio\s*(?:value|summary)",
        r"account\s*(?:value|balance)\s*summary",
        r"asset\s*allocation",
        r"holdings?\s*detail",
        r"year[- ]to[- ]date\s*performance",
        # Bank/credit patterns
        r"checking\s*account|savings\s*account",
        r"credit\s*limit",
        r"payment\s*due",
        # Prospectus patterns
        r"investment\s*objectives",
        r"risk\s*factors",
        r"fund\s*performance",
        # Tax documents
        r"form\s*1099",
        r"tax\s*withholding",
    },
    exclude_phrases={
        "account statement",
        "monthly statement",
        "portfolio summary",
    },
)

# Investment Prospectus
PROSPECTUS = SubthemeRule(
    name="prospectus",
    display_name="Investment Prospectus",
    parent_theme="Financial",
    subtheme_category="Investment",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core prospectus identifiers
        (r"prospectus", 0.95, "prospectus_header"),
        (r"investment\s*objectives?", 0.92, "investment_objectives"),
        (r"(?:principal\s*)?risk\s*factors?", 0.90, "risk_factors"),
        (r"fund\s*(?:fees|expenses)", 0.90, "fund_expenses"),
        (r"expense\s*ratio", 0.88, "expense_ratio"),
        # Fund-specific patterns
        (r"(?:mutual\s*)?fund\s*performance", 0.87, "fund_performance"),
        (r"portfolio\s*(?:manager|management)", 0.86, "portfolio_management"),
        (r"investment\s*(?:strategy|strategies)", 0.86, "investment_strategy"),
        # Regulatory and compliance
        (r"(?:summary|statutory)\s*prospectus", 0.88, "prospectus_type"),
        (r"shareholder\s*(?:fees|information)", 0.85, "shareholder_info"),
    ],
    definitive_phrases={
        "prospectus": 0.95,
        "summary prospectus": 0.92,
        "fund facts": 0.88,
        "investment company": 0.85,
        "before you invest": 0.85,
        "investment policies": 0.82,
        "principal investment strategies": 0.82,
        "portfolio turnover": 0.80,
        "tax consequences": 0.78,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:sales\s*)?loads?\s*and\s*fees", 0.50),
        (r"redemption\s*(?:fees?|procedures?)", 0.45),
        (r"distribution\s*(?:arrangements|fees)", 0.45),
        (r"share\s*classes?", 0.45),
        (r"minimum\s*investment", 0.40),
        (r"dividend\s*policy", 0.40),
        (r"benchmark\s*(?:index|comparison)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "prospectus",
        "fund",
        "investment",
        "objectives",
        "risk",
        "expenses",
        "fees",
        "performance",
        "portfolio",
        "strategy",
        "management",
        "shareholder",
        "distribution",
        "redemption",
        "turnover",
        "benchmark",
    },
    filename_patterns={
        "prospectus": 0.80,
        "fund": 0.65,
        "summary": 0.60,
    },
    # Exclusions to prevent confusion with statements and confirmations
    exclude_patterns={
        # Statement patterns
        r"account\s*(?:number|balance)",
        r"statement\s*period",
        r"beginning\s*balance.*?ending\s*balance",
        r"unrealized\s*(?:gain|loss)",
        # Trade confirmation patterns
        r"trade\s*confirmation",
        r"execution\s*(?:time|price)",
        r"settlement\s*date",
        r"(?:bought|sold)\s*\d+\s*shares",
        # Account-specific patterns
        r"your\s*account",
        r"account\s*activity",
        r"transaction\s*history",
        # Tax documents
        r"form\s*1099",
        r"tax\s*statement",
    },
    exclude_phrases={
        "account statement",
        "trade executed",
        "order confirmation",
        "transaction details",
    },
)


INVESTMENT_SUBTHEME_RULES: list[SubthemeRule] = [
    BROKERAGE_STATEMENT,
    TRADE_CONFIRMATION,
    PROSPECTUS,
]


INVESTMENT_SUBTHEME_RULES_DICT = {rule.name: rule for rule in INVESTMENT_SUBTHEME_RULES}
