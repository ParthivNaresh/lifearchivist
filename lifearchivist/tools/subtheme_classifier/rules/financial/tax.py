"""
Financial > Tax subtheme rules.

Defines precise, production-ready patterns for:
- W-2 Form
- 1099 Form
- Tax Return
- Property Tax

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from lifearchivist.tools.subtheme_classifier.rules import SubthemeRule

# W-2 Form
TAX_W2 = SubthemeRule(
    name="tax_w2",
    display_name="W-2 Form",
    parent_theme="Financial",
    subtheme_category="Tax",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core W-2 identifiers
        (r"form\s*w-?2", 0.95, "w2_form_header"),
        (r"wage\s*and\s*tax\s*statement", 0.92, "wage_tax_statement"),
        (r"employee'?s?\s*social\s*security\s*number", 0.90, "employee_ssn"),
        (
            r"employer'?s?\s*(?:federal\s*)?(?:ein|identification\s*number)",
            0.88,
            "employer_ein",
        ),
        # W-2 specific boxes
        (r"box\s*1\s*[:\-]?\s*wages", 0.90, "box1_wages"),
        (r"box\s*2\s*[:\-]?\s*federal\s*income\s*tax", 0.90, "box2_federal_tax"),
        (r"box\s*3\s*[:\-]?\s*social\s*security\s*wages", 0.88, "box3_ss_wages"),
        (r"box\s*4\s*[:\-]?\s*social\s*security\s*tax", 0.88, "box4_ss_tax"),
        (r"box\s*5\s*[:\-]?\s*medicare\s*wages", 0.86, "box5_medicare_wages"),
        (r"box\s*12[a-d]?\s*[:\-]?\s*", 0.85, "box12_codes"),
    ],
    definitive_phrases={
        "form w-2": 0.95,
        "form w2": 0.95,
        "wage and tax statement": 0.92,
        "copy a for social security administration": 0.90,
        "copy b to be filed with employee's federal tax return": 0.90,
        "copy c for employee's records": 0.88,
        "statutory employee": 0.85,
        "retirement plan": 0.82,
        "third-party sick pay": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"state\s*wages", 0.50),
        (r"local\s*wages", 0.45),
        (r"dependent\s*care\s*benefits", 0.45),
        (r"allocated\s*tips", 0.40),
        (r"advance\s*eic\s*payment", 0.40),
        (r"nonqualified\s*plans", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "w2",
        "w-2",
        "wages",
        "salary",
        "withholding",
        "federal",
        "social",
        "security",
        "medicare",
        "employer",
        "employee",
        "ein",
        "ssn",
        "box",
    },
    filename_patterns={
        "w2": 0.85,
        "w-2": 0.85,
        "wage": 0.70,
        "tax": 0.60,
    },
    # Exclusions to prevent confusion with other tax forms
    exclude_patterns={
        # 1099 forms
        r"form\s*1099",
        r"nonemployee\s*compensation",
        r"miscellaneous\s*income",
        r"interest\s*income",
        r"dividend\s*(?:income|distribution)",
        # Tax returns
        r"form\s*1040",
        r"schedule\s*[a-z]",
        r"adjusted\s*gross\s*income",
        r"itemized\s*deductions",
        # Property tax
        r"property\s*tax\s*(?:bill|statement)",
        r"assessed\s*value",
        r"tax\s*parcel",
    },
    exclude_phrases={
        "independent contractor",
        "tax return",
        "property assessment",
    },
)

# 1099 Form
TAX_1099 = SubthemeRule(
    name="tax_1099",
    display_name="1099 Form",
    parent_theme="Financial",
    subtheme_category="Tax",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core 1099 identifiers
        (r"form\s*1099(?:-[a-z]+)?", 0.95, "1099_form_header"),
        # Specific 1099 variants
        (r"1099-?misc", 0.92, "1099_misc"),
        (r"1099-?int", 0.92, "1099_int"),
        (r"1099-?div", 0.92, "1099_div"),
        (r"1099-?nec", 0.92, "1099_nec"),
        (r"1099-?r", 0.90, "1099_r"),
        (r"1099-?b", 0.90, "1099_b"),
        (r"1099-?g", 0.90, "1099_g"),
        # Common 1099 fields
        (
            r"(?:payer'?s?|payor'?s?)\s*(?:tin|federal\s*identification)",
            0.88,
            "payer_tin",
        ),
        (r"recipient'?s?\s*(?:tin|identification\s*number)", 0.88, "recipient_tin"),
        (r"nonemployee\s*compensation", 0.87, "nonemployee_comp"),
        (r"miscellaneous\s*income", 0.86, "misc_income"),
    ],
    definitive_phrases={
        "form 1099": 0.95,
        "miscellaneous income": 0.88,
        "nonemployee compensation": 0.88,
        "interest income": 0.88,
        "dividends and distributions": 0.88,
        "distributions from pensions": 0.85,
        "proceeds from broker": 0.85,
        "certain government payments": 0.82,
        "rents royalties": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:ordinary\s*)?dividends", 0.50),
        (r"qualified\s*dividends", 0.50),
        (r"capital\s*gain\s*distribution", 0.45),
        (r"federal\s*income\s*tax\s*withheld", 0.45),
        (r"state\s*tax\s*withheld", 0.40),
        (r"foreign\s*tax\s*paid", 0.40),
        (r"gross\s*proceeds", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "1099",
        "income",
        "interest",
        "dividend",
        "distribution",
        "compensation",
        "nonemployee",
        "contractor",
        "payer",
        "recipient",
        "proceeds",
        "royalties",
        "rents",
    },
    filename_patterns={
        "1099": 0.85,
        "misc": 0.65,
        "int": 0.65,
        "div": 0.65,
        "nec": 0.65,
    },
    # Exclusions to prevent confusion with other tax forms
    exclude_patterns={
        # W-2 forms
        r"form\s*w-?2",
        r"wage\s*and\s*tax\s*statement",
        r"employee'?s?\s*social\s*security",
        r"box\s*[1-9]\s*[:\-]?\s*wages",
        # Tax returns
        r"form\s*1040",
        r"schedule\s*[a-z]",
        r"filing\s*status",
        r"standard\s*deduction",
        # Property tax
        r"property\s*tax",
        r"real\s*estate\s*tax",
        r"assessed\s*value",
    },
    exclude_phrases={
        "employee wages",
        "tax return",
        "property assessment",
    },
)

# Tax Return
TAX_RETURN = SubthemeRule(
    name="tax_return",
    display_name="Tax Return",
    parent_theme="Financial",
    subtheme_category="Tax",
    # Primary identifiers (high confidence)
    unique_patterns=[
        # Core tax return identifiers
        (r"form\s*1040(?:[a-z]{1,2})?", 0.95, "1040_form_header"),
        (
            r"u\.?s\.?\s*individual\s*income\s*tax\s*return",
            0.92,
            "individual_tax_return",
        ),
        (r"(?:your\s*)?filing\s*status", 0.90, "filing_status"),
        (r"adjusted\s*gross\s*income", 0.90, "agi"),
        (r"taxable\s*income", 0.88, "taxable_income"),
        # Schedules and attachments
        (r"schedule\s*[a-z]\s", 0.88, "tax_schedule"),
        (r"itemized\s*deductions", 0.87, "itemized_deductions"),
        (r"standard\s*deduction", 0.86, "standard_deduction"),
        # Refund or amount owed
        (r"(?:refund|overpayment)", 0.86, "refund_field"),
        (r"amount\s*you\s*owe", 0.85, "amount_owed"),
    ],
    definitive_phrases={
        "form 1040": 0.95,
        "individual income tax return": 0.92,
        "married filing jointly": 0.88,
        "single": 0.85,
        "head of household": 0.85,
        "married filing separately": 0.85,
        "qualifying widow(er)": 0.82,
        "tax computation": 0.82,
        "payments and refundable credits": 0.80,
    },
    # Secondary identifiers (weighted structure/fields)
    structure_patterns=[
        (r"(?:tax\s*)?credits", 0.50),
        (r"other\s*taxes", 0.45),
        (r"estimated\s*tax\s*payments", 0.45),
        (r"earned\s*income\s*credit", 0.45),
        (r"child\s*tax\s*credit", 0.40),
        (r"education\s*credits", 0.40),
        (r"(?:ira\s*)?deduction", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints)
    keywords={
        "1040",
        "return",
        "income",
        "tax",
        "filing",
        "status",
        "deduction",
        "credit",
        "agi",
        "adjusted",
        "gross",
        "taxable",
        "refund",
        "schedule",
        "itemized",
    },
    filename_patterns={
        "1040": 0.85,
        "return": 0.75,
        "tax": 0.65,
        "federal": 0.60,
    },
    # Exclusions to prevent confusion with other tax documents
    exclude_patterns={
        # W-2 and 1099 forms
        r"wage\s*and\s*tax\s*statement",
        r"form\s*w-?2",
        r"form\s*1099",
        r"nonemployee\s*compensation",
        # Property tax
        r"property\s*tax\s*(?:bill|statement)",
        r"real\s*estate\s*tax",
        r"tax\s*parcel",
        r"mill\s*rate",
        # State-specific returns
        r"state\s*income\s*tax\s*return",
        r"state\s*tax\s*form",
    },
    exclude_phrases={
        "property tax bill",
        "wage statement",
        "information return",
    },
)


TAX_SUBTHEME_RULES: list[SubthemeRule] = [
    TAX_W2,
    TAX_1099,
    TAX_RETURN,
]


TAX_SUBTHEME_RULES_DICT = {rule.name: rule for rule in TAX_SUBTHEME_RULES}
