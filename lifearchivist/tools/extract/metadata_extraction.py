"""
Document metadata extraction utilities.

Extracts internal metadata from various document formats including:
- PDF: Creation date, modification date, author, title, etc.
- DOCX: Core properties including creation/modification dates
- XLSX: Workbook properties
- Images: EXIF data
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from docx import Document
from openpyxl import load_workbook
from PIL import Image
from pypdf import PdfReader

from lifearchivist.utils.logging import log_event


def parse_pdf_date(pdf_date_string: Optional[str]) -> Optional[str]:
    """
    Parse PDF date format to ISO 8601.

    PDF dates are in format: D:YYYYMMDDHHmmSSOHH'mm'
    Example: D:20240115103045-05'00' → 2024-01-15T10:30:45-05:00

    Args:
        pdf_date_string: PDF date string or None

    Returns:
        ISO 8601 formatted date string or None
    """
    if not pdf_date_string:
        return None

    try:
        # Remove 'D:' prefix if present
        date_str = pdf_date_string.strip()
        if date_str.startswith("D:"):
            date_str = date_str[2:]

        # Extract components
        # Format: YYYYMMDDHHmmSSOHH'mm' or YYYYMMDDHHmmSS
        if len(date_str) < 14:
            return None

        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hour = int(date_str[8:10])
        minute = int(date_str[10:12])
        second = int(date_str[12:14])

        # Create datetime object
        dt = datetime(year, month, day, hour, minute, second)

        # Handle timezone if present
        if len(date_str) > 14:
            tz_part = date_str[14:]
            # Parse timezone offset (e.g., "-05'00'" or "+00'00'")
            if tz_part and tz_part[0] in ["+", "-"]:
                try:
                    tz_sign = tz_part[0]
                    tz_hours = int(tz_part[1:3])
                    # Some PDFs have minutes after apostrophe
                    tz_minutes = 0
                    if "'" in tz_part:
                        tz_minutes = int(tz_part.split("'")[1][:2])

                    # Format timezone
                    tz_str = f"{tz_sign}{tz_hours:02d}:{tz_minutes:02d}"
                    return dt.isoformat() + tz_str
                except (ValueError, IndexError):
                    pass

        return dt.isoformat()

    except (ValueError, IndexError) as e:
        log_event(
            "pdf_date_parse_failed",
            {"pdf_date": pdf_date_string, "error": str(e)},
            level=logging.DEBUG,
        )
        return None


async def extract_pdf_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from PDF files.

    Extracts:
    - Creation date (/CreationDate)
    - Modification date (/ModDate)
    - Author (/Author)
    - Title (/Title)
    - Subject (/Subject)
    - Keywords (/Keywords)
    - Producer (/Producer)
    - Creator (/Creator)

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with extracted metadata
    """
    try:
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            pdf_metadata = reader.metadata

            if not pdf_metadata:
                log_event(
                    "pdf_metadata_empty", {"file": file_path.name}, level=logging.DEBUG
                )
                return {}

            # Extract and parse metadata
            metadata = {}

            # Dates
            if "/CreationDate" in pdf_metadata:
                created = parse_pdf_date(pdf_metadata["/CreationDate"])
                if created:
                    metadata["document_created_at"] = created

            if "/ModDate" in pdf_metadata:
                modified = parse_pdf_date(pdf_metadata["/ModDate"])
                if modified:
                    metadata["document_modified_at"] = modified

            # Text fields
            text_fields = {
                "/Author": "document_author",
                "/Title": "document_title",
                "/Subject": "document_subject",
                "/Keywords": "document_keywords",
                "/Producer": "document_producer",
                "/Creator": "document_creator",
            }

            for pdf_key, metadata_key in text_fields.items():
                if pdf_key in pdf_metadata:
                    value = pdf_metadata[pdf_key]
                    if value and isinstance(value, str):
                        metadata[metadata_key] = value.strip()

            # Log successful extraction
            if metadata:
                log_event(
                    "pdf_metadata_extracted",
                    {
                        "file": file_path.name,
                        "fields_extracted": list(metadata.keys()),
                        "has_creation_date": "document_created_at" in metadata,
                    },
                    level=logging.DEBUG,
                )

            return metadata

    except Exception as e:
        log_event(
            "pdf_metadata_extraction_failed",
            {"file": file_path.name, "error": str(e)},
            level=logging.WARNING,
        )
        return {}


async def extract_docx_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from Word documents.

    Extracts:
    - Creation date (core_properties.created)
    - Modification date (core_properties.modified)
    - Author (core_properties.author)
    - Title (core_properties.title)
    - Subject (core_properties.subject)
    - Keywords (core_properties.keywords)
    - Last modified by (core_properties.last_modified_by)
    - Revision (core_properties.revision)

    Args:
        file_path: Path to DOCX file

    Returns:
        Dictionary with extracted metadata
    """
    try:
        doc = Document(str(file_path))
        core_props = doc.core_properties

        metadata = {}

        # Dates
        if core_props.created:
            metadata["document_created_at"] = core_props.created.isoformat()

        if core_props.modified:
            metadata["document_modified_at"] = core_props.modified.isoformat()

        # Text fields
        if core_props.author:
            metadata["document_author"] = core_props.author.strip()

        if core_props.title:
            metadata["document_title"] = core_props.title.strip()

        if core_props.subject:
            metadata["document_subject"] = core_props.subject.strip()

        if core_props.keywords:
            metadata["document_keywords"] = core_props.keywords.strip()

        if core_props.last_modified_by:
            metadata["document_last_modified_by"] = core_props.last_modified_by.strip()

        if core_props.revision:
            try:
                metadata["document_revision"] = int(core_props.revision)
            except (ValueError, TypeError):
                pass

        # Log successful extraction
        if metadata:
            log_event(
                "docx_metadata_extracted",
                {
                    "file": file_path.name,
                    "fields_extracted": list(metadata.keys()),
                    "has_creation_date": "document_created_at" in metadata,
                },
                level=logging.DEBUG,
            )

        return metadata

    except Exception as e:
        log_event(
            "docx_metadata_extraction_failed",
            {"file": file_path.name, "error": str(e)},
            level=logging.WARNING,
        )
        return {}


async def extract_xlsx_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from Excel workbooks.

    Extracts:
    - Creation date (properties.created)
    - Modification date (properties.modified)
    - Creator (properties.creator)
    - Last modified by (properties.lastModifiedBy)
    - Title (properties.title)
    - Subject (properties.subject)
    - Keywords (properties.keywords)

    Args:
        file_path: Path to XLSX file

    Returns:
        Dictionary with extracted metadata
    """
    try:
        # Load in read-only mode for performance
        wb = load_workbook(str(file_path), read_only=True, data_only=True)
        props = wb.properties

        metadata = {}

        # Dates
        if props.created:
            metadata["document_created_at"] = props.created.isoformat()

        if props.modified:
            metadata["document_modified_at"] = props.modified.isoformat()

        # Text fields
        if props.creator:
            metadata["document_author"] = props.creator.strip()

        if props.lastModifiedBy:
            metadata["document_last_modified_by"] = props.lastModifiedBy.strip()

        if props.title:
            metadata["document_title"] = props.title.strip()

        if props.subject:
            metadata["document_subject"] = props.subject.strip()

        if props.keywords:
            metadata["document_keywords"] = props.keywords.strip()

        wb.close()

        # Log successful extraction
        if metadata:
            log_event(
                "xlsx_metadata_extracted",
                {
                    "file": file_path.name,
                    "fields_extracted": list(metadata.keys()),
                    "has_creation_date": "document_created_at" in metadata,
                },
                level=logging.DEBUG,
            )

        return metadata

    except Exception as e:
        log_event(
            "xlsx_metadata_extraction_failed",
            {"file": file_path.name, "error": str(e)},
            level=logging.WARNING,
        )
        return {}


async def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract EXIF metadata from images.

    Extracts:
    - Date taken (EXIF DateTimeOriginal)
    - Camera make/model
    - GPS coordinates (if available)

    Args:
        file_path: Path to image file

    Returns:
        Dictionary with extracted metadata
    """
    try:
        image = Image.open(file_path)
        exif_data = image.getexif()

        if not exif_data:
            return {}

        metadata = {}

        # EXIF tag IDs
        DATETIME_ORIGINAL = 36867  # DateTimeOriginal
        DATETIME_DIGITIZED = 36868  # DateTimeDigitized
        MAKE = 271  # Camera make
        MODEL = 272  # Camera model

        # Extract date taken
        if DATETIME_ORIGINAL in exif_data:
            date_str = exif_data[DATETIME_ORIGINAL]
            try:
                # EXIF format: "YYYY:MM:DD HH:MM:SS"
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                metadata["document_created_at"] = dt.isoformat()
            except ValueError:
                pass
        elif DATETIME_DIGITIZED in exif_data:
            date_str = exif_data[DATETIME_DIGITIZED]
            try:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                metadata["document_created_at"] = dt.isoformat()
            except ValueError:
                pass

        # Camera info
        if MAKE in exif_data:
            metadata["camera_make"] = exif_data[MAKE].strip()

        if MODEL in exif_data:
            metadata["camera_model"] = exif_data[MODEL].strip()

        # Log successful extraction
        if metadata:
            log_event(
                "image_metadata_extracted",
                {
                    "file": file_path.name,
                    "fields_extracted": list(metadata.keys()),
                    "has_creation_date": "document_created_at" in metadata,
                },
                level=logging.DEBUG,
            )

        return metadata

    except Exception as e:
        log_event(
            "image_metadata_extraction_failed",
            {"file": file_path.name, "error": str(e)},
            level=logging.WARNING,
        )
        return {}


async def extract_document_metadata(file_path: Path, mime_type: str) -> Dict[str, Any]:
    """
    Extract internal document metadata based on file type.

    This is the main entry point for metadata extraction.
    Routes to appropriate extractor based on MIME type.

    Args:
        file_path: Path to document
        mime_type: MIME type of document

    Returns:
        Dictionary with extracted metadata (empty if not supported or failed)
    """
    try:
        # PDF
        if mime_type == "application/pdf":
            return await extract_pdf_metadata(file_path)

        # Word documents
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            return await extract_docx_metadata(file_path)

        # Excel files
        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/excel",
            "application/x-excel",
            "application/x-msexcel",
        ]:
            return await extract_xlsx_metadata(file_path)

        # Images
        elif mime_type.startswith("image/"):
            return await extract_image_metadata(file_path)

        # Unsupported type
        else:
            return {}

    except Exception as e:
        log_event(
            "document_metadata_extraction_failed",
            {
                "file": file_path.name,
                "mime_type": mime_type,
                "error": str(e),
            },
            level=logging.WARNING,
        )
        return {}
