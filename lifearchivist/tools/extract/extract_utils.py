from pathlib import Path

import aiofiles
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


def _get_extraction_method(mime_type: str) -> str:
    """Get extraction method name based on mime type."""
    if mime_type.startswith("text/"):
        return "text_file"
    elif mime_type == "application/pdf":
        return "pypdf"
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return "python_docx"
    else:
        raise ValueError(f"Mime type not supported: {mime_type}")


async def _extract_text_file(file_path: Path) -> str:
    """Extract text from plain text files."""
    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return await f.read()


def extract_table_text(table: Table) -> str:
    """Extract text from table with structure preservation."""
    table_text = []
    for row in table.rows:
        row_text = []
        for cell in row.cells:
            cell_text = cell.text.strip()
            if cell_text:
                row_text.append(cell_text)
        if row_text:
            table_text.append(" | ".join(row_text))
    return "\n".join(table_text)


def extract_paragraph_text(paragraph: Paragraph) -> str:
    """Extract text from paragraph with run-level formatting awareness."""
    if not paragraph.text.strip():
        return ""

    paragraph_text = paragraph.text.strip()

    # Preserve important formatting indicators
    if paragraph.style and paragraph.style.name:
        style_name = paragraph.style.name.lower()
        if "heading" in style_name:
            # Mark headings for better semantic understanding
            paragraph_text = f"[HEADING] {paragraph_text}"
        elif "title" in style_name:
            paragraph_text = f"[TITLE] {paragraph_text}"

    return paragraph_text


async def _extract_docx_text(file_path: Path) -> str:
    """Extract text from Word documents using python-docx with comprehensive content extraction."""
    try:
        doc = Document(str(file_path))
        extracted_content = []

        # Process document body elements in order to preserve structure
        for element in doc.element.body:
            if isinstance(element, CT_P):
                # Paragraph element
                paragraph = Paragraph(element, doc)
                paragraph_text = extract_paragraph_text(paragraph)
                if paragraph_text:
                    extracted_content.append(paragraph_text)

            elif isinstance(element, CT_Tbl):
                # Table element
                table = Table(element, doc)
                table_text = extract_table_text(table)
                if table_text:
                    extracted_content.append(f"[TABLE]\n{table_text}")

        # Process headers and footers for comprehensive extraction
        for section in doc.sections:
            if section.header:
                for paragraph in section.header.paragraphs:
                    header_text = extract_paragraph_text(paragraph)
                    if header_text:
                        extracted_content.insert(0, f"[HEADER] {header_text}")

            if section.footer:
                for paragraph in section.footer.paragraphs:
                    footer_text = extract_paragraph_text(paragraph)
                    if footer_text:
                        extracted_content.append(f"[FOOTER] {footer_text}")

        # Join all content with proper spacing
        full_text = "\n\n".join(extracted_content)

        # Clean up excessive whitespace while preserving structure
        import re

        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r"[ \t]+", " ", full_text)

        word_count = len(full_text.split())

        return full_text.strip()

    except Exception as e:
        raise ValueError(
            f"Error extracting Word document text from {file_path}: {e}"
        ) from None


async def _extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF files using pypdf."""
    try:
        text_content = []
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())

        return "\n".join(text_content)
    except Exception as e:
        raise ValueError(f"Error extracting PDF text: {e}") from None


async def _extract_text_by_type(file_path: Path, mime_type: str) -> str:
    """Extract text based on file type."""
    try:
        if mime_type.startswith("text/"):
            return await _extract_text_file(file_path)
        elif mime_type == "application/pdf":
            return await _extract_pdf_text(file_path)
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            return await _extract_docx_text(file_path)
        else:
            return ""
    except Exception as e:
        raise ValueError(f"Error extracting text from {file_path}: {e}") from None
