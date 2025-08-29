"""
Date extraction utilities and constants for document date parsing.
"""

from datetime import datetime
from typing import Optional

from lifearchivist.utils.logging import log_event

SUPPORTED_DATE_FORMATS = [
    "%Y-%m-%d",  # 2024-01-15 (ISO format - preferred by LLM)
    "%B %d, %Y",  # January 15, 2024
    "%B %d %Y",  # January 15 2024
    "%b %d, %Y",  # Jan 15, 2024
    "%b %d %Y",  # Jan 15 2024
    "%m/%d/%Y",  # 01/15/2024
    "%m/%d/%y",  # 01/15/24
    "%d/%m/%Y",  # 15/01/2024 (European format)
]


DATE_EXTRACTION_PROMPT_TEMPLATE = """You are a document date extraction expert. Your goal is to find the PRIMARY DATE when this document was created, issued, or sent out. This is typically found at the top of the document.

WHAT TO LOOK FOR:
1. **Statement Date** - When the statement/bill was issued
2. **Document Date** - When the document was created/printed
3. **Issue Date** - When the document was sent out
4. **Report Date** - When the report was generated (for test results, reports)
5. **Payroll Date** - When the paycheck/paystub was issued or sent
6. **Account Statement Date** - The ending date range for the account statement time period

PRIORITY ORDER (look for the FIRST/HIGHEST priority date you can find):
1. Statement Date, Issue Date, Document Date (TOP PRIORITY)
2. Report Date, Test Date, Generated Date
3. Closing Date, As of Date (for account statements)
4. Creation Date, Print Date

IGNORE these dates:
- Service periods ("January 1 - 31, 2022" coverage periods)
- Due dates ("Payment due by...")  
- Transaction dates (individual purchases/payments)
- Appointment dates within the document content

DOCUMENT TEXT:
{text}

FIND THE MAIN DOCUMENT DATE - typically near the top of the document.

EXAMPLES:
- "Statement Date: March 29, 2022" → date: "2022-03-29"
- "Report Date: 05/26/2022" → date: "2022-05-26"  
- "Issued: February 15, 2022" → date: "2022-02-15"
- "Lab Results - Date: 01/28/2022" → date: "2022-01-28"

Return ONLY ONE DATE - the primary document creation/issue date. Do this without any additional commentary.

DATE OUTPUT:"""


def create_date_extraction_prompt(text: str) -> str:
    """
    Create a comprehensive prompt for LLM-based date extraction.

    Args:
        text: Document text content to analyze

    Returns:
        Formatted prompt for LLM date extraction
    """
    return DATE_EXTRACTION_PROMPT_TEMPLATE.format(text=text)


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse various date string formats into datetime objects.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object or None if parsing fails
    """
    date_str = date_str.strip()

    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            log_event(
                "date_parsing_successful",
                {
                    "input_date": date_str,
                    "format_used": fmt,
                    "parsed_date": parsed_date.isoformat(),
                },
            )
            return parsed_date
        except ValueError:
            continue

    log_event(
        "date_parsing_failed",
        {"input_date": date_str, "formats_attempted": len(SUPPORTED_DATE_FORMATS)},
    )
    return None


def truncate_text_for_llm(
    text: str, max_chars: int = 10000, document_id: Optional[str] = None
) -> str:
    """
    Truncate text to avoid LLM token limits while preserving beginning content.

    Args:
        text: Text content to potentially truncate
        max_chars: Maximum character limit
        document_id: Optional document ID for logging

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_chars:
        return text

    truncated_text = text[:max_chars] + "..."

    log_event(
        "text_truncated_for_llm",
        {
            "document_id": document_id,
            "original_length": len(text),
            "truncated_length": len(truncated_text),
            "max_chars": max_chars,
        },
    )

    return truncated_text
