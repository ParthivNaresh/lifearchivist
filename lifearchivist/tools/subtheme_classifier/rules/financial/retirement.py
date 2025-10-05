"""
Financial > Retirement subtheme rules.

Defines precise, production-ready patterns for:
- 401(k) Statement
- IRA Statement
- Pension Statement
- Social Security Statement
- 529 Education Savings Plan

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# 401(k) Statement
RETIREMENT_401K = SubthemeRule(
    name="retirement_401k",
    display_name="401(k) Statement",
    parent_theme="Financial",
    subtheme_category="Retirement",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core 401(k) identifiers
        (
            r"401\s*\(?\s*k\s*\)?(?:\s*(?:plan|account|statement))?",
            0.85,
            "401k_identifier",
        ),
        (r"employer\s*(?:match|matching|contribution)", 0.85, "employer_match"),
        (r"participant\s*(?:name|id|number)", 0.88, "participant_info"),
        # Contribution patterns
        (
            r"(?:employee|participant)\s*(?:contribution|deferral)",
            0.88,
            "employee_contribution",
        ),
        (r"(?:pre-?tax|roth)\s*contribution", 0.87, "contribution_type"),
        (r"contribution\s*(?:rate|percentage)", 0.86, "contribution_rate"),
        # Investment and allocation
        (r"investment\s*(?:elections?|options?|lineup)", 0.86, "investment_elections"),
        (r"fund\s*allocation", 0.85, "fund_allocation"),
        (r"loan\s*(?:balance|repayment)", 0.85, "401k_loan"),
    ],
    definitive_phrases={
        "401(k) plan": 0.95,
        "401k account": 0.95,
        "retirement savings plan": 0.88,
        "employer sponsored retirement": 0.88,
        "vesting schedule": 0.86,
        "employer match": 0.86,
        "salary deferral": 0.85,
        "catch-up contribution": 0.82,
        "safe harbor": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"vesting\s*schedule", 0.50),
        (r"beneficiary\s*(?:designation|information)", 0.45),
        (r"rollover\s*(?:options?|information)", 0.45),
        (r"hardship\s*withdrawal", 0.40),
        (r"in-?service\s*withdrawal", 0.40),
        (r"profit\s*sharing", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "401k",
        "retirement",
        "employer",
        "match",
        "vested",
        "vesting",
        "contribution",
        "deferral",
        "participant",
        "rollover",
        "beneficiary",
        "pretax",
        "roth",
        "allocation",
    },
    filename_patterns={
        "401k": 0.80,
        "401": 0.70,
        "retirement": 0.65,
        "participant": 0.60,
    },
    # Exclusions to prevent confusion with other retirement and investment documents
    exclude_patterns={
        # IRA-specific patterns
        r"individual\s*retirement\s*(?:account|arrangement)",
        r"traditional\s*ira",
        r"roth\s*ira",
        r"sep[- ]ira",
        r"simple\s*ira",
        # Pension-specific
        r"defined\s*benefit\s*plan",
        r"pension\s*benefit",
        r"monthly\s*pension",
        # Social Security
        r"social\s*security\s*(?:administration|statement)",
        r"ssa\s*statement",
        # General brokerage
        r"brokerage\s*statement",
        r"trade\s*confirmation",
    },
    exclude_phrases={
        "ira account",
        "pension plan",
        "social security benefits",
    },
)

# IRA Statement
RETIREMENT_IRA = SubthemeRule(
    name="retirement_ira",
    display_name="IRA Statement",
    parent_theme="Financial",
    subtheme_category="Retirement",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core IRA identifiers
        (
            r"(?:individual\s*retirement\s*(?:account|arrangement)|\bira\b)",
            0.95,
            "ira_identifier",
        ),
        (r"(?:traditional|roth|sep|simple)\s*ira", 0.92, "ira_type"),
        (r"required\s*minimum\s*distribution|rmd", 0.90, "rmd_field"),
        (r"ira\s*(?:account|statement)", 0.88, "ira_account"),
        # Contribution and distribution patterns
        (r"ira\s*contribution", 0.88, "ira_contribution"),
        (r"(?:qualified|non-?qualified)\s*distribution", 0.87, "distribution_type"),
        (r"rollover\s*(?:contribution|ira)", 0.86, "rollover_ira"),
        # Tax-related IRA patterns
        (r"tax[- ](?:deferred|deductible)\s*contribution", 0.86, "tax_treatment"),
        (r"conversion\s*(?:to|from)\s*roth", 0.85, "roth_conversion"),
        (r"early\s*withdrawal\s*penalty", 0.85, "early_withdrawal"),
    ],
    definitive_phrases={
        "individual retirement account": 0.95,
        "ira statement": 0.92,
        "traditional ira": 0.90,
        "roth ira": 0.90,
        "sep-ira": 0.88,
        "simple ira": 0.88,
        "ira rollover": 0.85,
        "backdoor roth": 0.82,
        "ira custodian": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"custodian\s*(?:name|information)", 0.50),
        (r"fair\s*market\s*value", 0.45),
        (r"contribution\s*limit", 0.45),
        (r"catch[- ]up\s*contribution", 0.40),
        (r"recharacterization", 0.40),
        (r"inherited\s*ira", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "ira",
        "individual",
        "retirement",
        "traditional",
        "roth",
        "sep",
        "simple",
        "rmd",
        "distribution",
        "rollover",
        "conversion",
        "custodian",
        "contribution",
        "withdrawal",
    },
    filename_patterns={
        "ira": 0.80,
        "roth": 0.70,
        "traditional": 0.65,
        "retirement": 0.60,
    },
    # Exclusions to prevent confusion with 401(k) and other documents
    exclude_patterns={
        # 401(k)-specific patterns
        r"401\s*\(?\s*k\s*\)?",
        r"employer\s*(?:match|contribution)",
        r"participant\s*(?:id|number)",
        r"salary\s*deferral",
        # Pension-specific
        r"defined\s*benefit",
        r"pension\s*(?:benefit|payment)",
        r"annuity\s*payment",
        # Social Security
        r"social\s*security",
        r"ssa\s*statement",
        # General investment
        r"brokerage\s*account",
        r"trade\s*confirmation",
    },
    exclude_phrases={
        "401k plan",
        "employer sponsored",
        "pension statement",
    },
)

# Pension Statement
PENSION_STATEMENT = SubthemeRule(
    name="pension_statement",
    display_name="Pension Statement",
    parent_theme="Financial",
    subtheme_category="Retirement",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core pension identifiers
        (r"pension\s*(?:statement|benefit|plan)", 0.92, "pension_identifier"),
        (r"defined\s*benefit\s*(?:plan|pension)", 0.90, "defined_benefit"),
        (
            r"(?:monthly|annual)\s*pension\s*(?:benefit|payment)",
            0.90,
            "pension_payment",
        ),
        (r"years?\s*of\s*(?:service|credit)", 0.88, "service_years"),
        # Benefit calculation patterns
        (r"(?:accrued|earned)\s*benefit", 0.88, "accrued_benefit"),
        (r"benefit\s*(?:formula|calculation)", 0.87, "benefit_formula"),
        (r"final\s*average\s*(?:salary|compensation)", 0.86, "final_average_salary"),
        # Retirement and survivor benefits
        (r"(?:normal|early)\s*retirement\s*(?:date|age)", 0.86, "retirement_date"),
        (r"survivor\s*benefit", 0.85, "survivor_benefit"),
        (r"joint\s*and\s*survivor", 0.85, "joint_survivor"),
    ],
    definitive_phrases={
        "pension statement": 0.95,
        "pension benefit": 0.92,
        "defined benefit plan": 0.90,
        "retirement pension": 0.88,
        "pension plan statement": 0.88,
        "vested pension": 0.85,
        "pension annuity": 0.85,
        "lump sum option": 0.82,
        "cost of living adjustment": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"actuarial\s*(?:value|equivalent)", 0.50),
        (r"cola|cost[- ]of[- ]living", 0.45),
        (r"disability\s*(?:benefit|pension)", 0.45),
        (r"deferred\s*(?:pension|retirement)", 0.40),
        (r"pension\s*(?:freeze|termination)", 0.40),
        (r"pbgc|pension\s*benefit\s*guaranty", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "pension",
        "defined",
        "benefit",
        "annuity",
        "retirement",
        "service",
        "accrued",
        "vested",
        "survivor",
        "monthly",
        "cola",
        "actuarial",
        "pbgc",
    },
    filename_patterns={
        "pension": 0.80,
        "benefit": 0.65,
        "retirement": 0.60,
        "annuity": 0.60,
    },
    # Exclusions to prevent confusion with 401(k), IRA, and Social Security
    exclude_patterns={
        # 401(k)-specific
        r"401\s*\(?\s*k\s*\)?",
        r"employer\s*match",
        r"salary\s*deferral",
        r"investment\s*elections",
        # IRA-specific
        r"individual\s*retirement",
        r"\bira\b",
        r"roth\s*(?:ira|conversion)",
        r"required\s*minimum\s*distribution",
        # Social Security
        r"social\s*security",
        r"ssa\s*statement",
        r"medicare",
        # Investment accounts
        r"brokerage\s*statement",
        r"portfolio\s*value",
    },
    exclude_phrases={
        "401k account",
        "ira account",
        "social security administration",
    },
)

# Social Security Statement
SOCIAL_SECURITY = SubthemeRule(
    name="social_security",
    display_name="Social Security Statement",
    parent_theme="Financial",
    subtheme_category="Retirement",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core Social Security identifiers
        (
            r"social\s*security\s*(?:statement|administration)",
            0.95,
            "social_security_header",
        ),
        (r"ssa\s*statement", 0.92, "ssa_statement"),
        (
            r"(?:estimated\s*)?(?:retirement|disability|survivor)\s*benefits?",
            0.90,
            "benefit_types",
        ),
        (r"earnings\s*record", 0.88, "earnings_record"),
        # Benefit calculation patterns
        (r"full\s*retirement\s*age", 0.88, "full_retirement_age"),
        (r"primary\s*insurance\s*amount", 0.87, "primary_insurance_amount"),
        (r"(?:taxed\s*)?social\s*security\s*earnings", 0.86, "ss_earnings"),
        # Medicare-related patterns
        (r"medicare\s*(?:part\s*[a-d]|coverage)", 0.86, "medicare_info"),
        (r"quarters?\s*of\s*coverage", 0.85, "quarters_coverage"),
        (r"work\s*credits?", 0.85, "work_credits"),
    ],
    definitive_phrases={
        "social security statement": 0.95,
        "your social security statement": 0.92,
        "ssa.gov": 0.90,
        "social security administration": 0.90,
        "retirement benefits estimate": 0.88,
        "disability benefits": 0.85,
        "survivor benefits": 0.85,
        "medicare benefits": 0.82,
        "delayed retirement credits": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:early|delayed)\s*retirement", 0.50),
        (r"spousal\s*benefits?", 0.45),
        (r"windfall\s*elimination", 0.45),
        (r"government\s*pension\s*offset", 0.40),
        (r"cola\s*adjustment", 0.40),
        (r"taxable\s*benefits", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "social",
        "security",
        "ssa",
        "medicare",
        "retirement",
        "disability",
        "survivor",
        "earnings",
        "credits",
        "quarters",
        "benefits",
        "cola",
    },
    filename_patterns={
        "social": 0.75,
        "security": 0.75,
        "ssa": 0.80,
        "statement": 0.60,
    },
    # Exclusions to prevent confusion with other retirement documents
    exclude_patterns={
        # 401(k)-specific
        r"401\s*\(?\s*k\s*\)?",
        r"employer\s*(?:match|contribution)",
        r"investment\s*(?:options|elections)",
        # IRA-specific
        r"individual\s*retirement",
        r"\bira\b",
        r"custodian",
        r"rollover\s*contribution",
        # Pension-specific
        r"defined\s*benefit",
        r"pension\s*(?:plan|benefit)",
        r"years\s*of\s*service",
        # Investment/brokerage
        r"portfolio\s*value",
        r"investment\s*holdings",
        r"brokerage\s*account",
    },
    exclude_phrases={
        "401k plan",
        "ira statement",
        "pension statement",
        "investment account",
    },
)

# 529 Education Savings Plan
EDUCATION_529 = SubthemeRule(
    name="education_529",
    display_name="529 Education Savings Plan",
    parent_theme="Financial",
    subtheme_category="Retirement",  # Often grouped with retirement due to tax-advantaged nature
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core 529 identifiers
        (r"529\s*(?:plan|account|statement)", 0.95, "529_identifier"),
        (
            r"(?:qualified\s*)?(?:tuition|education)\s*(?:program|plan)",
            0.92,
            "education_plan",
        ),
        (r"education\s*savings\s*(?:plan|account)", 0.90, "education_savings"),
        (r"coverdell\s*(?:esa|education)", 0.88, "coverdell_esa"),
        # Beneficiary and contribution patterns
        (r"(?:account\s*)?beneficiary", 0.88, "beneficiary_field"),
        (
            r"qualified\s*(?:education|higher\s*education)\s*expense",
            0.87,
            "qualified_expenses",
        ),
        (r"(?:k-12|elementary|secondary)\s*tuition", 0.86, "k12_tuition"),
        # Tax and distribution patterns
        (r"tax[- ]free\s*(?:withdrawal|distribution)", 0.86, "tax_free_distribution"),
        (r"(?:state\s*)?tax\s*(?:deduction|credit)", 0.85, "tax_benefit"),
        (r"rollover\s*to\s*(?:another\s*)?529", 0.85, "529_rollover"),
    ],
    definitive_phrases={
        "529 plan": 0.95,
        "529 account": 0.95,
        "education savings plan": 0.92,
        "qualified tuition program": 0.90,
        "college savings plan": 0.88,
        "prepaid tuition plan": 0.88,
        "education ira": 0.85,  # Old name for Coverdell ESA
        "ugma/utma": 0.82,
        "age-based investment option": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:age[- ]based|target[- ]date)\s*portfolio", 0.50),
        (r"gift\s*contribution", 0.45),
        (r"successor\s*(?:owner|participant)", 0.45),
        (r"maximum\s*contribution", 0.40),
        (r"(?:in[- ]state|out[- ]of[- ]state)\s*plan", 0.40),
        (r"investment\s*(?:options?|portfolios?)", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "529",
        "education",
        "savings",
        "tuition",
        "college",
        "beneficiary",
        "qualified",
        "expense",
        "coverdell",
        "esa",
        "ugma",
        "utma",
        "prepaid",
        "scholarship",
    },
    filename_patterns={
        "529": 0.85,
        "education": 0.70,
        "college": 0.65,
        "tuition": 0.65,
        "coverdell": 0.75,
    },
    # Exclusions to prevent confusion with other accounts
    exclude_patterns={
        # Retirement-specific
        r"401\s*\(?\s*k\s*\)?",
        r"individual\s*retirement",
        r"\bira\b",
        r"pension\s*(?:plan|benefit)",
        r"social\s*security",
        r"required\s*minimum\s*distribution",
        # Employment-related
        r"employer\s*(?:match|contribution)",
        r"vested\s*balance",
        r"salary\s*deferral",
        # Student loan documents
        r"student\s*loan\s*(?:statement|payment)",
        r"loan\s*servicer",
        r"interest\s*rate",
        r"repayment\s*plan",
        # Financial aid
        r"fafsa",
        r"financial\s*aid\s*(?:award|package)",
        r"pell\s*grant",
    },
    exclude_phrases={
        "retirement account",
        "loan statement",
        "financial aid award",
        "student loan",
    },
)


RETIREMENT_SUBTHEME_RULES: list[SubthemeRule] = [
    RETIREMENT_401K,
    RETIREMENT_IRA,
    PENSION_STATEMENT,
    SOCIAL_SECURITY,
    EDUCATION_529,
]


RETIREMENT_SUBTHEME_RULES_DICT = {rule.name: rule for rule in RETIREMENT_SUBTHEME_RULES}


__all__ = [
    "RETIREMENT_401K",
    "RETIREMENT_IRA",
    "PENSION_STATEMENT",
    "SOCIAL_SECURITY",
    "EDUCATION_529",
    "RETIREMENT_SUBTHEME_RULES",
    "RETIREMENT_SUBTHEME_RULES_DICT",
]
