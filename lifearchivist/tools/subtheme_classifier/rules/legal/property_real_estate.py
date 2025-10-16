"""
Legal > Property and Real Estate subtheme rules.

Defines precise, production-ready patterns for:
- Property Deed
- Mortgage Document
- Title Document
- HOA Document
- Property Transfer

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Property Deed - Warranty deeds, quitclaim deeds, title documents
PROPERTY_DEED = SubthemeRule(
    name="property_deed",
    display_name="Property Deed",
    parent_theme="Legal",
    subtheme_category="Property and Real Estate",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core deed patterns (highly distinctive)
        (r"(?:warranty|quitclaim|grant)\s*deed", 0.95, "deed_type"),
        (r"(?:general|special)\s*warranty\s*deed", 0.94, "warranty_deed"),
        (r"quitclaim\s*deed", 0.93, "quitclaim_deed"),
        (r"deed\s*of\s*(?:conveyance|transfer)", 0.92, "deed_of_conveyance"),
        (r"(?:this\s*)?(?:indenture|deed)\s*(?:made|executed)", 0.90, "deed_execution"),
        # Grantor/Grantee patterns (deed-specific)
        (r"grantor:?\s*[A-Z][a-z]+", 0.89, "grantor_name"),
        (r"grantee:?\s*[A-Z][a-z]+", 0.89, "grantee_name"),
        (r"(?:party|parties)\s*of\s*the\s*first\s*part", 0.87, "first_party"),
        (r"(?:party|parties)\s*of\s*the\s*second\s*part", 0.87, "second_party"),
        # Property description patterns
        (r"legal\s*description:?\s*", 0.88, "legal_description"),
        (r"(?:lot|block|tract)\s*(?:number|#)?:?\s*\d+", 0.86, "lot_block_number"),
        (r"parcel\s*(?:number|id|#):?\s*[A-Z0-9\-]+", 0.85, "parcel_number"),
        (
            r"(?:situated|located)\s*in\s*(?:the\s*)?(?:county|city)\s*of",
            0.84,
            "property_location",
        ),
        # Conveyance language (deed-specific)
        (
            r"(?:do\s*)?(?:hereby\s*)?(?:grant|convey|transfer)",
            0.87,
            "conveyance_language",
        ),
        (r"(?:bargain|sell|alien)\s*and\s*(?:sell|convey)", 0.86, "bargain_sell"),
        (r"to\s*have\s*and\s*to\s*hold", 0.85, "habendum_clause"),
        (r"(?:fee\s*simple|fee\s*simple\s*absolute)", 0.84, "fee_simple"),
        # Warranty/covenant patterns
        (r"(?:covenant|warrant)\s*(?:and\s*agree)?", 0.85, "covenant_language"),
        (r"(?:general|special)\s*warranty", 0.84, "warranty_type"),
        (r"(?:free\s*and\s*clear|clear\s*title)", 0.83, "clear_title"),
    ],
    definitive_phrases={
        # Core deed phrases
        "warranty deed": 0.95,
        "quitclaim deed": 0.94,
        "grant deed": 0.93,
        "deed of conveyance": 0.92,
        "general warranty deed": 0.93,
        "special warranty deed": 0.92,
        "bargain and sale deed": 0.91,
        # Party designations
        "grantor": 0.90,
        "grantee": 0.90,
        "party of the first part": 0.88,
        "party of the second part": 0.88,
        # Conveyance phrases
        "hereby grant and convey": 0.89,
        "bargain and sell": 0.88,
        "grant, bargain, sell": 0.88,
        "to have and to hold": 0.87,
        "fee simple": 0.86,
        "fee simple absolute": 0.87,
        # Property description phrases
        "legal description": 0.88,
        "real property": 0.86,
        "real estate": 0.85,
        "parcel of land": 0.85,
        "tract of land": 0.84,
        # Warranty phrases
        "covenant and warrant": 0.86,
        "free and clear": 0.85,
        "clear title": 0.85,
        "good and marketable title": 0.84,
        "quiet enjoyment": 0.83,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Deed sections
        (r"witnesseth:?\s*", 0.46),
        (r"consideration:?\s*", 0.48),
        (r"property\s*description:?\s*", 0.48),
        (r"habendum:?\s*", 0.44),
        (r"covenants:?\s*", 0.44),
        # Legal description elements
        (r"township:?\s*", 0.42),
        (r"range:?\s*", 0.42),
        (r"section:?\s*", 0.40),
        (r"plat:?\s*", 0.40),
        # Recording information
        (r"recording\s*(?:date|information):?\s*", 0.42),
        (r"book:?\s*\d+", 0.40),
        (r"page:?\s*\d+", 0.40),
        (r"instrument\s*(?:number|#):?\s*", 0.38),
        # Signatures
        (r"grantor'?s?\s*signature", 0.42),
        (r"notary\s*public", 0.40),
        (r"acknowledgment", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Deed-specific primary terms
        "deed",
        "warranty",
        "quitclaim",
        "grant",
        "conveyance",
        "transfer",
        "bargain",
        "sale",
        # Party terms
        "grantor",
        "grantee",
        "conveyor",
        "conveyee",
        # Property terms
        "property",
        "real",
        "estate",
        "land",
        "parcel",
        "lot",
        "block",
        "tract",
        "premises",
        # Legal description terms
        "legal",
        "description",
        "township",
        "range",
        "section",
        "plat",
        "subdivision",
        "survey",
        # Conveyance terms
        "convey",
        "assign",
        "release",
        "remise",
        "alien",
        "warrant",
        # Title terms
        "title",
        "ownership",
        "interest",
        "fee",
        "simple",
        "absolute",
        "marketable",
    },
    filename_patterns={
        "deed": 0.78,
        "warranty_deed": 0.80,
        "quitclaim": 0.78,
        "property_deed": 0.77,
        "grant_deed": 0.76,
        "conveyance": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Mortgage patterns
        r"mortgage\s*(?:agreement|document)",
        r"promissory\s*note",
        r"loan\s*amount",
        r"interest\s*rate",
        # Title insurance patterns
        r"title\s*insurance\s*policy",
        r"title\s*commitment",
        r"schedule\s*[AB]\s*exceptions",
        # HOA patterns
        r"homeowners?\s*association",
        r"cc&rs?",
        r"bylaws",
        # Transfer tax patterns
        r"transfer\s*tax",
        r"documentary\s*stamps",
    },
    exclude_phrases={
        "mortgage agreement",
        "deed of trust",
        "title insurance",
        "hoa agreement",
        "easement agreement",
    },
)

# Mortgage Document - Mortgage agreements, deed of trust (legal aspects)
MORTGAGE_DOCUMENT = SubthemeRule(
    name="mortgage_document",
    display_name="Mortgage Document",
    parent_theme="Legal",
    subtheme_category="Property and Real Estate",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core mortgage patterns (highly distinctive)
        (r"mortgage\s*(?:agreement|document|instrument)", 0.95, "mortgage_agreement"),
        (r"deed\s*of\s*trust", 0.94, "deed_of_trust"),
        (r"(?:first|second)\s*mortgage", 0.92, "mortgage_position"),
        (r"home\s*(?:loan|mortgage)\s*agreement", 0.91, "home_mortgage"),
        (r"security\s*instrument", 0.90, "security_instrument"),
        # Party patterns (mortgage-specific)
        (r"mortgagor:?\s*[A-Z][a-z]+", 0.89, "mortgagor_name"),
        (r"mortgagee:?\s*[A-Z][a-z]+", 0.89, "mortgagee_name"),
        (r"borrower:?\s*[A-Z][a-z]+", 0.88, "borrower_name"),
        (r"lender:?\s*[A-Z][a-z]+", 0.88, "lender_name"),
        (r"trustor.*trustee.*beneficiary", 0.87, "deed_trust_parties"),
        # Loan terms patterns
        (r"principal\s*(?:amount|sum):?\s*\$?[\d,]+", 0.88, "principal_amount"),
        (r"interest\s*rate:?\s*\d+\.?\d*\s*%", 0.87, "interest_rate"),
        (r"(?:loan|mortgage)\s*term:?\s*\d+\s*years?", 0.86, "loan_term"),
        (r"monthly\s*payment:?\s*\$?[\d,]+", 0.85, "monthly_payment"),
        (r"maturity\s*date:?\s*", 0.84, "maturity_date"),
        # Security interest patterns
        (r"(?:grant|convey)\s*(?:a\s*)?security\s*interest", 0.87, "security_interest"),
        (
            r"(?:secure|secured\s*by)\s*(?:the\s*)?(?:real\s*)?property",
            0.86,
            "secured_by_property",
        ),
        (r"power\s*of\s*sale", 0.85, "power_of_sale"),
        (r"right\s*(?:to\s*)?foreclose", 0.84, "foreclosure_right"),
        # Property as collateral patterns
        (r"(?:property\s*)?(?:used\s*)?as\s*collateral", 0.85, "collateral"),
        (r"(?:encumber|lien)\s*(?:on|upon)\s*(?:the\s*)?property", 0.84, "encumbrance"),
        (r"first\s*lien\s*position", 0.83, "lien_position"),
    ],
    definitive_phrases={
        # Core mortgage phrases
        "mortgage agreement": 0.95,
        "deed of trust": 0.94,
        "mortgage document": 0.93,
        "security instrument": 0.92,
        "home mortgage": 0.91,
        "mortgage loan": 0.90,
        # Party designations
        "mortgagor": 0.90,
        "mortgagee": 0.90,
        "borrower": 0.88,
        "lender": 0.88,
        "trustor": 0.87,
        "trustee": 0.87,
        "beneficiary": 0.86,
        # Loan terms
        "principal amount": 0.88,
        "interest rate": 0.87,
        "loan term": 0.86,
        "monthly payment": 0.85,
        "amortization schedule": 0.84,
        "prepayment penalty": 0.83,
        # Security phrases
        "security interest": 0.87,
        "secured by property": 0.86,
        "power of sale": 0.85,
        "foreclosure": 0.84,
        "default provisions": 0.84,
        # Legal phrases specific to mortgages
        "promissory note": 0.85,
        "acceleration clause": 0.84,
        "due on sale": 0.83,
        "escrow account": 0.82,
        "pmi": 0.81,  # Private Mortgage Insurance
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Mortgage sections
        (r"definitions:?\s*", 0.44),
        (r"loan\s*terms:?\s*", 0.48),
        (r"payment\s*(?:terms|schedule):?\s*", 0.46),
        (r"default\s*(?:provisions|remedies):?\s*", 0.46),
        (r"insurance\s*requirements:?\s*", 0.44),
        # Property description
        (r"property\s*address:?\s*", 0.44),
        (r"legal\s*description:?\s*", 0.42),
        (r"parcel\s*(?:number|id):?\s*", 0.40),
        # Financial terms
        (r"escrow:?\s*", 0.42),
        (r"taxes\s*and\s*insurance:?\s*", 0.42),
        (r"late\s*charges:?\s*", 0.40),
        (r"prepayment:?\s*", 0.38),
        # Legal provisions
        (r"governing\s*law:?\s*", 0.38),
        (r"severability:?\s*", 0.36),
        (r"notices:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Mortgage-specific primary terms
        "mortgage",
        "deed",
        "trust",
        "loan",
        "security",
        "instrument",
        "lien",
        "encumbrance",
        # Party terms
        "mortgagor",
        "mortgagee",
        "borrower",
        "lender",
        "trustor",
        "trustee",
        "beneficiary",
        # Financial terms
        "principal",
        "interest",
        "payment",
        "amortization",
        "escrow",
        "prepayment",
        "default",
        "foreclosure",
        # Property terms (mortgage context)
        "property",
        "real",
        "estate",
        "collateral",
        "secured",
        "encumber",
        # Legal terms specific to mortgages
        "promissory",
        "note",
        "acceleration",
        "power",
        "sale",
        "foreclose",
        "cure",
    },
    filename_patterns={
        "mortgage": 0.78,
        "deed_of_trust": 0.78,
        "deed_trust": 0.76,
        "mortgage_agreement": 0.80,
        "home_loan": 0.74,
        "security_instrument": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Pure deed patterns
        r"warranty\s*deed",
        r"quitclaim\s*deed",
        r"grant\s*deed",
        r"bargain\s*and\s*sale",
        # Title patterns
        r"title\s*insurance",
        r"title\s*report",
        r"title\s*commitment",
        # HOA patterns
        r"homeowners?\s*association",
        r"cc&rs?",
        r"architectural\s*committee",
        # Pure transfer patterns
        r"easement\s*agreement",
        r"right\s*of\s*way",
    },
    exclude_phrases={
        "warranty deed",
        "quitclaim deed",
        "title insurance",
        "hoa agreement",
        "easement agreement",
    },
)

# Title Document - Title insurance, title reports, title transfers
TITLE_DOCUMENT = SubthemeRule(
    name="title_document",
    display_name="Title Document",
    parent_theme="Legal",
    subtheme_category="Property and Real Estate",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core title patterns (highly distinctive)
        (r"title\s*insurance\s*policy", 0.95, "title_insurance_policy"),
        (r"(?:preliminary\s*)?title\s*report", 0.94, "title_report"),
        (r"title\s*commitment", 0.93, "title_commitment"),
        (r"(?:owner'?s?|lender'?s?)\s*title\s*insurance", 0.92, "title_insurance_type"),
        (r"abstract\s*of\s*title", 0.91, "abstract_of_title"),
        (r"title\s*search\s*report", 0.90, "title_search"),
        # Title company patterns
        (r"title\s*company:?\s*[A-Z][a-z]+", 0.88, "title_company"),
        (r"title\s*insurer:?\s*[A-Z][a-z]+", 0.87, "title_insurer"),
        (r"underwriter:?\s*[A-Z][a-z]+", 0.86, "underwriter"),
        (r"policy\s*(?:number|#):?\s*[A-Z0-9\-]+", 0.85, "policy_number"),
        # Coverage patterns
        (r"(?:coverage\s*)?amount:?\s*\$?[\d,]+", 0.87, "coverage_amount"),
        (r"effective\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.86, "effective_date"),
        (r"schedule\s*[AB]\s*(?:exceptions?)?", 0.85, "schedule_exceptions"),
        (r"covered\s*risks?", 0.84, "covered_risks"),
        # Title status patterns
        (r"(?:clear|marketable)\s*title", 0.86, "clear_title"),
        (r"chain\s*of\s*title", 0.85, "chain_of_title"),
        (r"title\s*vesting", 0.84, "title_vesting"),
        (r"fee\s*simple\s*(?:absolute\s*)?title", 0.83, "fee_simple_title"),
        # Exceptions and exclusions patterns
        (r"(?:standard\s*)?exceptions?\s*(?:to\s*coverage)?", 0.85, "exceptions"),
        (r"(?:liens?|encumbrances?)\s*(?:of\s*record)?", 0.84, "liens_encumbrances"),
        (r"easements?\s*(?:of\s*record)?", 0.83, "easements"),
        (
            r"(?:covenants?|restrictions?)\s*(?:of\s*record)?",
            0.82,
            "covenants_restrictions",
        ),
    ],
    definitive_phrases={
        # Core title phrases
        "title insurance policy": 0.95,
        "title report": 0.94,
        "title commitment": 0.93,
        "title insurance": 0.92,
        "abstract of title": 0.91,
        "title search": 0.90,
        "preliminary title report": 0.91,
        # Insurance types
        "owner's title insurance": 0.90,
        "lender's title insurance": 0.90,
        "alta policy": 0.88,  # American Land Title Association
        "clta policy": 0.87,  # California Land Title Association
        # Coverage phrases
        "insured amount": 0.87,
        "coverage amount": 0.86,
        "policy coverage": 0.85,
        "covered risks": 0.84,
        "exclusions from coverage": 0.83,
        # Title status phrases
        "marketable title": 0.86,
        "clear title": 0.85,
        "insurable title": 0.84,
        "chain of title": 0.84,
        "title defect": 0.83,
        "cloud on title": 0.82,
        # Exception phrases
        "schedule a": 0.84,
        "schedule b": 0.84,
        "standard exceptions": 0.83,
        "special exceptions": 0.82,
        "requirements": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Title sections
        (r"schedule\s*a:?\s*", 0.48),
        (r"schedule\s*b:?\s*", 0.48),
        (r"covered\s*risks:?\s*", 0.46),
        (r"exclusions:?\s*", 0.44),
        (r"conditions:?\s*", 0.42),
        # Property information
        (r"legal\s*description:?\s*", 0.44),
        (r"property\s*address:?\s*", 0.42),
        (r"vesting:?\s*", 0.42),
        (r"estate\s*or\s*interest:?\s*", 0.40),
        # Exceptions and requirements
        (r"exceptions:?\s*", 0.44),
        (r"requirements:?\s*", 0.42),
        (r"notes:?\s*", 0.38),
        # Insurance terms
        (r"premium:?\s*", 0.40),
        (r"deductible:?\s*", 0.38),
        (r"endorsements?:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Title-specific primary terms
        "title",
        "insurance",
        "policy",
        "report",
        "commitment",
        "abstract",
        "search",
        "examination",
        # Insurance terms
        "coverage",
        "premium",
        "insured",
        "insurer",
        "underwriter",
        "endorsement",
        "exclusion",
        # Title status terms
        "marketable",
        "clear",
        "insurable",
        "defect",
        "cloud",
        "chain",
        "vesting",
        # Exception terms
        "exception",
        "lien",
        "encumbrance",
        "easement",
        "covenant",
        "restriction",
        "requirement",
        # Legal terms (title context)
        "schedule",
        "alta",
        "clta",
        "survey",
        "plat",
        "record",
        "recording",
    },
    filename_patterns={
        "title": 0.76,
        "title_insurance": 0.80,
        "title_report": 0.78,
        "title_commitment": 0.77,
        "title_policy": 0.76,
        "abstract": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Deed patterns
        r"warranty\s*deed",
        r"quitclaim\s*deed",
        r"grant\s*deed",
        r"grantor.*grantee",
        # Mortgage patterns
        r"mortgage\s*agreement",
        r"deed\s*of\s*trust",
        r"mortgagor.*mortgagee",
        r"principal\s*amount",
        # HOA patterns
        r"homeowners?\s*association",
        r"cc&rs?",
        r"dues\s*and\s*assessments",
        # Transfer patterns
        r"transfer\s*(?:of\s*)?ownership",
        r"conveyance\s*document",
    },
    exclude_phrases={
        "warranty deed",
        "mortgage agreement",
        "deed of trust",
        "hoa agreement",
        "transfer document",
    },
)

# HOA Document - HOA agreements, CC&Rs, bylaws
HOA_DOCUMENT = SubthemeRule(
    name="hoa_document",
    display_name="HOA Document",
    parent_theme="Legal",
    subtheme_category="Property and Real Estate",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core HOA patterns (highly distinctive)
        (r"homeowners?\s*association", 0.95, "homeowners_association"),
        (r"(?:covenants?|conditions?)\s*(?:and|&)\s*restrictions?", 0.94, "ccr"),
        (r"cc&rs?", 0.93, "ccr_abbrev"),
        (r"(?:hoa|homeowners?\s*association)\s*bylaws", 0.92, "hoa_bylaws"),
        (
            r"declaration\s*of\s*(?:covenants?|restrictions?)",
            0.91,
            "declaration_covenants",
        ),
        (r"(?:master\s*)?deed\s*restrictions?", 0.90, "deed_restrictions"),
        # HOA governance patterns
        (r"board\s*of\s*directors", 0.88, "board_of_directors"),
        (r"architectural\s*(?:review\s*)?committee", 0.87, "architectural_committee"),
        (r"(?:annual|special)\s*meeting", 0.86, "meeting_type"),
        (r"voting\s*(?:rights|procedures?)", 0.85, "voting_rights"),
        # Assessment and fee patterns
        (r"(?:hoa\s*)?(?:dues|assessments?)", 0.87, "hoa_dues"),
        (r"(?:monthly|annual)\s*assessment:?\s*\$?[\d,]+", 0.86, "assessment_amount"),
        (r"special\s*assessment", 0.85, "special_assessment"),
        (r"common\s*(?:area|expense)", 0.84, "common_area_expense"),
        # Property use restrictions
        (r"(?:use\s*)?restrictions?", 0.85, "use_restrictions"),
        (r"prohibited\s*(?:uses?|activities)", 0.84, "prohibited_uses"),
        (r"architectural\s*(?:guidelines|standards)", 0.83, "architectural_guidelines"),
        (
            r"landscaping\s*(?:requirements?|guidelines)",
            0.82,
            "landscaping_requirements",
        ),
        # Common area patterns
        (r"common\s*(?:areas?|elements?|property)", 0.85, "common_areas"),
        (r"(?:shared|community)\s*facilities", 0.84, "shared_facilities"),
        (r"(?:pool|clubhouse|gym)\s*rules?", 0.83, "facility_rules"),
    ],
    definitive_phrases={
        # Core HOA phrases
        "homeowners association": 0.95,
        "hoa": 0.92,
        "covenants and restrictions": 0.94,
        "cc&r": 0.93,
        "cc&rs": 0.93,
        "bylaws": 0.91,
        "declaration of covenants": 0.92,
        "deed restrictions": 0.90,
        # Governance phrases
        "board of directors": 0.88,
        "architectural committee": 0.87,
        "architectural review board": 0.87,
        "annual meeting": 0.85,
        "special meeting": 0.85,
        "proxy voting": 0.84,
        # Assessment phrases
        "hoa dues": 0.87,
        "monthly assessment": 0.86,
        "annual assessment": 0.86,
        "special assessment": 0.85,
        "late fees": 0.84,
        "lien rights": 0.83,
        # Restriction phrases
        "use restrictions": 0.85,
        "architectural guidelines": 0.84,
        "landscaping requirements": 0.83,
        "parking restrictions": 0.82,
        "pet restrictions": 0.82,
        # Common area phrases
        "common areas": 0.85,
        "common elements": 0.84,
        "community property": 0.83,
        "shared facilities": 0.83,
        "maintenance responsibilities": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # HOA sections
        (r"article\s*[IVX]+:?\s*", 0.44),
        (r"definitions:?\s*", 0.42),
        (r"membership:?\s*", 0.44),
        (r"assessments:?\s*", 0.46),
        (r"restrictions:?\s*", 0.46),
        # Governance sections
        (r"board\s*(?:of\s*directors)?:?\s*", 0.44),
        (r"officers:?\s*", 0.42),
        (r"committees:?\s*", 0.40),
        (r"meetings:?\s*", 0.40),
        # Property sections
        (r"common\s*areas?:?\s*", 0.42),
        (r"maintenance:?\s*", 0.42),
        (r"architectural\s*(?:control|review):?\s*", 0.44),
        # Legal sections
        (r"enforcement:?\s*", 0.40),
        (r"violations:?\s*", 0.38),
        (r"amendments:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # HOA-specific primary terms
        "hoa",
        "homeowners",
        "association",
        "covenant",
        "restriction",
        "ccr",
        "bylaws",
        "declaration",
        # Governance terms
        "board",
        "directors",
        "officers",
        "committee",
        "meeting",
        "voting",
        "proxy",
        "quorum",
        # Financial terms
        "assessment",
        "dues",
        "fee",
        "budget",
        "reserve",
        "lien",
        "collection",
        # Property terms
        "common",
        "area",
        "facilities",
        "maintenance",
        "architectural",
        "landscaping",
        "parking",
        # Restriction terms
        "prohibited",
        "permitted",
        "approval",
        "violation",
        "enforcement",
        "fine",
        "penalty",
    },
    filename_patterns={
        "hoa": 0.78,
        "ccr": 0.78,
        "cc&r": 0.78,
        "bylaws": 0.76,
        "covenants": 0.74,
        "restrictions": 0.72,
        "homeowners": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Deed patterns
        r"warranty\s*deed",
        r"quitclaim\s*deed",
        r"grantor.*grantee",
        # Mortgage patterns
        r"mortgage\s*agreement",
        r"principal\s*amount",
        r"interest\s*rate",
        # Title patterns
        r"title\s*insurance",
        r"title\s*report",
        r"covered\s*risks",
        # Transfer patterns
        r"easement\s*agreement",
        r"right\s*of\s*way",
    },
    exclude_phrases={
        "warranty deed",
        "mortgage agreement",
        "title insurance",
        "easement agreement",
        "transfer document",
    },
)

# Property Transfer - Transfer documents, conveyance papers, easements
PROPERTY_TRANSFER = SubthemeRule(
    name="property_transfer",
    display_name="Property Transfer",
    parent_theme="Legal",
    subtheme_category="Property and Real Estate",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core transfer patterns (highly distinctive)
        (
            r"(?:transfer|conveyance)\s*(?:of\s*)?(?:property|ownership)",
            0.94,
            "transfer_ownership",
        ),
        (r"easement\s*(?:agreement|grant)", 0.93, "easement_agreement"),
        (r"right[\s-]of[\s-]way\s*(?:agreement|grant)", 0.92, "right_of_way"),
        (
            r"(?:property\s*)?transfer\s*(?:document|agreement)",
            0.91,
            "transfer_document",
        ),
        (r"assignment\s*of\s*(?:interest|rights)", 0.90, "assignment_rights"),
        # Easement-specific patterns
        (r"(?:perpetual|temporary)\s*easement", 0.89, "easement_type"),
        (r"(?:utility|access|drainage)\s*easement", 0.88, "easement_purpose"),
        (r"dominant\s*(?:estate|tenement)", 0.87, "dominant_estate"),
        (r"servient\s*(?:estate|tenement)", 0.87, "servient_estate"),
        (r"easement\s*(?:area|location)", 0.85, "easement_area"),
        # Transfer terms patterns
        (
            r"(?:transfer|convey)\s*(?:all\s*)?(?:right|title|interest)",
            0.87,
            "transfer_rights",
        ),
        (r"(?:for\s*)?valuable\s*consideration", 0.86, "consideration"),
        (r"transfer\s*tax", 0.85, "transfer_tax"),
        (r"documentary\s*stamps?", 0.84, "documentary_stamps"),
        # Rights and restrictions patterns
        (r"(?:grant|convey)\s*(?:the\s*)?right", 0.86, "grant_right"),
        (r"(?:ingress\s*and\s*egress|access)\s*rights?", 0.85, "access_rights"),
        (
            r"(?:burden|benefit)\s*(?:of|to)\s*(?:the\s*)?property",
            0.84,
            "burden_benefit",
        ),
        (r"runs?\s*with\s*(?:the\s*)?land", 0.83, "runs_with_land"),
        # Boundary and survey patterns
        (
            r"(?:metes\s*and\s*bounds|boundary)\s*description",
            0.85,
            "boundary_description",
        ),
        (r"survey\s*(?:plat|map)", 0.84, "survey_reference"),
        (r"(?:width|length)\s*of\s*easement", 0.83, "easement_dimensions"),
    ],
    definitive_phrases={
        # Core transfer phrases
        "transfer of ownership": 0.94,
        "transfer of property": 0.93,
        "conveyance of property": 0.92,
        "easement agreement": 0.93,
        "right of way": 0.92,
        "property transfer": 0.91,
        "assignment of rights": 0.90,
        # Easement phrases
        "perpetual easement": 0.89,
        "temporary easement": 0.88,
        "utility easement": 0.88,
        "access easement": 0.87,
        "drainage easement": 0.87,
        "conservation easement": 0.86,
        # Rights phrases
        "grant of easement": 0.88,
        "easement rights": 0.87,
        "ingress and egress": 0.86,
        "right of access": 0.85,
        "right to use": 0.84,
        # Legal phrases
        "runs with the land": 0.85,
        "dominant estate": 0.84,
        "servient estate": 0.84,
        "appurtenant easement": 0.83,
        "easement in gross": 0.82,
        # Transfer terms
        "valuable consideration": 0.84,
        "transfer tax": 0.83,
        "documentary stamps": 0.82,
        "recording fees": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Transfer sections
        (r"recitals:?\s*", 0.44),
        (r"grant\s*of\s*easement:?\s*", 0.48),
        (r"description\s*of\s*easement:?\s*", 0.46),
        (r"purpose:?\s*", 0.44),
        (r"term:?\s*", 0.42),
        # Property description
        (r"legal\s*description:?\s*", 0.44),
        (r"property\s*affected:?\s*", 0.42),
        (r"easement\s*area:?\s*", 0.42),
        # Rights and obligations
        (r"rights\s*granted:?\s*", 0.44),
        (r"restrictions:?\s*", 0.42),
        (r"maintenance:?\s*", 0.40),
        (r"indemnification:?\s*", 0.38),
        # Recording information
        (r"recording\s*information:?\s*", 0.40),
        (r"tax\s*stamps:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Transfer-specific primary terms
        "transfer",
        "conveyance",
        "easement",
        "right",
        "way",
        "assignment",
        "grant",
        "convey",
        # Easement types
        "utility",
        "access",
        "drainage",
        "conservation",
        "perpetual",
        "temporary",
        "appurtenant",
        "gross",
        # Rights terms
        "ingress",
        "egress",
        "use",
        "burden",
        "benefit",
        "dominant",
        "servient",
        "runs",
        # Property terms
        "property",
        "land",
        "parcel",
        "estate",
        "boundary",
        "survey",
        "plat",
        # Legal terms
        "consideration",
        "recording",
        "documentary",
        "stamps",
        "tax",
        "fees",
    },
    filename_patterns={
        "easement": 0.78,
        "transfer": 0.76,
        "conveyance": 0.74,
        "right_of_way": 0.76,
        "row": 0.72,  # Right of Way abbreviation
        "assignment": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Deed patterns
        r"warranty\s*deed",
        r"quitclaim\s*deed",
        r"bargain\s*and\s*sale",
        # Mortgage patterns
        r"mortgage\s*agreement",
        r"deed\s*of\s*trust",
        r"principal\s*amount",
        # Title patterns
        r"title\s*insurance",
        r"title\s*report",
        # HOA patterns
        r"homeowners?\s*association",
        r"cc&rs?",
        r"architectural\s*committee",
    },
    exclude_phrases={
        "warranty deed",
        "mortgage agreement",
        "title insurance",
        "hoa agreement",
        "deed of trust",
    },
)

# Export rules
PROPERTY_REAL_ESTATE_SUBTHEME_RULES: List[SubthemeRule] = [
    PROPERTY_DEED,
    MORTGAGE_DOCUMENT,
    TITLE_DOCUMENT,
    HOA_DOCUMENT,
    PROPERTY_TRANSFER,
]

PROPERTY_REAL_ESTATE_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in PROPERTY_REAL_ESTATE_SUBTHEME_RULES
}
