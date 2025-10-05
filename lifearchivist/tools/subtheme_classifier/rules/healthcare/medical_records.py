"""
Healthcare > Medical Records subtheme rules.

Defines precise, production-ready patterns for:
- Medical History
- Discharge Summary
- Immunization Record

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Medical History - Patient medical history, consultation reports, and clinical notes
MEDICAL_HISTORY = SubthemeRule(
    name="medical_history",
    display_name="Medical History",
    parent_theme="Healthcare",
    subtheme_category="Medical Records",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core medical history identifiers
        (r"medical\s*(?:history|record)", 0.93, "medical_history_header"),
        (
            r"patient\s*(?:id|identifier|mrn):?\s*[A-Z0-9\-]{4,}",
            0.91,
            "patient_identifier",
        ),
        (
            r"medical\s*record\s*(?:number|no\.?|#):?\s*[A-Z0-9\-]{4,}",
            0.91,
            "medical_record_number",
        ),
        (r"chief\s*complaint:?\s*.{5,}", 0.90, "chief_complaint_section"),
        (r"history\s*of\s*present\s*illness", 0.92, "hpi_section"),
        (r"past\s*medical\s*history", 0.91, "pmh_section"),
        (r"review\s*of\s*systems", 0.89, "ros_section"),
        (r"physical\s*exam(?:ination)?:?\s*", 0.88, "physical_exam_section"),
        (r"assessment\s*(?:and|&)\s*plan", 0.91, "assessment_plan_section"),
        # History and physical patterns
        (r"history\s*(?:and|&)\s*physical", 0.92, "h_and_p"),
        (r"(?:social|family|surgical)\s*history", 0.88, "history_sections"),
        (r"allergies:?\s*(?:nkda|no\s*known)", 0.86, "allergy_section"),
        # Consultation patterns
        (r"consultation\s*(?:report|note)", 0.91, "consultation_document"),
        (r"referring\s*(?:physician|provider|doctor)", 0.88, "referring_provider"),
        (r"specialist\s*(?:consultation|opinion)", 0.89, "specialist_consultation"),
        (r"second\s*opinion", 0.87, "second_opinion"),
        # Progress note patterns
        (r"progress\s*note", 0.90, "progress_note_header"),
        (r"soap\s*note|subjective.*objective.*assessment.*plan", 0.89, "soap_format"),
        (r"office\s*visit\s*(?:note|summary)", 0.88, "office_visit"),
        (r"follow[- ]up\s*(?:visit|note)", 0.87, "followup_note"),
        # Vital signs patterns
        (r"vital\s*signs:?\s*", 0.86, "vital_signs_section"),
        (
            r"(?:bp|blood\s*pressure):?\s*\d{2,3}/\d{2,3}",
            0.85,
            "blood_pressure_reading",
        ),
        (
            r"(?:hr|heart\s*rate|pulse):?\s*\d{2,3}\s*(?:bpm|/min)?",
            0.84,
            "heart_rate_reading",
        ),
        (r"temp(?:erature)?:?\s*\d{2,3}\.?\d*\s*°?[FC]?", 0.83, "temperature_reading"),
    ],
    definitive_phrases={
        # Core medical history phrases
        "medical history": 0.93,
        "patient history": 0.91,
        "clinical history": 0.90,
        "medical record": 0.90,
        "patient information": 0.87,
        "clinical notes": 0.88,
        "encounter date": 0.86,
        "provider notes": 0.87,
        # History and physical
        "history and physical": 0.94,
        "h&p": 0.92,
        "review of systems": 0.90,
        "social history": 0.87,
        "family history": 0.87,
        "surgical history": 0.87,
        "past medical history": 0.91,
        "past surgical history": 0.89,
        "allergies and reactions": 0.86,
        # Consultation related
        "consultation report": 0.92,
        "consultation note": 0.91,
        "specialist consultation": 0.90,
        "second opinion": 0.87,
        "referral consultation": 0.88,
        "consultative opinion": 0.89,
        # Progress notes
        "progress note": 0.90,
        "office visit": 0.86,
        "follow-up visit": 0.86,
        "clinic note": 0.87,
        "encounter note": 0.87,
        "soap note": 0.89,
        # Provider information
        "attending physician": 0.87,
        "primary care provider": 0.86,
        "treating physician": 0.85,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Medical history sections
        (r"medications:?\s*", 0.52),
        (r"allergies:?\s*", 0.50),
        (r"social\s*history:?\s*", 0.47),
        (r"family\s*history:?\s*", 0.47),
        (r"surgical\s*history:?\s*", 0.45),
        (r"habits:?\s*", 0.42),
        # Examination findings
        (r"general\s*appearance:?\s*", 0.42),
        (r"heent:?\s*", 0.44),  # Head, Eyes, Ears, Nose, Throat
        (r"cardiovascular:?\s*", 0.42),
        (r"respiratory:?\s*", 0.42),
        (r"gastrointestinal:?\s*", 0.40),
        (r"neurological:?\s*", 0.40),
        (r"musculoskeletal:?\s*", 0.38),
        (r"psychiatric:?\s*", 0.38),
        # Clinical elements
        (r"impression:?\s*", 0.47),
        (r"recommendations:?\s*", 0.45),
        (r"plan\s*of\s*care:?\s*", 0.43),
        (r"prognosis:?\s*", 0.42),
        # Provider information
        (r"provider\s*signature", 0.37),
        (r"electronically\s*signed", 0.37),
        (r"dictated\s*by", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Medical history types
        "medical",
        "history",
        "record",
        "clinical",
        "patient",
        "encounter",
        "consultation",
        "progress",
        "note",
        "visit",
        "exam",
        "physical",
        # Medical sections
        "chief",
        "complaint",
        "hpi",
        "pmh",
        "ros",
        "assessment",
        "plan",
        "subjective",
        "objective",
        "soap",
        # Medical terms
        "diagnosis",
        "symptoms",
        "examination",
        "vital",
        "signs",
        "treatment",
        "therapy",
        "procedure",
        "condition",
        "illness",
        # Body systems
        "cardiovascular",
        "respiratory",
        "neurological",
        "gastrointestinal",
        "musculoskeletal",
        "genitourinary",
        "psychiatric",
        "endocrine",
        "hematologic",
        "dermatologic",
        # Vital signs
        "blood",
        "pressure",
        "pulse",
        "temperature",
        "respiration",
        "oxygen",
        "saturation",
        "weight",
        "height",
        "bmi",
        # Provider terms
        "physician",
        "doctor",
        "provider",
        "attending",
        "resident",
        "nurse",
        "practitioner",
        "specialist",
        "consultant",
        # History terms
        "past",
        "family",
        "social",
        "surgical",
        "allergy",
        "medication",
        "tobacco",
        "alcohol",
        "drug",
        "habit",
    },
    filename_patterns={
        "medical": 0.72,
        "history": 0.70,
        "record": 0.68,
        "consultation": 0.71,
        "consult": 0.70,
        "progress": 0.68,
        "clinical": 0.65,
        "notes": 0.65,
        "h&p": 0.71,  # History & Physical
        "soap": 0.68,  # SOAP note
        "office_visit": 0.68,
        "encounter": 0.66,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Discharge summary patterns
        r"discharge\s*(?:summary|instructions)",
        r"hospital\s*course",
        r"admission\s*date.*discharge\s*date",
        r"discharge\s*diagnosis",
        r"discharge\s*medications",
        # Immunization patterns
        r"(?:immunization|vaccination)\s*record",
        r"vaccine\s*information\s*statement",
        r"immunization\s*schedule",
        r"vaccine\s*administered",
        # Test results patterns
        r"lab\s*results?\s*report",
        r"laboratory\s*report",
        r"test\s*results?\s*summary",
        r"radiology\s*report",
        r"imaging\s*(?:report|results)",
        r"pathology\s*report",
        r"(?:mri|ct|xray|x-ray)\s*(?:report|results)",
        # Prescription patterns
        r"prescription\s*(?:label|information)",
        r"rx\s*(?:number|#)",
        r"pharmacy\s*(?:name|phone)",
        r"refills?\s*(?:remaining|left)",
        r"days?\s*supply",
        # Billing patterns
        r"(?:amount|balance)\s*due",
        r"payment\s*(?:due|required)",
        r"insurance\s*claim",
        r"billing\s*statement",
        r"invoice\s*(?:number|#)",
        r"cpt\s*code\s*\d{5}",  # Billing codes
        # EOB patterns (Financial)
        r"explanation\s*of\s*benefits",
        r"this\s*is\s*not\s*a\s*bill",
        r"patient\s*responsibility",
    },
    exclude_phrases={
        "discharge summary",
        "discharge instructions",
        "immunization record",
        "vaccination record",
        "vaccine schedule",
        "lab results",
        "test results",
        "imaging report",
        "prescription label",
        "amount due",
        "billing statement",
    },
)

# Discharge Summary - Hospital discharge documentation
DISCHARGE_SUMMARY = SubthemeRule(
    name="discharge_summary",
    display_name="Discharge Summary",
    parent_theme="Healthcare",
    subtheme_category="Medical Records",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core discharge patterns
        (r"discharge\s*summary", 0.95, "discharge_summary_header"),
        (r"discharge\s*(?:instructions|orders)", 0.93, "discharge_instructions"),
        (r"hospital\s*discharge", 0.91, "hospital_discharge"),
        (r"patient\s*discharge\s*(?:summary|report)", 0.92, "patient_discharge"),
        # Admission and discharge dates
        (r"admission\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.90, "admission_date"),
        (r"discharge\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.90, "discharge_date"),
        (
            r"date\s*of\s*admission.*date\s*of\s*discharge",
            0.89,
            "admission_discharge_dates",
        ),
        (r"length\s*of\s*stay:?\s*\d+\s*days?", 0.87, "length_of_stay"),
        # Discharge-specific sections
        (r"discharge\s*diagnosis", 0.91, "discharge_diagnosis"),
        (r"principal\s*diagnosis", 0.89, "principal_diagnosis"),
        (r"secondary\s*diagnos[ie]s", 0.88, "secondary_diagnoses"),
        (r"hospital\s*course", 0.90, "hospital_course"),
        (r"discharge\s*medications", 0.89, "discharge_medications"),
        (r"discharge\s*condition", 0.88, "discharge_condition"),
        (r"discharge\s*disposition", 0.87, "discharge_disposition"),
        # Follow-up instructions
        (
            r"follow[- ]up\s*(?:appointments?|instructions)",
            0.88,
            "followup_instructions",
        ),
        (r"discharge\s*plan", 0.87, "discharge_plan"),
        (r"activity\s*restrictions", 0.86, "activity_restrictions"),
        (r"diet\s*(?:instructions|restrictions)", 0.85, "diet_instructions"),
        # Procedures during admission
        (r"procedures?\s*performed", 0.87, "procedures_performed"),
        (r"operations?\s*performed", 0.86, "operations_performed"),
        (r"surgical\s*procedures?", 0.86, "surgical_procedures"),
    ],
    definitive_phrases={
        # Core discharge phrases
        "discharge summary": 0.95,
        "discharge instructions": 0.93,
        "hospital discharge": 0.91,
        "patient discharged": 0.90,
        "discharge report": 0.90,
        # Admission/discharge info
        "admission date": 0.89,
        "discharge date": 0.89,
        "date of admission": 0.88,
        "date of discharge": 0.88,
        "length of stay": 0.87,
        "hospital stay": 0.86,
        # Clinical course
        "hospital course": 0.91,
        "clinical course": 0.89,
        "treatment course": 0.88,
        "brief hospital course": 0.90,
        # Discharge details
        "discharge diagnosis": 0.92,
        "discharge medications": 0.90,
        "discharge condition": 0.89,
        "discharge disposition": 0.88,
        "discharge status": 0.87,
        "discharge diet": 0.86,
        # Follow-up
        "follow-up appointments": 0.88,
        "follow-up instructions": 0.88,
        "return precautions": 0.87,
        "when to return": 0.86,
        "call your doctor if": 0.85,
        # Condition at discharge
        "stable condition": 0.85,
        "improved condition": 0.85,
        "resolved": 0.84,
        "recovering well": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Discharge sections
        (r"chief\s*complaint", 0.48),
        (r"history\s*of\s*present\s*illness", 0.46),
        (r"past\s*medical\s*history", 0.44),
        (r"hospital\s*course", 0.52),
        (r"discharge\s*physical\s*exam", 0.48),
        # Clinical information
        (r"laboratory\s*(?:data|results)", 0.44),
        (r"imaging\s*(?:studies|results)", 0.42),
        (r"consultations", 0.42),
        (r"procedures", 0.44),
        # Discharge planning
        (r"discharge\s*planning", 0.46),
        (r"patient\s*education", 0.44),
        (r"home\s*care", 0.42),
        (r"rehabilitation", 0.40),
        # Medications
        (r"admission\s*medications", 0.42),
        (r"medication\s*changes", 0.44),
        (r"new\s*medications", 0.42),
        (r"discontinued\s*medications", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Discharge terms
        "discharge",
        "summary",
        "instructions",
        "hospital",
        "admission",
        "stay",
        "course",
        "disposition",
        "condition",
        "status",
        # Clinical terms
        "diagnosis",
        "treatment",
        "procedure",
        "surgery",
        "operation",
        "recovery",
        "improvement",
        "stable",
        "resolved",
        # Follow-up terms
        "follow",
        "followup",
        "appointment",
        "return",
        "precautions",
        "restrictions",
        "activity",
        "diet",
        "care",
        # Medication terms
        "medications",
        "prescriptions",
        "continue",
        "stop",
        "new",
        "changed",
        "discontinued",
        # Provider terms
        "attending",
        "physician",
        "doctor",
        "provider",
        "team",
        "service",
        "department",
        # Outcome terms
        "home",
        "facility",
        "rehabilitation",
        "skilled",
        "nursing",
        "transfer",
        "outpatient",
    },
    filename_patterns={
        "discharge": 0.75,
        "discharge_summary": 0.78,
        "hospital_discharge": 0.75,
        "discharge_instructions": 0.74,
        "summary": 0.68,
        "instructions": 0.66,
        "hospital": 0.65,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Medical history patterns
        r"past\s*medical\s*history\s*only",
        r"history\s*and\s*physical",
        r"consultation\s*report",
        r"progress\s*note",
        r"office\s*visit",
        # Immunization patterns
        r"immunization\s*record",
        r"vaccination\s*history",
        # Test result patterns
        r"lab(?:oratory)?\s*results?\s*report",
        r"imaging\s*report",
        r"radiology\s*report",
        # Prescription patterns
        r"prescription\s*label",
        r"rx\s*number",
        # Billing patterns
        r"amount\s*due",
        r"billing\s*statement",
    },
    exclude_phrases={
        "medical history",
        "consultation note",
        "progress note",
        "immunization record",
        "lab results",
        "imaging report",
        "prescription label",
        "billing statement",
    },
)

# Immunization Record - Vaccination history and immunization documentation
IMMUNIZATION_RECORD = SubthemeRule(
    name="immunization_record",
    display_name="Immunization Record",
    parent_theme="Healthcare",
    subtheme_category="Medical Records",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core immunization patterns
        (r"(?:immunization|vaccination)\s*record", 0.95, "immunization_record_header"),
        (r"(?:immunization|vaccination)\s*history", 0.93, "immunization_history"),
        (r"vaccine\s*administration\s*record", 0.92, "vaccine_admin_record"),
        (r"shot\s*record", 0.90, "shot_record"),
        (r"immunization\s*certificate", 0.91, "immunization_certificate"),
        # Vaccine-specific patterns
        (
            r"vaccine\s*(?:name|type):?\s*(?:covid|flu|tdap|mmr|hepatitis|varicella|polio)",
            0.90,
            "vaccine_type",
        ),
        (
            r"(?:pfizer|moderna|johnson|astrazeneca|novavax)",
            0.88,
            "covid_vaccine_brand",
        ),
        (r"(?:dose|shot)\s*(?:#?\d+|first|second|third|booster)", 0.89, "vaccine_dose"),
        (r"vaccine\s*lot\s*(?:number|#):?\s*[A-Z0-9\-]{4,}", 0.87, "vaccine_lot"),
        (
            r"manufacturer:?\s*(?:pfizer|moderna|merck|gsk|sanofi)",
            0.86,
            "vaccine_manufacturer",
        ),
        # Administration details
        (
            r"date\s*(?:given|administered):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.89,
            "administration_date",
        ),
        (r"site:?\s*(?:left|right)\s*(?:arm|thigh|deltoid)", 0.85, "injection_site"),
        (
            r"route:?\s*(?:im|sq|subq|intramuscular|subcutaneous)",
            0.85,
            "administration_route",
        ),
        (r"administered\s*by:?\s*", 0.84, "administrator"),
        # Immunization schedule patterns
        (r"immunization\s*schedule", 0.88, "immunization_schedule"),
        (r"next\s*dose\s*due:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.86, "next_dose_due"),
        (r"series\s*(?:complete|incomplete)", 0.87, "series_status"),
        # VIS and compliance
        (r"vaccine\s*information\s*statement", 0.88, "vis_statement"),
        (r"vis\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.86, "vis_date"),
        (
            r"(?:school|travel)\s*immunization\s*requirements?",
            0.85,
            "immunization_requirements",
        ),
    ],
    definitive_phrases={
        # Core immunization phrases
        "immunization record": 0.95,
        "vaccination record": 0.94,
        "immunization history": 0.93,
        "vaccination history": 0.92,
        "shot record": 0.91,
        "vaccine record": 0.91,
        "immunization certificate": 0.92,
        # Vaccine types
        "covid-19 vaccine": 0.90,
        "influenza vaccine": 0.89,
        "flu shot": 0.88,
        "tdap vaccine": 0.88,
        "mmr vaccine": 0.88,
        "hepatitis vaccine": 0.88,
        "varicella vaccine": 0.87,
        "polio vaccine": 0.87,
        "pneumococcal vaccine": 0.87,
        "meningococcal vaccine": 0.87,
        # Administration phrases
        "vaccine administered": 0.90,
        "date administered": 0.88,
        "vaccine given": 0.87,
        "immunization given": 0.87,
        "dose administered": 0.86,
        # Schedule phrases
        "immunization schedule": 0.89,
        "vaccine schedule": 0.88,
        "up to date": 0.86,
        "fully vaccinated": 0.87,
        "series complete": 0.87,
        "booster due": 0.85,
        # Compliance phrases
        "vaccine information statement": 0.89,
        "vis provided": 0.87,
        "consent obtained": 0.85,
        "school requirements": 0.85,
        "travel vaccines": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Vaccine information
        (r"vaccine\s*name", 0.50),
        (r"vaccine\s*type", 0.48),
        (r"manufacturer", 0.46),
        (r"lot\s*number", 0.44),
        (r"expiration\s*date", 0.42),
        # Administration details
        (r"date\s*given", 0.48),
        (r"site", 0.44),
        (r"route", 0.42),
        (r"dose\s*(?:number|#)", 0.46),
        (r"administered\s*by", 0.42),
        # Patient information
        (r"patient\s*name", 0.44),
        (r"date\s*of\s*birth", 0.42),
        (r"age", 0.40),
        # Schedule information
        (r"next\s*dose", 0.44),
        (r"due\s*date", 0.42),
        (r"series\s*status", 0.42),
        # Documentation
        (r"vis\s*date", 0.40),
        (r"clinic\s*name", 0.38),
        (r"provider\s*signature", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Immunization terms
        "immunization",
        "vaccination",
        "vaccine",
        "shot",
        "injection",
        "inoculation",
        "immunity",
        "immunize",
        "vaccinate",
        # Vaccine names
        "covid",
        "flu",
        "influenza",
        "tdap",
        "dtap",
        "mmr",
        "hepatitis",
        "varicella",
        "chickenpox",
        "polio",
        "hpv",
        "pneumococcal",
        "meningococcal",
        "rotavirus",
        "hib",
        "pcv",
        "ipv",
        # Dose terms
        "dose",
        "booster",
        "series",
        "primary",
        "initial",
        "final",
        "first",
        "second",
        "third",
        "annual",
        "seasonal",
        # Administration terms
        "administered",
        "given",
        "received",
        "date",
        "site",
        "route",
        "lot",
        "manufacturer",
        "expiration",
        # Compliance terms
        "schedule",
        "requirements",
        "school",
        "travel",
        "mandatory",
        "recommended",
        "optional",
        "contraindication",
        "exemption",
        # Status terms
        "complete",
        "incomplete",
        "current",
        "overdue",
        "due",
        "up-to-date",
        "behind",
        "catch-up",
    },
    filename_patterns={
        "immunization": 0.78,
        "vaccination": 0.78,
        "vaccine": 0.75,
        "shot": 0.72,
        "shot_record": 0.75,
        "imm_record": 0.74,
        "vax": 0.70,
        "covid_card": 0.72,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Medical history patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"review\s*of\s*systems",
        r"physical\s*exam",
        r"assessment\s*and\s*plan",
        # Discharge patterns
        r"discharge\s*summary",
        r"hospital\s*course",
        # Test result patterns
        r"lab(?:oratory)?\s*results?",
        r"test\s*results?",
        # Prescription patterns
        r"prescription\s*label",
        r"rx\s*number",
        # Billing patterns
        r"amount\s*due",
        r"billing\s*statement",
    },
    exclude_phrases={
        "medical history",
        "discharge summary",
        "consultation report",
        "progress note",
        "lab results",
        "prescription label",
        "billing statement",
    },
)


# Export rules
MEDICAL_RECORDS_SUBTHEME_RULES: List[SubthemeRule] = [
    MEDICAL_HISTORY,
    DISCHARGE_SUMMARY,
    IMMUNIZATION_RECORD,
]

MEDICAL_RECORDS_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in MEDICAL_RECORDS_SUBTHEME_RULES
}
