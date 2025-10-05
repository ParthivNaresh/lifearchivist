SECONDARY_STRUCTURE_PATTERN_DEFINITIONS = {
    "Financial": [
        (r"beginning\s+balance.*?ending\s+balance", 0.8),
        (r"account\s+(?:number|#):\s*[\d\-]+", 0.6),
        (r"(?:total\s+)?(?:amount\s+)?due:?\s*\$?[\d,]+\.?\d*", 0.5),
        (r"apr:?\s*\d+\.?\d*%?", 0.7),
    ],
    "Healthcare": [
        (r"patient\s+(?:name|id):", 0.8),
        (r"date\s+of\s+(?:service|birth):", 0.7),
        (r"diagnosis\s+(?:code|description):", 0.8),
        (r"provider\s+(?:name|id):", 0.7),
    ],
    "Legal": [
        (r"\bwhereas\b.*?\btherefore\b", 0.9),
        (r"party\s+of\s+the\s+first\s+part", 0.8),
        (r"governing\s+law", 0.7),
        (r"section\s+\d+\.\d+", 0.5),
    ],
    "Professional": [
        (r"education\s*:.*?(?:bachelor|master|phd)", 0.8),
        (r"experience\s*:.*?years?", 0.7),
        (r"skills?\s*:.*?(?:\n|$)", 0.6),
        (r"references?\s+(?:available|upon\s+request)", 0.7),
    ],
}
