"""
Legal > Court and Legal Proceedings subtheme rules.

Defines precise, production-ready patterns for:
- Court Order
- Legal Notice
- Court Filing
- Settlement Agreement
- Legal Correspondence

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Court Order - Judicial orders, judgments, verdicts, restraining orders
COURT_ORDER = SubthemeRule(
    name="court_order",
    display_name="Court Order",
    parent_theme="Legal",
    subtheme_category="Court and Legal Proceedings",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core court order patterns (highly distinctive)
        (r"(?:court\s*)?order", 0.95, "court_order"),
        (r"(?:final\s*)?judgment", 0.94, "judgment"),
        (r"(?:jury\s*)?verdict", 0.93, "verdict"),
        (r"(?:temporary\s*)?restraining\s*order", 0.92, "restraining_order"),
        (r"(?:preliminary\s*)?injunction", 0.91, "injunction"),
        (r"decree", 0.90, "decree"),
        # Judge and court patterns
        (r"(?:honorable\s*)?judge:?\s*[A-Z][a-z]+", 0.89, "judge_name"),
        (r"(?:superior|district|circuit)\s*court", 0.88, "court_type"),
        (r"case\s*(?:number|no\.):?\s*[A-Z0-9\-]+", 0.87, "case_number"),
        (r"(?:it\s*is\s*)?(?:hereby\s*)?ordered", 0.86, "ordered_language"),
        # Order type patterns
        (r"(?:protective|gag)\s*order", 0.87, "protective_order"),
        (r"(?:custody|support)\s*order", 0.86, "family_order"),
        (r"(?:search|arrest)\s*warrant", 0.85, "warrant"),
        (r"(?:summary\s*)?judgment", 0.84, "summary_judgment"),
        # Judicial language patterns
        (r"(?:court\s*)?(?:finds|found)\s*(?:that)?", 0.85, "court_findings"),
        (
            r"(?:plaintiff|defendant)\s*(?:is\s*)?(?:entitled|ordered)",
            0.84,
            "party_entitlement",
        ),
        (r"(?:granted|denied)\s*(?:in\s*)?(?:full|part)", 0.83, "ruling_outcome"),
        (r"(?:effective\s*)?(?:immediately|forthwith)", 0.82, "effective_timing"),
        # Enforcement patterns
        (r"(?:failure\s*to\s*)?comply", 0.84, "compliance"),
        (r"(?:contempt\s*of\s*court|sanctions)", 0.83, "contempt_sanctions"),
        (r"(?:shall\s*)?(?:be\s*)?enforced", 0.82, "enforcement"),
    ],
    definitive_phrases={
        # Core order phrases
        "court order": 0.95,
        "judgment": 0.94,
        "verdict": 0.93,
        "restraining order": 0.92,
        "injunction": 0.91,
        "decree": 0.90,
        "judicial order": 0.91,
        # Court authority phrases
        "it is hereby ordered": 0.90,
        "ordered and adjudged": 0.89,
        "court finds": 0.88,
        "court orders": 0.88,
        "hereby ordered": 0.87,
        # Order types
        "temporary restraining order": 0.89,
        "permanent injunction": 0.88,
        "protective order": 0.87,
        "summary judgment": 0.86,
        "default judgment": 0.85,
        "consent order": 0.84,
        # Judicial language
        "granted": 0.85,
        "denied": 0.85,
        "sustained": 0.84,
        "overruled": 0.84,
        "affirmed": 0.83,
        "reversed": 0.83,
        # Enforcement phrases
        "contempt of court": 0.84,
        "failure to comply": 0.83,
        "sanctions": 0.82,
        "enforceable": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Court information
        (r"court:?\s*", 0.46),
        (r"judge:?\s*", 0.44),
        (r"case\s*(?:no\.|number):?\s*", 0.44),
        (r"docket:?\s*", 0.42),
        # Order sections
        (r"findings:?\s*", 0.46),
        (r"conclusions:?\s*", 0.44),
        (r"order:?\s*", 0.48),
        (r"decree:?\s*", 0.42),
        # Party information
        (r"plaintiff:?\s*", 0.42),
        (r"defendant:?\s*", 0.42),
        (r"petitioner:?\s*", 0.40),
        (r"respondent:?\s*", 0.40),
        # Legal basis
        (r"pursuant\s*to:?\s*", 0.40),
        (r"authority:?\s*", 0.38),
        (r"jurisdiction:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Order-specific primary terms
        "order",
        "judgment",
        "verdict",
        "decree",
        "injunction",
        "restraining",
        "warrant",
        "ruling",
        # Court terms
        "court",
        "judge",
        "judicial",
        "bench",
        "tribunal",
        "magistrate",
        "justice",
        # Party terms
        "plaintiff",
        "defendant",
        "petitioner",
        "respondent",
        "appellant",
        "appellee",
        # Legal action terms
        "ordered",
        "adjudged",
        "decreed",
        "granted",
        "denied",
        "sustained",
        "overruled",
        "affirmed",
        # Enforcement terms
        "comply",
        "enforce",
        "contempt",
        "sanctions",
        "violation",
        "breach",
    },
    filename_patterns={
        "order": 0.78,
        "court_order": 0.80,
        "judgment": 0.78,
        "verdict": 0.76,
        "injunction": 0.74,
        "restraining_order": 0.76,
        "tro": 0.72,  # Temporary Restraining Order
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Notice patterns
        r"notice\s*(?:of\s*)?(?:hearing|appearance)",
        r"summons",
        r"subpoena",
        # Filing patterns
        r"complaint",
        r"petition\s*for",
        r"motion\s*(?:to|for)",
        r"brief",
        # Settlement patterns
        r"settlement\s*agreement",
        r"mediation\s*agreement",
        # Correspondence patterns
        r"retainer\s*agreement",
        r"attorney\s*letter",
    },
    exclude_phrases={
        "legal notice",
        "court filing",
        "settlement agreement",
        "attorney correspondence",
        "demand letter",
    },
)

# Legal Notice - Court summons, subpoenas, legal notifications, demand letters
LEGAL_NOTICE = SubthemeRule(
    name="legal_notice",
    display_name="Legal Notice",
    parent_theme="Legal",
    subtheme_category="Court and Legal Proceedings",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core notice patterns (highly distinctive)
        (r"(?:legal\s*)?notice", 0.94, "legal_notice"),
        (r"summons", 0.95, "summons"),
        (r"subpoena(?:\s*duces\s*tecum)?", 0.94, "subpoena"),
        (r"demand\s*letter", 0.93, "demand_letter"),
        (r"notice\s*(?:of\s*)?(?:hearing|appearance)", 0.92, "notice_hearing"),
        (r"cease\s*and\s*desist", 0.91, "cease_desist"),
        # Service and delivery patterns
        (
            r"(?:you\s*are\s*)?(?:hereby\s*)?(?:notified|summoned)",
            0.89,
            "notification_language",
        ),
        (r"(?:service\s*of\s*)?process", 0.88, "service_process"),
        (r"(?:proof|certificate)\s*of\s*service", 0.87, "proof_service"),
        (r"(?:personal|certified)\s*(?:service|delivery)", 0.86, "service_type"),
        # Response requirement patterns
        (r"(?:must|shall)\s*(?:appear|respond)", 0.88, "response_required"),
        (r"within\s*\d+\s*days", 0.87, "response_deadline"),
        (r"failure\s*to\s*(?:appear|respond)", 0.86, "failure_consequences"),
        (r"default\s*(?:judgment\s*)?(?:may|will)", 0.85, "default_warning"),
        # Demand patterns
        (r"demand\s*(?:is\s*)?(?:hereby\s*)?made", 0.86, "demand_made"),
        (r"(?:pay|payment)\s*(?:of\s*)?\$?[\d,]+", 0.85, "payment_demand"),
        (r"(?:cure|remedy)\s*(?:the\s*)?(?:breach|default)", 0.84, "cure_demand"),
        (r"(?:immediate|prompt)\s*(?:action|attention)", 0.83, "urgency"),
        # Legal action warning patterns
        (
            r"(?:legal\s*)?action\s*(?:will|may)\s*be\s*(?:taken|commenced)",
            0.85,
            "legal_action_warning",
        ),
        (r"(?:without\s*)?further\s*notice", 0.84, "no_further_notice"),
        (r"(?:pursue|seek)\s*(?:all\s*)?(?:legal\s*)?remedies", 0.83, "legal_remedies"),
    ],
    definitive_phrases={
        # Core notice phrases
        "legal notice": 0.94,
        "summons": 0.95,
        "subpoena": 0.94,
        "subpoena duces tecum": 0.93,
        "demand letter": 0.93,
        "notice of hearing": 0.92,
        "notice of appearance": 0.91,
        "cease and desist": 0.91,
        # Notification phrases
        "you are hereby notified": 0.90,
        "you are hereby summoned": 0.90,
        "notice is hereby given": 0.89,
        "take notice": 0.88,
        "please take notice": 0.87,
        # Response phrases
        "must appear": 0.88,
        "required to respond": 0.87,
        "answer within": 0.86,
        "failure to appear": 0.85,
        "failure to respond": 0.85,
        "default judgment": 0.84,
        # Demand phrases
        "demand is made": 0.86,
        "payment demanded": 0.85,
        "immediate payment": 0.84,
        "cure the breach": 0.83,
        "remedy the default": 0.83,
        # Warning phrases
        "legal action": 0.84,
        "further action": 0.83,
        "without further notice": 0.83,
        "time is of the essence": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Notice sections
        (r"to:?\s*", 0.46),
        (r"from:?\s*", 0.44),
        (r"re:?\s*", 0.44),
        (r"date:?\s*", 0.42),
        # Legal basis
        (r"pursuant\s*to:?\s*", 0.44),
        (r"under\s*(?:the\s*)?authority:?\s*", 0.42),
        (r"violation\s*of:?\s*", 0.42),
        # Response information
        (r"response\s*(?:required|due):?\s*", 0.44),
        (r"deadline:?\s*", 0.42),
        (r"appear\s*(?:at|before):?\s*", 0.42),
        # Service information
        (r"served\s*(?:on|upon):?\s*", 0.40),
        (r"method\s*of\s*service:?\s*", 0.38),
        (r"proof\s*of\s*service:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Notice-specific primary terms
        "notice",
        "summons",
        "subpoena",
        "demand",
        "notification",
        "service",
        "process",
        "cease",
        "desist",
        # Action terms
        "notify",
        "summon",
        "appear",
        "respond",
        "answer",
        "comply",
        "cure",
        "remedy",
        # Deadline terms
        "within",
        "days",
        "deadline",
        "due",
        "expire",
        "immediate",
        "forthwith",
        "promptly",
        # Warning terms
        "failure",
        "default",
        "consequences",
        "action",
        "legal",
        "proceedings",
        "litigation",
        # Service terms
        "served",
        "delivered",
        "certified",
        "registered",
        "receipt",
        "proof",
        "certificate",
    },
    filename_patterns={
        "notice": 0.76,
        "summons": 0.78,
        "subpoena": 0.78,
        "demand_letter": 0.76,
        "legal_notice": 0.78,
        "cease_desist": 0.74,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Order patterns
        r"(?:court\s*)?order",
        r"judgment",
        r"verdict",
        r"decree",
        # Filing patterns
        r"complaint",
        r"petition\s*for",
        r"motion\s*(?:to|for)",
        r"brief",
        # Settlement patterns
        r"settlement\s*agreement",
        r"mediation",
        # Correspondence patterns
        r"retainer\s*agreement",
        r"legal\s*opinion",
    },
    exclude_phrases={
        "court order",
        "court filing",
        "settlement agreement",
        "retainer agreement",
        "legal opinion",
    },
)

# Court Filing - Complaints, petitions, motions, briefs
COURT_FILING = SubthemeRule(
    name="court_filing",
    display_name="Court Filing",
    parent_theme="Legal",
    subtheme_category="Court and Legal Proceedings",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core filing patterns (highly distinctive)
        (r"complaint", 0.95, "complaint"),
        (r"petition(?:\s*for)?", 0.94, "petition"),
        (r"motion(?:\s*(?:to|for))?", 0.93, "motion"),
        (r"(?:appellate\s*)?brief", 0.92, "brief"),
        (r"(?:amended\s*)?complaint", 0.91, "amended_complaint"),
        (r"answer(?:\s*and\s*counterclaim)?", 0.90, "answer"),
        # Filing type patterns
        (r"motion\s*to\s*dismiss", 0.89, "motion_dismiss"),
        (r"motion\s*for\s*summary\s*judgment", 0.88, "motion_summary_judgment"),
        (r"motion\s*to\s*compel", 0.87, "motion_compel"),
        (r"petition\s*for\s*(?:writ|relief)", 0.86, "petition_writ"),
        # Pleading patterns
        (r"(?:plaintiff|petitioner)\s*(?:alleges?|states?)", 0.87, "plaintiff_alleges"),
        (r"causes?\s*of\s*action", 0.86, "causes_action"),
        (
            r"(?:first|second|third)\s*(?:cause\s*of\s*action|count)",
            0.85,
            "numbered_counts",
        ),
        (r"wherefore.*prays?", 0.84, "prayer_relief"),
        # Legal argument patterns
        (r"(?:legal\s*)?argument", 0.85, "legal_argument"),
        (r"(?:statement\s*of\s*)?(?:facts?|issues?)", 0.84, "statement_facts"),
        (
            r"(?:memorandum\s*of\s*)?(?:law|points\s*and\s*authorities)",
            0.83,
            "memorandum_law",
        ),
        (r"(?:respectfully\s*)?(?:submitted|requests?)", 0.82, "respectful_submission"),
        # Court filing markers
        (r"(?:filed|e-filed)\s*(?:with|in)", 0.84, "filed_with_court"),
        (r"(?:original|copy)\s*filed", 0.83, "filing_status"),
        (r"case\s*(?:no\.|number):?\s*[A-Z0-9\-]+", 0.82, "case_number"),
    ],
    definitive_phrases={
        # Core filing phrases
        "complaint": 0.95,
        "petition": 0.94,
        "motion": 0.93,
        "brief": 0.92,
        "amended complaint": 0.91,
        "answer": 0.90,
        "counterclaim": 0.89,
        "cross-complaint": 0.88,
        # Motion types
        "motion to dismiss": 0.90,
        "motion for summary judgment": 0.89,
        "motion to compel": 0.88,
        "motion in limine": 0.87,
        "motion to strike": 0.86,
        "motion for reconsideration": 0.85,
        # Petition types
        "petition for writ": 0.88,
        "petition for relief": 0.87,
        "petition for review": 0.86,
        "habeas corpus": 0.85,
        # Pleading phrases
        "plaintiff alleges": 0.87,
        "causes of action": 0.86,
        "prayer for relief": 0.85,
        "wherefore plaintiff prays": 0.84,
        "jurisdiction and venue": 0.83,
        # Legal argument phrases
        "statement of facts": 0.84,
        "statement of the case": 0.83,
        "legal argument": 0.83,
        "memorandum of law": 0.82,
        "points and authorities": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Filing sections
        (r"caption:?\s*", 0.44),
        (r"parties:?\s*", 0.42),
        (r"jurisdiction:?\s*", 0.44),
        (r"venue:?\s*", 0.42),
        # Pleading sections
        (r"allegations:?\s*", 0.46),
        (r"count\s*[IVX]+:?\s*", 0.44),
        (r"factual\s*background:?\s*", 0.44),
        (r"prayer:?\s*", 0.42),
        # Legal sections
        (r"argument:?\s*", 0.44),
        (r"discussion:?\s*", 0.42),
        (r"conclusion:?\s*", 0.40),
        (r"relief\s*(?:sought|requested):?\s*", 0.42),
        # Filing information
        (r"dated:?\s*", 0.38),
        (r"respectfully\s*submitted:?\s*", 0.40),
        (r"attorney\s*for:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Filing-specific primary terms
        "complaint",
        "petition",
        "motion",
        "brief",
        "pleading",
        "answer",
        "counterclaim",
        "reply",
        # Legal document terms
        "filing",
        "filed",
        "e-filed",
        "docket",
        "caption",
        "memorandum",
        "declaration",
        "affidavit",
        # Pleading terms
        "alleges",
        "allegations",
        "causes",
        "action",
        "count",
        "claim",
        "prayer",
        "relief",
        # Legal argument terms
        "argument",
        "facts",
        "law",
        "authority",
        "precedent",
        "statute",
        "regulation",
        "case",
        # Court terms
        "plaintiff",
        "defendant",
        "petitioner",
        "respondent",
        "court",
        "jurisdiction",
        "venue",
    },
    filename_patterns={
        "complaint": 0.78,
        "petition": 0.76,
        "motion": 0.76,
        "brief": 0.74,
        "filing": 0.72,
        "pleading": 0.72,
        "answer": 0.70,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Order patterns
        r"(?:court\s*)?order",
        r"judgment",
        r"verdict",
        r"decree",
        # Notice patterns
        r"summons",
        r"subpoena",
        r"notice\s*of\s*hearing",
        # Settlement patterns
        r"settlement\s*agreement",
        r"mediation\s*agreement",
        # Correspondence patterns
        r"retainer\s*agreement",
        r"attorney\s*letter",
        r"legal\s*opinion",
    },
    exclude_phrases={
        "court order",
        "legal notice",
        "settlement agreement",
        "retainer agreement",
        "legal opinion",
    },
)

# Settlement Agreement - Legal settlements, mediation agreements
SETTLEMENT_AGREEMENT = SubthemeRule(
    name="settlement_agreement",
    display_name="Settlement Agreement",
    parent_theme="Legal",
    subtheme_category="Court and Legal Proceedings",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core settlement patterns (highly distinctive)
        (r"settlement\s*agreement", 0.95, "settlement_agreement"),
        (r"(?:mediation\s*)?(?:settlement|agreement)", 0.93, "mediation_settlement"),
        (r"(?:compromise\s*and\s*)?release", 0.92, "compromise_release"),
        (r"(?:mutual\s*)?release\s*(?:and\s*settlement)", 0.91, "mutual_release"),
        (r"(?:confidential\s*)?settlement", 0.90, "confidential_settlement"),
        # Dispute resolution patterns
        (r"(?:full\s*and\s*final\s*)?settlement", 0.89, "full_settlement"),
        (r"(?:amicable\s*)?resolution", 0.88, "amicable_resolution"),
        (r"(?:dispute\s*)?resolution\s*agreement", 0.87, "dispute_resolution"),
        (r"(?:mediated\s*)?settlement", 0.86, "mediated_settlement"),
        # Release patterns
        (
            r"(?:general\s*)?release\s*(?:of\s*(?:all\s*)?claims?)",
            0.88,
            "release_claims",
        ),
        (r"(?:mutual\s*)?release\s*(?:of\s*liability)", 0.87, "release_liability"),
        (r"(?:waive|waiver)\s*(?:of\s*)?(?:claims?|rights?)", 0.86, "waiver_claims"),
        (r"discharge\s*(?:and\s*release)", 0.85, "discharge_release"),
        # Settlement terms patterns
        (r"settlement\s*(?:amount|sum):?\s*\$?[\d,]+", 0.87, "settlement_amount"),
        (r"(?:payment\s*)?(?:terms|schedule)", 0.85, "payment_terms"),
        (r"(?:lump\s*sum|installments?)", 0.84, "payment_type"),
        (r"(?:without\s*)?admission\s*of\s*(?:liability|guilt)", 0.83, "no_admission"),
        # Confidentiality patterns
        (
            r"(?:confidentiality\s*)?(?:clause|provision)",
            0.85,
            "confidentiality_clause",
        ),
        (r"(?:non-disclosure|nda)\s*(?:provision)?", 0.84, "nondisclosure"),
        (r"(?:shall\s*)?(?:remain\s*)?confidential", 0.83, "remain_confidential"),
        (r"(?:no\s*)?(?:publicity|public\s*statements?)", 0.82, "no_publicity"),
    ],
    definitive_phrases={
        # Core settlement phrases
        "settlement agreement": 0.95,
        "mediation agreement": 0.93,
        "settlement and release": 0.92,
        "compromise and release": 0.91,
        "mutual release": 0.90,
        "confidential settlement": 0.89,
        # Resolution phrases
        "full and final settlement": 0.90,
        "amicable resolution": 0.88,
        "dispute resolution": 0.87,
        "mediated settlement": 0.86,
        "negotiated settlement": 0.85,
        # Release phrases
        "release of all claims": 0.88,
        "general release": 0.87,
        "release and discharge": 0.86,
        "waiver of claims": 0.85,
        "covenant not to sue": 0.84,
        # Settlement terms
        "settlement amount": 0.86,
        "payment terms": 0.85,
        "without admission of liability": 0.84,
        "no admission of guilt": 0.83,
        "dismissal with prejudice": 0.83,
        # Confidentiality phrases
        "confidentiality provision": 0.84,
        "non-disclosure provision": 0.83,
        "confidential terms": 0.82,
        "no publicity": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Settlement sections
        (r"recitals:?\s*", 0.44),
        (r"whereas:?\s*", 0.42),
        (r"settlement\s*terms:?\s*", 0.46),
        (r"release:?\s*", 0.44),
        # Payment sections
        (r"payment:?\s*", 0.44),
        (r"consideration:?\s*", 0.42),
        (r"settlement\s*amount:?\s*", 0.44),
        # Legal sections
        (r"confidentiality:?\s*", 0.42),
        (r"non-disparagement:?\s*", 0.40),
        (r"indemnification:?\s*", 0.40),
        (r"governing\s*law:?\s*", 0.38),
        # Execution
        (r"effective\s*date:?\s*", 0.40),
        (r"signatures:?\s*", 0.38),
        (r"acknowledgment:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Settlement-specific primary terms
        "settlement",
        "mediation",
        "resolution",
        "compromise",
        "release",
        "discharge",
        "waiver",
        # Dispute terms
        "dispute",
        "claim",
        "controversy",
        "litigation",
        "lawsuit",
        "action",
        "proceeding",
        # Release terms
        "waive",
        "relinquish",
        "covenant",
        "sue",
        "liability",
        # Payment terms
        "payment",
        "compensation",
        "consideration",
        "amount",
        "installment",
        "lump",
        "sum",
        # Legal terms
        "confidential",
        "prejudice",
        "dismissal",
        "withdrawal",
        "admission",
        "fault",
        "guilt",
    },
    filename_patterns={
        "settlement": 0.78,
        "settlement_agreement": 0.80,
        "mediation": 0.74,
        "release": 0.72,
        "compromise": 0.70,
        "resolution": 0.70,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Order patterns
        r"(?:court\s*)?order",
        r"judgment",
        r"verdict",
        # Notice patterns
        r"summons",
        r"subpoena",
        r"notice\s*of\s*hearing",
        # Filing patterns
        r"complaint",
        r"petition\s*for",
        r"motion\s*(?:to|for)",
        # Correspondence patterns
        r"retainer\s*agreement",
        r"attorney\s*letter",
        r"legal\s*opinion",
    },
    exclude_phrases={
        "court order",
        "legal notice",
        "court filing",
        "retainer agreement",
        "legal opinion",
    },
)

# Legal Correspondence - Attorney letters, retainer agreements, legal opinions
LEGAL_CORRESPONDENCE = SubthemeRule(
    name="legal_correspondence",
    display_name="Legal Correspondence",
    parent_theme="Legal",
    subtheme_category="Court and Legal Proceedings",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core correspondence patterns (highly distinctive)
        (r"(?:attorney|lawyer)\s*(?:letter|correspondence)", 0.94, "attorney_letter"),
        (r"retainer\s*agreement", 0.95, "retainer_agreement"),
        (r"(?:legal\s*)?opinion\s*letter", 0.93, "opinion_letter"),
        (r"(?:engagement|representation)\s*letter", 0.92, "engagement_letter"),
        (r"(?:client\s*)?(?:advisory|advice)\s*letter", 0.91, "advisory_letter"),
        # Law firm patterns
        (r"law\s*(?:firm|office)(?:\s*of)?", 0.88, "law_firm"),
        (r"attorneys?\s*at\s*law", 0.87, "attorneys_at_law"),
        (r"(?:esquire|esq\.)", 0.86, "esquire"),
        (r"(?:counsel|counselor)\s*at\s*law", 0.85, "counsel"),
        # Retainer patterns
        (r"(?:legal\s*)?(?:fees?|retainer)", 0.87, "legal_fees"),
        (r"(?:hourly\s*)?(?:rate|billing):?\s*\$?[\d,]+", 0.86, "hourly_rate"),
        (r"(?:scope\s*of\s*)?representation", 0.85, "scope_representation"),
        (r"(?:attorney-client\s*)?(?:relationship|privilege)", 0.84, "attorney_client"),
        # Legal opinion patterns
        (r"(?:legal\s*)?(?:analysis|opinion)", 0.86, "legal_analysis"),
        (r"(?:our\s*)?(?:conclusion|recommendation)", 0.85, "conclusion"),
        (r"(?:based\s*on\s*)?(?:our\s*)?review", 0.84, "based_on_review"),
        (r"(?:legal\s*)?(?:research|authority)", 0.83, "legal_research"),
        # Professional communication patterns
        (r"(?:dear\s*)?(?:client|counsel)", 0.84, "salutation"),
        (r"(?:re|regarding):?\s*", 0.83, "regarding"),
        (r"(?:sincerely|respectfully)", 0.82, "closing"),
        (r"(?:privileged\s*and\s*)?confidential", 0.83, "privileged_confidential"),
    ],
    definitive_phrases={
        # Core correspondence phrases
        "attorney letter": 0.94,
        "retainer agreement": 0.95,
        "opinion letter": 0.92,
        "engagement letter": 0.91,
        "representation letter": 0.90,
        "client advisory": 0.89,
        # Law firm phrases
        "law firm": 0.88,
        "law office": 0.87,
        "attorneys at law": 0.87,
        "legal counsel": 0.86,
        "esquire": 0.85,
        # Retainer phrases
        "legal retainer": 0.88,
        "retainer fee": 0.87,
        "scope of representation": 0.86,
        "attorney-client relationship": 0.85,
        "attorney-client privilege": 0.85,
        "terms of engagement": 0.84,
        # Opinion phrases
        "legal opinion": 0.87,
        "legal analysis": 0.86,
        "legal advice": 0.85,
        "our opinion": 0.84,
        "we conclude": 0.83,
        "we recommend": 0.83,
        # Professional phrases
        "privileged and confidential": 0.84,
        "attorney work product": 0.83,
        "confidential communication": 0.82,
        "legal memorandum": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Letter sections
        (r"date:?\s*", 0.42),
        (r"to:?\s*", 0.44),
        (r"from:?\s*", 0.44),
        (r"re:?\s*", 0.46),
        # Opinion sections
        (r"background:?\s*", 0.44),
        (r"analysis:?\s*", 0.46),
        (r"conclusion:?\s*", 0.44),
        (r"recommendation:?\s*", 0.42),
        # Retainer sections
        (r"scope\s*of\s*(?:services|work):?\s*", 0.44),
        (r"fees:?\s*", 0.42),
        (r"billing:?\s*", 0.40),
        (r"termination:?\s*", 0.38),
        # Professional elements
        (r"sincerely:?\s*", 0.38),
        (r"respectfully:?\s*", 0.38),
        (r"enclosures?:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Correspondence-specific primary terms
        "attorney",
        "lawyer",
        "counsel",
        "esquire",
        "esq",
        "letter",
        "correspondence",
        "memorandum",
        # Retainer terms
        "retainer",
        "engagement",
        "representation",
        "retention",
        "fee",
        "billing",
        "hourly",
        "rate",
        # Opinion terms
        "opinion",
        "advice",
        "analysis",
        "recommendation",
        "conclusion",
        "review",
        "assessment",
        # Professional terms
        "client",
        "firm",
        "office",
        "practice",
        "privileged",
        "confidential",
        "work product",
        # Communication terms
        "regarding",
        "concerning",
        "matter",
        "case",
        "reference",
        "subject",
        "inquiry",
    },
    filename_patterns={
        "letter": 0.72,
        "correspondence": 0.74,
        "retainer": 0.78,
        "retainer_agreement": 0.80,
        "opinion": 0.76,
        "legal_opinion": 0.78,
        "engagement": 0.74,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Order patterns
        r"(?:court\s*)?order",
        r"judgment",
        r"verdict",
        # Notice patterns
        r"summons",
        r"subpoena",
        r"notice\s*of\s*hearing",
        # Filing patterns
        r"complaint",
        r"petition\s*for",
        r"motion\s*(?:to|for)",
        # Settlement patterns
        r"settlement\s*agreement",
        r"release\s*of\s*claims",
    },
    exclude_phrases={
        "court order",
        "legal notice",
        "court filing",
        "settlement agreement",
        "demand letter",
    },
)

# Export rules
COURT_PROCEEDINGS_SUBTHEME_RULES: List[SubthemeRule] = [
    COURT_ORDER,
    LEGAL_NOTICE,
    COURT_FILING,
    SETTLEMENT_AGREEMENT,
    LEGAL_CORRESPONDENCE,
]

COURT_PROCEEDINGS_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in COURT_PROCEEDINGS_SUBTHEME_RULES
}
