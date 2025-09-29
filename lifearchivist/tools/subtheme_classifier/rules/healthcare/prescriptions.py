"""
Healthcare > Prescriptions and Medications subtheme rules.

Defines precise, production-ready patterns for:
- Prescription Label
- Medication List
- Prior Authorization

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Prescription Label - Actual prescription documents from pharmacy
PRESCRIPTION_LABEL = SubthemeRule(
    name="prescription_label",
    display_name="Prescription Label",
    parent_theme="Healthcare",
    subtheme_category="Prescriptions and Medications",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core prescription label patterns
        (r"rx\s*(?:number|#):?\s*[0-9\-]{5,}", 0.95, "prescription_number"),
        (r"prescription\s*(?:label|information)", 0.93, "prescription_label_header"),
        (r"(?:ndc|national\s*drug\s*code):?\s*\d{5}-\d{4}-\d{2}", 0.91, "ndc_code"),
        (r"dea\s*(?:number|#):?\s*[A-Z]{2}\d{7}", 0.89, "dea_number"),
        (r"prescriber:?\s*(?:dr\.?|doctor)", 0.88, "prescriber_field"),
        (r"pharmacy:?\s*(?:name|phone)", 0.87, "pharmacy_info"),
        # Dosage and administration patterns specific to labels
        (r"take\s*\d+\s*(?:tablet|capsule|pill|ml|mg)", 0.91, "dosage_instruction"),
        (r"(?:sig|directions):?\s*take", 0.90, "sig_directions"),
        (
            r"\d+\s*(?:mg|mcg|ml|units?)\s*(?:tablet|capsule|solution)",
            0.89,
            "medication_strength",
        ),
        (
            r"(?:by\s*mouth|orally|subcutaneous|intramuscular|intravenous|topical)",
            0.87,
            "route_administration",
        ),
        (
            r"(?:once|twice|three\s*times|four\s*times)\s*(?:a\s*day|daily)",
            0.86,
            "frequency_pattern",
        ),
        (r"(?:qd|bid|tid|qid|prn|q\d+h)", 0.88, "medical_frequency_abbreviation"),
        # Supply and refill patterns
        (r"quantity:?\s*\d+", 0.87, "quantity_dispensed"),
        (r"days?\s*supply:?\s*\d+", 0.88, "days_supply"),
        (
            r"refills?\s*(?:remaining|left|authorized):?\s*\d+",
            0.89,
            "refills_remaining",
        ),
        (
            r"(?:date\s*filled|dispensed):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.87,
            "date_filled",
        ),
        (
            r"(?:expiration|discard\s*after):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.86,
            "expiration_date",
        ),
        # Pharmacy-specific patterns
        (r"lot\s*(?:number|#):?\s*[A-Z0-9\-]{4,}", 0.85, "lot_number"),
        (r"(?:generic|brand)\s*(?:for|equivalent)", 0.84, "generic_brand_indicator"),
    ],
    definitive_phrases={
        # Core prescription label phrases
        "prescription label": 0.93,
        "prescription information": 0.91,
        "rx number": 0.91,
        "prescriber information": 0.87,
        "pharmacy label": 0.86,
        "controlled substance": 0.89,
        "generic substitution": 0.85,
        "brand name": 0.84,
        "generic name": 0.84,
        # Dosage instructions specific to labels
        "take as directed": 0.87,
        "for oral use": 0.86,
        "shake well": 0.84,
        "with food": 0.83,
        "on empty stomach": 0.83,
        "do not crush": 0.84,
        "keep refrigerated": 0.83,
        # Pharmacy-specific phrases
        "date filled": 0.87,
        "date dispensed": 0.87,
        "discard after": 0.85,
        "auxiliary labels": 0.84,
        "patient counseling": 0.83,
        # Safety warnings on labels
        "black box warning": 0.89,
        "may cause drowsiness": 0.84,
        "do not drive": 0.83,
        "avoid alcohol": 0.83,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Prescription label structure
        (r"patient\s*name", 0.52),
        (r"date\s*of\s*birth", 0.50),
        (r"prescriber\s*(?:name|signature)", 0.48),
        (r"dea\s*(?:number|schedule)", 0.45),
        (r"npi\s*number", 0.43),
        # Medication details on label
        (r"strength", 0.47),
        (r"dosage\s*form", 0.45),
        (r"route", 0.44),
        (r"frequency", 0.44),
        (r"duration", 0.42),
        # Supply information
        (r"quantity\s*dispensed", 0.47),
        (r"refills\s*authorized", 0.45),
        (r"generic\s*equivalent", 0.42),
        (r"manufacturer", 0.40),
        (r"lot\s*number", 0.38),
        # Pharmacy information
        (r"pharmacist", 0.40),
        (r"rph", 0.38),  # Registered Pharmacist
        (r"pharmacy\s*address", 0.36),
        (r"pharmacy\s*phone", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Core prescription label terms
        "prescription",
        "rx",
        "medication",
        "medicine",
        "drug",
        "prescriber",
        "pharmacy",
        "pharmacist",
        "dispense",
        "fill",
        "refill",
        # Dosage terms
        "dose",
        "dosage",
        "strength",
        "tablet",
        "capsule",
        "pill",
        "solution",
        "suspension",
        "cream",
        "ointment",
        "patch",
        "injection",
        "mg",
        "mcg",
        "ml",
        "unit",
        "gram",
        # Administration terms
        "take",
        "apply",
        "inject",
        "inhale",
        "instill",
        "oral",
        "topical",
        "subcutaneous",
        "intramuscular",
        "daily",
        "twice",
        "morning",
        "evening",
        "bedtime",
        # Supply terms
        "quantity",
        "supply",
        "days",
        "bottle",
        "vial",
        "tube",
        "package",
        "blister",
        "pen",
        # Label-specific terms
        "label",
        "filled",
        "dispensed",
        "expires",
        "discard",
        "lot",
        "batch",
        "ndc",
        "dea",
        "schedule",
    },
    filename_patterns={
        "prescription": 0.78,
        "rx": 0.75,
        "pharmacy": 0.72,
        "label": 0.70,
        "medication": 0.68,
        "drug": 0.65,
        "refill": 0.65,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Medication list patterns
        r"(?:current|active)\s*medications?\s*list",
        r"medication\s*reconciliation",
        r"home\s*medications",
        r"discharge\s*medications",
        # Prior authorization patterns
        r"prior\s*authorization\s*(?:request|form)",
        r"formulary\s*(?:exception|review)",
        r"step\s*therapy",
        r"coverage\s*determination",
        # Test result patterns
        r"lab(?:oratory)?\s*results?\s*report",
        r"test\s*results?\s*summary",
        r"specimen\s*(?:id|number)",
        r"reference\s*range",
        r"imaging\s*(?:report|study)",
        r"radiology\s*report",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"review\s*of\s*systems",
        r"physical\s*exam(?:ination)?",
        r"discharge\s*summary",
        r"progress\s*note",
        # Billing patterns
        r"(?:amount|balance)\s*due",
        r"payment\s*(?:due|required)",
        r"insurance\s*claim\s*form",
        r"billing\s*(?:statement|invoice)",
        r"procedure\s*code\s*\d{5}",
        r"total\s*charges",
        # EOB patterns
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        r"patient\s*responsibility",
        r"plan\s*pays",
    },
    exclude_phrases={
        "medication list",
        "medication reconciliation",
        "prior authorization",
        "formulary exception",
        "lab results",
        "test report",
        "clinical notes",
        "office visit",
        "amount due",
        "billing statement",
    },
)

# Medication List - Current medications, reconciliation, and medication summaries
MEDICATION_LIST = SubthemeRule(
    name="medication_list",
    display_name="Medication List",
    parent_theme="Healthcare",
    subtheme_category="Prescriptions and Medications",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core medication list patterns
        (r"(?:current|active)\s*medications?\s*list", 0.94, "medication_list_header"),
        (r"medication\s*reconciliation", 0.93, "medication_reconciliation"),
        (r"medications?\s*(?:summary|review)", 0.91, "medications_summary"),
        (r"home\s*medications", 0.89, "home_medications"),
        (r"discharge\s*medications", 0.89, "discharge_medications"),
        (r"admission\s*medications", 0.88, "admission_medications"),
        # Medication list structure patterns
        (r"medication\s*name.*dosage.*frequency", 0.90, "medication_table_header"),
        (
            r"(?:start|stop)\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.86,
            "medication_dates",
        ),
        (
            r"last\s*(?:updated|reviewed):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.85,
            "last_updated",
        ),
        # Allergy and reaction patterns
        (
            r"allergies?\s*(?:and\s*)?(?:reactions?|intolerances?)",
            0.88,
            "allergies_section",
        ),
        (r"(?:nkda|no\s*known\s*drug\s*allergies)", 0.87, "no_allergies"),
        (r"adverse\s*(?:drug\s*)?reactions?", 0.86, "adverse_reactions"),
        # Medication categories in lists
        (r"(?:prescription|rx)\s*medications", 0.85, "prescription_meds_section"),
        (r"over[- ]the[- ]counter\s*(?:medications|otc)", 0.85, "otc_section"),
        (r"(?:vitamins?|supplements?|herbals?)", 0.84, "supplements_section"),
    ],
    definitive_phrases={
        # Core list phrases
        "medication list": 0.93,
        "current medications": 0.91,
        "active medications": 0.91,
        "medication reconciliation": 0.93,
        "medication review": 0.89,
        "medication summary": 0.89,
        # Context phrases
        "home medications": 0.88,
        "discharge medications": 0.88,
        "admission medications": 0.87,
        "outpatient medications": 0.86,
        "inpatient medications": 0.86,
        # Reconciliation phrases
        "medication reconciled": 0.90,
        "verified with patient": 0.87,
        "confirmed with pharmacy": 0.86,
        "medication history": 0.85,
        # Allergy phrases
        "medication allergies": 0.87,
        "drug allergies": 0.87,
        "adverse reactions": 0.86,
        "drug intolerances": 0.85,
        "allergy list": 0.85,
        # Status phrases
        "continue medication": 0.84,
        "discontinue medication": 0.84,
        "new medication": 0.83,
        "changed medication": 0.83,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # List structure
        (r"medication\s*name", 0.50),
        (r"dose\s*(?:/|and)?\s*strength", 0.48),
        (r"frequency", 0.46),
        (r"route", 0.44),
        (r"indication", 0.42),
        # Dates and timing
        (r"start\s*date", 0.45),
        (r"stop\s*date", 0.43),
        (r"last\s*filled", 0.40),
        (r"next\s*refill", 0.38),
        # Provider information
        (r"prescribing\s*provider", 0.42),
        (r"ordering\s*physician", 0.40),
        (r"reviewed\s*by", 0.38),
        # Status indicators
        (r"active", 0.40),
        (r"inactive", 0.38),
        (r"discontinued", 0.38),
        (r"on\s*hold", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # List terms
        "list",
        "summary",
        "review",
        "reconciliation",
        "current",
        "active",
        "home",
        "discharge",
        "admission",
        "outpatient",
        "inpatient",
        # Medication terms
        "medication",
        "medicine",
        "drug",
        "prescription",
        "otc",
        "vitamin",
        "supplement",
        "herbal",
        # Action terms
        "continue",
        "discontinue",
        "start",
        "stop",
        "change",
        "modify",
        "add",
        "remove",
        "update",
        "verify",
        "confirm",
        # Allergy terms
        "allergy",
        "allergies",
        "reaction",
        "intolerance",
        "adverse",
        "nkda",
        "sensitivity",
        # Common medications in lists
        "aspirin",
        "tylenol",
        "ibuprofen",
        "acetaminophen",
        "metformin",
        "lisinopril",
        "atorvastatin",
        "omeprazole",
    },
    filename_patterns={
        "medication_list": 0.75,
        "med_list": 0.73,
        "medications": 0.70,
        "reconciliation": 0.72,
        "med_rec": 0.70,
        "discharge_meds": 0.68,
        "home_meds": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Prescription label patterns
        r"rx\s*(?:number|#):?\s*[0-9\-]{5,}",
        r"pharmacy\s*label",
        r"date\s*filled",
        r"refills?\s*remaining",
        r"days?\s*supply",
        # Prior authorization patterns
        r"prior\s*authorization\s*(?:request|form)",
        r"formulary\s*exception",
        r"coverage\s*determination",
        # Test result patterns
        r"lab(?:oratory)?\s*results?",
        r"test\s*results?",
        # Medical record patterns
        r"chief\s*complaint",
        r"physical\s*exam",
        # Billing patterns
        r"amount\s*due",
        r"payment\s*required",
    },
    exclude_phrases={
        "prescription label",
        "pharmacy label",
        "prior authorization",
        "formulary exception",
        "lab results",
        "test report",
        "amount due",
        "billing statement",
    },
)

# Prior Authorization - Insurance approval requests for medications
PRIOR_AUTHORIZATION = SubthemeRule(
    name="prior_authorization",
    display_name="Prior Authorization",
    parent_theme="Healthcare",
    subtheme_category="Prescriptions and Medications",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core prior authorization patterns
        (r"prior\s*authorization\s*(?:request|form)", 0.95, "prior_auth_header"),
        (
            r"(?:pa|prior\s*auth)\s*(?:number|#):?\s*[A-Z0-9\-]{5,}",
            0.92,
            "prior_auth_number",
        ),
        (r"pre[- ]?authorization\s*(?:request|required)", 0.91, "preauthorization"),
        (r"medication\s*authorization\s*(?:request|form)", 0.90, "medication_auth"),
        # Formulary and coverage patterns
        (r"formulary\s*(?:exception|review|request)", 0.90, "formulary_exception"),
        (r"non[- ]formulary\s*(?:medication|drug|request)", 0.89, "non_formulary"),
        (r"step\s*therapy\s*(?:required|exception|override)", 0.88, "step_therapy"),
        (r"coverage\s*determination", 0.87, "coverage_determination"),
        (r"tier\s*exception\s*request", 0.86, "tier_exception"),
        # Medical necessity patterns
        (r"medical\s*necessity", 0.88, "medical_necessity"),
        (r"clinical\s*(?:justification|rationale)", 0.87, "clinical_justification"),
        (r"(?:diagnosis|icd[- ]?10)\s*code:?\s*[A-Z]\d{2}", 0.86, "diagnosis_code"),
        # Approval/denial patterns
        (
            r"(?:approved|approved\s*through):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.87,
            "approval_date",
        ),
        (
            r"authorization\s*(?:valid|effective)\s*(?:from|through)",
            0.86,
            "auth_validity",
        ),
        (r"(?:denied|denial)\s*(?:date|reason)", 0.85, "denial_info"),
        (r"appeal\s*(?:request|process|deadline)", 0.85, "appeal_info"),
    ],
    definitive_phrases={
        # Core authorization phrases
        "prior authorization": 0.95,
        "prior approval": 0.93,
        "preauthorization": 0.92,
        "medication authorization": 0.90,
        "drug authorization": 0.89,
        # Formulary phrases
        "formulary exception": 0.91,
        "non-formulary": 0.89,
        "formulary review": 0.88,
        "preferred alternative": 0.86,
        "step therapy": 0.87,
        "tier exception": 0.86,
        # Coverage phrases
        "coverage determination": 0.88,
        "coverage criteria": 0.86,
        "benefit investigation": 0.85,
        "insurance approval": 0.85,
        # Medical necessity phrases
        "medical necessity": 0.89,
        "medically necessary": 0.88,
        "clinical justification": 0.87,
        "clinical criteria": 0.86,
        "treatment rationale": 0.85,
        # Process phrases
        "urgent request": 0.86,
        "expedited review": 0.86,
        "standard review": 0.84,
        "appeal rights": 0.85,
        "reconsideration": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Request information
        (r"request\s*date", 0.50),
        (r"submission\s*date", 0.48),
        (r"member\s*(?:id|number)", 0.46),
        (r"group\s*number", 0.44),
        # Medication information
        (r"medication\s*requested", 0.48),
        (r"drug\s*name", 0.46),
        (r"dosage\s*requested", 0.44),
        (r"quantity\s*requested", 0.42),
        (r"duration\s*of\s*therapy", 0.40),
        # Clinical information
        (r"diagnosis", 0.45),
        (r"icd[- ]?10", 0.43),
        (r"clinical\s*information", 0.42),
        (r"treatment\s*history", 0.40),
        (r"failed\s*therapies", 0.40),
        # Provider information
        (r"prescribing\s*provider", 0.42),
        (r"npi", 0.40),
        (r"tax\s*id", 0.38),
        (r"office\s*contact", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Authorization terms
        "prior",
        "authorization",
        "approval",
        "preauthorization",
        "pa",
        "request",
        "review",
        "determination",
        "decision",
        # Formulary terms
        "formulary",
        "exception",
        "tier",
        "preferred",
        "alternative",
        "non-formulary",
        "step",
        "therapy",
        "protocol",
        # Coverage terms
        "coverage",
        "benefit",
        "insurance",
        "plan",
        "policy",
        "criteria",
        "guideline",
        "requirement",
        # Medical terms
        "medical",
        "necessity",
        "clinical",
        "justification",
        "rationale",
        "diagnosis",
        "indication",
        "evidence",
        "documentation",
        # Process terms
        "urgent",
        "expedited",
        "standard",
        "appeal",
        "reconsideration",
        "denial",
        "pending",
        # Common PA medications
        "specialty",
        "biologic",
        "injectable",
        "compound",
        "experimental",
        "investigational",
        "off-label",
    },
    filename_patterns={
        "prior_auth": 0.75,
        "pa_form": 0.73,
        "authorization": 0.70,
        "formulary": 0.70,
        "pa_request": 0.72,
        "coverage": 0.68,
        "exception": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Prescription label patterns
        r"rx\s*(?:number|#):?\s*[0-9\-]{5,}",
        r"pharmacy\s*label",
        r"date\s*filled",
        r"refills?\s*remaining",
        # Medication list patterns
        r"(?:current|active)\s*medications?\s*list",
        r"medication\s*reconciliation",
        # Test result patterns
        r"lab(?:oratory)?\s*results?",
        r"test\s*results?",
        # Medical record patterns
        r"chief\s*complaint",
        r"physical\s*exam",
        # Billing patterns
        r"amount\s*due",
        r"payment\s*required",
        r"billing\s*statement",
    },
    exclude_phrases={
        "prescription label",
        "medication list",
        "medication reconciliation",
        "lab results",
        "test report",
        "medical record",
        "amount due",
        "billing statement",
    },
)


# Export rules
PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES: List[SubthemeRule] = [
    PRESCRIPTION_LABEL,
    MEDICATION_LIST,
    PRIOR_AUTHORIZATION,
]

PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in PRESCRIPTIONS_MEDICATIONS_SUBTHEME_RULES
}
