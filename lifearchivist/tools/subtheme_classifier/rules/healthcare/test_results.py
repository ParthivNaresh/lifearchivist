"""
Healthcare > Test Results subtheme rules.

Defines precise, production-ready patterns for:
- Lab Results
- Imaging Report
- Diagnostic Test

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Lab Results - Laboratory test results and reports
LAB_RESULTS = SubthemeRule(
    name="lab_results",
    display_name="Lab Results",
    parent_theme="Healthcare",
    subtheme_category="Test Results",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core laboratory result patterns
        (
            r"lab(?:oratory)?\s*results?\s*(?:report|summary)",
            0.95,
            "lab_results_header",
        ),
        (r"specimen\s*(?:id|number|#):?\s*[A-Z0-9\-]{4,}", 0.92, "specimen_identifier"),
        (r"accession\s*(?:number|#):?\s*[A-Z0-9\-]{4,}", 0.91, "accession_number"),
        (
            r"collection\s*(?:date|time):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.89,
            "collection_date",
        ),
        (r"reference\s*range:?\s*[\d\.\-\s]+", 0.88, "reference_range"),
        (r"(?:abnormal|critical)\s*(?:value|result|flag)", 0.90, "abnormal_flag"),
        # Common lab test patterns with values
        (
            r"(?:wbc|white\s*blood\s*cells?):?\s*[\d\.,]+\s*(?:k/ul|cells)",
            0.87,
            "wbc_result",
        ),
        (
            r"(?:rbc|red\s*blood\s*cells?):?\s*[\d\.,]+\s*(?:m/ul|cells)",
            0.87,
            "rbc_result",
        ),
        (r"(?:hemoglobin|hgb):?\s*[\d\.,]+\s*(?:g/dl)?", 0.87, "hemoglobin_result"),
        (r"(?:hematocrit|hct):?\s*[\d\.,]+\s*%?", 0.86, "hematocrit_result"),
        (r"(?:platelet|plt):?\s*[\d\.,]+\s*(?:k/ul)?", 0.86, "platelet_result"),
        (
            r"(?:glucose|blood\s*sugar):?\s*[\d\.,]+\s*(?:mg/dl)?",
            0.87,
            "glucose_result",
        ),
        (r"(?:creatinine|creat):?\s*[\d\.,]+\s*(?:mg/dl)?", 0.86, "creatinine_result"),
        (
            r"(?:cholesterol|ldl|hdl):?\s*[\d\.,]+\s*(?:mg/dl)?",
            0.86,
            "cholesterol_result",
        ),
        # Lab-specific patterns
        (
            r"(?:sodium|potassium|chloride|co2):?\s*[\d\.,]+\s*(?:mmol/l|meq/l)?",
            0.85,
            "electrolyte_result",
        ),
        (
            r"(?:ast|alt|alkaline\s*phosphatase):?\s*[\d\.,]+\s*(?:u/l|iu/l)?",
            0.85,
            "liver_enzyme",
        ),
        (r"(?:tsh|t3|t4):?\s*[\d\.,]+", 0.85, "thyroid_test"),
        # Pathology patterns specific to lab reports
        (r"pathology\s*report", 0.93, "pathology_report"),
        (r"(?:biopsy|cytology)\s*(?:report|results)", 0.91, "biopsy_report"),
        (r"microscopic\s*(?:description|examination)", 0.88, "microscopic_exam"),
        (
            r"(?:malignant|benign|atypical)\s*(?:cells|tissue)",
            0.87,
            "pathology_finding",
        ),
        # LOINC codes for lab tests
        (r"loinc:?\s*\d{4,5}-\d", 0.86, "loinc_code"),
    ],
    definitive_phrases={
        # Core laboratory phrases
        "laboratory results": 0.95,
        "lab report": 0.93,
        "test results": 0.89,
        "specimen collected": 0.87,
        "reference range": 0.86,
        "normal range": 0.85,
        "out of range": 0.86,
        "critical value": 0.89,
        "panic value": 0.88,
        # Common lab panels
        "complete blood count": 0.91,
        "cbc with differential": 0.91,
        "basic metabolic panel": 0.91,
        "comprehensive metabolic panel": 0.91,
        "lipid panel": 0.89,
        "liver function test": 0.89,
        "thyroid panel": 0.89,
        "urinalysis": 0.88,
        "blood culture": 0.88,
        "urine culture": 0.87,
        # Lab-specific phrases
        "specimen type": 0.86,
        "performing laboratory": 0.85,
        "test methodology": 0.84,
        "quality control": 0.83,
        # Pathology phrases
        "pathology report": 0.93,
        "microscopic examination": 0.89,
        "gross description": 0.87,
        "histologic diagnosis": 0.89,
        "immunohistochemistry": 0.86,
        "special stains": 0.85,
        "tumor markers": 0.85,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Lab result structure
        (r"test\s*name", 0.52),
        (r"result\s*value", 0.50),
        (r"units", 0.47),
        (r"flag", 0.45),
        (r"performing\s*lab", 0.42),
        (r"ordering\s*provider", 0.42),
        # Lab-specific structure
        (r"specimen\s*type", 0.45),
        (r"collection\s*method", 0.42),
        (r"fasting\s*status", 0.40),
        (r"test\s*methodology", 0.40),
        # Result interpretation
        (r"interpretation", 0.47),
        (r"clinical\s*significance", 0.44),
        (r"comment", 0.40),
        # Quality indicators
        (r"verified\s*by", 0.40),
        (r"electronically\s*signed", 0.37),
        (r"amended\s*report", 0.37),
        (r"corrected\s*report", 0.37),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Core lab terms
        "lab",
        "laboratory",
        "test",
        "result",
        "report",
        "specimen",
        "pathology",
        "biopsy",
        "cytology",
        "culture",
        # Lab components
        "blood",
        "urine",
        "serum",
        "plasma",
        "tissue",
        "fluid",
        "stool",
        "sputum",
        "csf",
        "synovial",
        # Blood tests
        "cbc",
        "wbc",
        "rbc",
        "hemoglobin",
        "hematocrit",
        "platelet",
        "neutrophil",
        "lymphocyte",
        "monocyte",
        "eosinophil",
        "basophil",
        # Chemistry tests
        "glucose",
        "cholesterol",
        "triglyceride",
        "ldl",
        "hdl",
        "sodium",
        "potassium",
        "chloride",
        "bicarbonate",
        "creatinine",
        "bun",
        "urea",
        "bilirubin",
        "enzyme",
        "protein",
        "albumin",
        # Other common tests
        "thyroid",
        "tsh",
        "vitamin",
        "iron",
        "ferritin",
        "b12",
        "folate",
        "psa",
        "cea",
        "afp",
        "hcg",
        "troponin",
        "bnp",
        # Result descriptors
        "normal",
        "abnormal",
        "high",
        "low",
        "positive",
        "negative",
        "elevated",
        "decreased",
        "within",
        "range",
        "critical",
        "panic",
        # Units
        "mg/dl",
        "g/dl",
        "mmol/l",
        "meq/l",
        "iu/l",
        "u/l",
        "ng/ml",
        "pg/ml",
        "mcg",
        "cells/ul",
        "k/ul",
        "m/ul",
    },
    filename_patterns={
        "lab": 0.75,
        "laboratory": 0.75,
        "blood": 0.70,
        "urine": 0.70,
        "test": 0.68,
        "result": 0.70,
        "pathology": 0.73,
        "biopsy": 0.72,
        "culture": 0.70,
        "panel": 0.68,
        "cbc": 0.70,
        "metabolic": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Imaging report patterns
        r"(?:radiology|imaging)\s*report",
        r"(?:mri|ct|xray|x-ray|ultrasound)\s*(?:report|results)",
        r"impression:?\s*.{10,}",
        r"findings:?\s*.{10,}",
        r"contrast\s*(?:enhanced|administration)",
        # Diagnostic test patterns
        r"(?:ekg|ecg|electrocardiogram)\s*(?:report|results)",
        r"(?:eeg|electroencephalogram)\s*(?:report|results)",
        r"stress\s*test\s*(?:report|results)",
        r"pulmonary\s*function\s*test",
        r"echocardiogram\s*(?:report|results)",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"review\s*of\s*systems",
        r"physical\s*exam(?:ination)?",
        r"assessment\s*(?:and|&)\s*plan",
        r"discharge\s*(?:summary|instructions)",
        r"progress\s*note",
        # Prescription patterns
        r"prescription\s*(?:label|information)",
        r"directions?\s*for\s*use",
        r"take\s*\d+\s*(?:tablet|capsule|pill)",
        r"refills?\s*(?:remaining|left)",
        r"pharmacy\s*(?:name|phone)",
        # Billing patterns
        r"(?:amount|balance)\s*due",
        r"payment\s*(?:due|required)",
        r"insurance\s*claim",
        r"billing\s*(?:statement|invoice)",
        r"procedure\s*code\s*\d{5}",  # CPT codes for billing
        # Administrative patterns
        r"authorization\s*(?:number|required)",
        r"prior\s*authorization",
        r"referral\s*(?:form|required)",
    },
    exclude_phrases={
        "imaging report",
        "radiology report",
        "xray report",
        "mri report",
        "ct report",
        "ekg report",
        "ecg report",
        "stress test",
        "medical history",
        "clinical notes",
        "prescription label",
        "medication list",
        "amount due",
        "billing statement",
    },
)

# Imaging Report - Radiology and imaging study reports
IMAGING_REPORT = SubthemeRule(
    name="imaging_report",
    display_name="Imaging Report",
    parent_theme="Healthcare",
    subtheme_category="Test Results",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core imaging report patterns
        (r"(?:radiology|imaging)\s*report", 0.94, "imaging_report_header"),
        (r"radiological\s*(?:examination|study)", 0.91, "radiological_exam"),
        (r"imaging\s*study\s*(?:report|results)", 0.90, "imaging_study"),
        # Specific imaging modalities
        (
            r"(?:mri|magnetic\s*resonance\s*imaging)\s*(?:report|results|study)",
            0.93,
            "mri_report",
        ),
        (
            r"(?:ct|computed\s*tomography|cat\s*scan)\s*(?:report|results|study)",
            0.93,
            "ct_report",
        ),
        (
            r"(?:x-?ray|radiograph)\s*(?:report|results|examination)",
            0.92,
            "xray_report",
        ),
        (
            r"(?:ultrasound|sonogram|sonography)\s*(?:report|results|study)",
            0.92,
            "ultrasound_report",
        ),
        (
            r"(?:pet|positron\s*emission\s*tomography)\s*(?:scan|report)",
            0.91,
            "pet_scan",
        ),
        (r"(?:dexa|bone\s*density)\s*(?:scan|report)", 0.90, "dexa_scan"),
        (r"(?:mammogram|mammography)\s*(?:report|results)", 0.91, "mammogram"),
        (r"fluoroscopy\s*(?:report|study)", 0.89, "fluoroscopy"),
        # Key imaging sections
        (r"impression:?\s*.{10,}", 0.90, "imaging_impression"),
        (r"findings:?\s*.{10,}", 0.89, "imaging_findings"),
        (r"clinical\s*indication:?\s*.{5,}", 0.87, "clinical_indication"),
        (r"comparison:?\s*(?:prior|previous|none)", 0.86, "comparison_study"),
        (r"technique:?\s*.{5,}", 0.85, "imaging_technique"),
        # Contrast and technical details
        (r"contrast\s*(?:enhanced|administration|material)", 0.87, "contrast_used"),
        (r"(?:with|without)\s*(?:iv|oral|rectal)\s*contrast", 0.86, "contrast_type"),
        (r"slice\s*thickness:?\s*\d+\s*mm", 0.85, "slice_thickness"),
        (r"field\s*strength:?\s*\d+\.?\d*\s*(?:t|tesla)", 0.85, "mri_field_strength"),
    ],
    definitive_phrases={
        # Core imaging phrases
        "radiology report": 0.94,
        "imaging report": 0.92,
        "imaging study": 0.89,
        "radiological examination": 0.89,
        "diagnostic imaging": 0.88,
        # Modality-specific phrases
        "mri report": 0.93,
        "ct report": 0.93,
        "xray report": 0.92,
        "ultrasound report": 0.92,
        "pet scan": 0.91,
        "bone density scan": 0.90,
        "mammography report": 0.91,
        # Technical phrases
        "contrast enhanced": 0.86,
        "contrast material": 0.85,
        "iv contrast": 0.85,
        "oral contrast": 0.84,
        "comparison study": 0.85,
        "prior examination": 0.84,
        # Findings phrases
        "no acute findings": 0.86,
        "unremarkable study": 0.85,
        "normal appearance": 0.84,
        "abnormal finding": 0.85,
        "incidental finding": 0.84,
        # Anatomical references
        "visualized portions": 0.83,
        "limited examination": 0.82,
        "technically adequate": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Report structure
        (r"clinical\s*history", 0.48),
        (r"indication\s*for\s*study", 0.46),
        (r"comparison", 0.44),
        (r"technique", 0.42),
        (r"contrast", 0.40),
        # Findings structure
        (r"findings", 0.50),
        (r"impression", 0.48),
        (r"recommendation", 0.44),
        (r"conclusion", 0.42),
        # Technical details
        (r"protocol", 0.40),
        (r"sequences", 0.38),  # MRI specific
        (r"views", 0.38),  # X-ray specific
        (r"images", 0.36),
        # Quality and limitations
        (r"image\s*quality", 0.38),
        (r"motion\s*artifact", 0.36),
        (r"limited\s*by", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Imaging types
        "radiology",
        "imaging",
        "xray",
        "radiograph",
        "mri",
        "magnetic",
        "ct",
        "computed",
        "tomography",
        "cat",
        "scan",
        "ultrasound",
        "sonogram",
        "echo",
        "pet",
        "dexa",
        "mammogram",
        "fluoroscopy",
        # Anatomical terms
        "chest",
        "abdomen",
        "pelvis",
        "head",
        "brain",
        "spine",
        "extremity",
        "joint",
        "bone",
        "lung",
        "liver",
        "kidney",
        # Findings terms
        "impression",
        "findings",
        "normal",
        "abnormal",
        "unremarkable",
        "lesion",
        "mass",
        "nodule",
        "opacity",
        "density",
        "enhancement",
        "signal",
        "intensity",
        "attenuation",
        "artifact",
        # Technical terms
        "contrast",
        "sagittal",
        "coronal",
        "axial",
        "lateral",
        "ap",
        "portable",
        "bilateral",
        "unilateral",
        "comparison",
        "prior",
        # Descriptive terms
        "acute",
        "chronic",
        "stable",
        "interval",
        "change",
        "new",
        "resolved",
        "persistent",
        "suspicious",
        "benign",
        "malignant",
    },
    filename_patterns={
        "imaging": 0.73,
        "radiology": 0.73,
        "xray": 0.72,
        "x-ray": 0.72,
        "mri": 0.74,
        "ct": 0.72,
        "scan": 0.70,
        "ultrasound": 0.71,
        "mammogram": 0.72,
        "pet": 0.71,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lab result patterns
        r"lab(?:oratory)?\s*results?\s*report",
        r"specimen\s*(?:id|number)",
        r"reference\s*range",
        r"(?:wbc|rbc|hemoglobin|glucose|cholesterol):?\s*[\d\.,]+",
        # Diagnostic test patterns
        r"(?:ekg|ecg|electrocardiogram)\s*(?:report|results)",
        r"(?:eeg|electroencephalogram)\s*(?:report|results)",
        r"stress\s*test\s*results",
        r"pulmonary\s*function\s*test",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"physical\s*exam",
        # Prescription patterns
        r"rx\s*number",
        r"refills?\s*remaining",
        # Billing patterns
        r"amount\s*due",
        r"payment\s*required",
    },
    exclude_phrases={
        "lab results",
        "laboratory report",
        "blood test",
        "urine test",
        "ekg report",
        "stress test",
        "medical history",
        "prescription label",
        "amount due",
    },
)

# Diagnostic Test - Specialized diagnostic test reports (EKG, EEG, stress tests, etc.)
DIAGNOSTIC_TEST = SubthemeRule(
    name="diagnostic_test",
    display_name="Diagnostic Test",
    parent_theme="Healthcare",
    subtheme_category="Test Results",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Cardiac diagnostic tests
        (
            r"(?:ekg|ecg|electrocardiogram)\s*(?:report|results|tracing)",
            0.93,
            "ekg_report",
        ),
        (r"(?:12-lead|12\s*lead)\s*(?:ekg|ecg)", 0.91, "12_lead_ekg"),
        (
            r"(?:stress\s*test|treadmill\s*test|exercise\s*test)\s*(?:report|results)",
            0.91,
            "stress_test",
        ),
        (
            r"(?:echo|echocardiogram|echocardiography)\s*(?:report|results)",
            0.91,
            "echocardiogram",
        ),
        (
            r"(?:holter|24-?hour)\s*monitor(?:ing)?\s*(?:report|results)",
            0.90,
            "holter_monitor",
        ),
        (r"cardiac\s*catheterization\s*(?:report|results)", 0.89, "cardiac_cath"),
        # Neurological diagnostic tests
        (
            r"(?:eeg|electroencephalogram|electroencephalography)\s*(?:report|results)",
            0.92,
            "eeg_report",
        ),
        (
            r"(?:emg|electromyography|nerve\s*conduction)\s*(?:study|report)",
            0.91,
            "emg_study",
        ),
        (r"(?:vng|videonystagmography)\s*(?:test|report)", 0.89, "vng_test"),
        (
            r"(?:evoked\s*potential|vep|baer)\s*(?:study|report)",
            0.88,
            "evoked_potential",
        ),
        # Pulmonary diagnostic tests
        (
            r"(?:pulmonary\s*function|spirometry|pft)\s*(?:test|results)",
            0.91,
            "pulmonary_function",
        ),
        (
            r"(?:sleep\s*study|polysomnography)\s*(?:report|results)",
            0.90,
            "sleep_study",
        ),
        (
            r"(?:abg|arterial\s*blood\s*gas)\s*(?:analysis|results)",
            0.89,
            "abg_analysis",
        ),
        # Cardiac-specific patterns
        (r"(?:normal\s*sinus\s*rhythm|nsr)", 0.88, "normal_rhythm"),
        (r"(?:pr|qrs|qt)\s*interval:?\s*\d+\s*ms", 0.87, "cardiac_intervals"),
        (r"(?:heart\s*rate|hr):?\s*\d+\s*(?:bpm|beats)", 0.86, "heart_rate"),
        (r"ejection\s*fraction:?\s*\d+%", 0.87, "ejection_fraction"),
        # Pulmonary-specific patterns
        (r"(?:fev1|fvc|fev1/fvc):?\s*\d+", 0.87, "spirometry_values"),
        (r"(?:dlco|diffusion\s*capacity):?\s*\d+", 0.86, "diffusion_capacity"),
    ],
    definitive_phrases={
        # Cardiac test phrases
        "electrocardiogram report": 0.93,
        "ekg report": 0.92,
        "ecg report": 0.92,
        "stress test results": 0.91,
        "exercise tolerance test": 0.90,
        "treadmill test": 0.89,
        "echocardiogram report": 0.91,
        "holter monitor": 0.90,
        "cardiac catheterization": 0.89,
        # Cardiac findings
        "normal sinus rhythm": 0.88,
        "sinus bradycardia": 0.87,
        "sinus tachycardia": 0.87,
        "atrial fibrillation": 0.87,
        "st elevation": 0.86,
        "qt prolongation": 0.86,
        # Neurological test phrases
        "eeg report": 0.92,
        "electroencephalogram": 0.91,
        "emg study": 0.91,
        "nerve conduction study": 0.90,
        "evoked potential": 0.88,
        # Pulmonary test phrases
        "pulmonary function test": 0.91,
        "spirometry results": 0.90,
        "lung function test": 0.89,
        "sleep study report": 0.90,
        "polysomnography": 0.89,
        "arterial blood gas": 0.89,
        # Test quality phrases
        "technically adequate": 0.84,
        "good effort": 0.83,
        "reproducible": 0.83,
        "baseline study": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Test information
        (r"test\s*date", 0.48),
        (r"indication", 0.46),
        (r"referring\s*physician", 0.44),
        (r"technician", 0.40),
        # Cardiac patterns
        (r"rate", 0.42),
        (r"rhythm", 0.42),
        (r"axis", 0.40),
        (r"intervals", 0.40),
        (r"voltage", 0.38),
        # Pulmonary patterns
        (r"predicted", 0.42),
        (r"actual", 0.42),
        (r"percent\s*predicted", 0.40),
        # Interpretation
        (r"interpretation", 0.46),
        (r"conclusion", 0.44),
        (r"clinical\s*correlation", 0.42),
        (r"comparison\s*with\s*prior", 0.40),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Cardiac terms
        "ekg",
        "ecg",
        "electrocardiogram",
        "cardiac",
        "heart",
        "rhythm",
        "rate",
        "interval",
        "wave",
        "segment",
        "axis",
        "voltage",
        "stress",
        "treadmill",
        "exercise",
        "echo",
        "echocardiogram",
        "holter",
        "monitor",
        "catheterization",
        # Neurological terms
        "eeg",
        "electroencephalogram",
        "brain",
        "seizure",
        "epileptiform",
        "emg",
        "nerve",
        "conduction",
        "muscle",
        # Pulmonary terms
        "pulmonary",
        "lung",
        "spirometry",
        "fev1",
        "fvc",
        "pef",
        "dlco",
        "diffusion",
        "capacity",
        "sleep",
        "apnea",
        "oxygen",
        # Common findings
        "normal",
        "abnormal",
        "borderline",
        "mild",
        "moderate",
        "severe",
        "acute",
        "chronic",
        "stable",
        "improved",
        "worsened",
        # Technical terms
        "lead",
        "tracing",
        "waveform",
        "amplitude",
        "duration",
        "latency",
        "velocity",
        "flow",
        "volume",
        "resistance",
    },
    filename_patterns={
        "ekg": 0.74,
        "ecg": 0.74,
        "electrocardiogram": 0.73,
        "stress_test": 0.72,
        "echo": 0.71,
        "eeg": 0.73,
        "emg": 0.72,
        "pulmonary": 0.71,
        "spirometry": 0.71,
        "sleep_study": 0.71,
        "diagnostic": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lab result patterns
        r"lab(?:oratory)?\s*results?\s*report",
        r"specimen\s*(?:id|number)",
        r"reference\s*range",
        r"(?:wbc|rbc|hemoglobin|glucose|cholesterol):?\s*[\d\.,]+",
        # Imaging patterns
        r"(?:radiology|imaging)\s*report",
        r"(?:mri|ct|xray)\s*(?:report|results)",
        r"impression:?\s*.{10,}",
        r"contrast\s*enhanced",
        # Medical record patterns
        r"chief\s*complaint",
        r"history\s*of\s*present\s*illness",
        r"physical\s*exam",
        # Prescription patterns
        r"rx\s*number",
        r"refills?\s*remaining",
        # Billing patterns
        r"amount\s*due",
        r"payment\s*required",
    },
    exclude_phrases={
        "lab results",
        "laboratory report",
        "imaging report",
        "radiology report",
        "xray report",
        "mri report",
        "ct report",
        "medical history",
        "prescription label",
        "amount due",
    },
)


# Export rules
TEST_RESULTS_SUBTHEME_RULES: List[SubthemeRule] = [
    LAB_RESULTS,
    IMAGING_REPORT,
    DIAGNOSTIC_TEST,
]

TEST_RESULTS_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in TEST_RESULTS_SUBTHEME_RULES
}
