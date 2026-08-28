"""
rag/ingest/parser.py
=====================
Step 1 of RAG Ingest: Document Parsing.

Converts raw files (PDF, DOCX, TXT) into plain text.

TODO: Implement PDF parsing with pdfplumber or unstructured.io.
TODO: Implement DOCX parsing with python-docx.
TODO: Handle scanned PDFs with OCR (Tesseract / Azure Form Recognizer).

Production: Replace with Unstructured.io managed service for complex layouts.
"""

import os
import zipfile
import xml.etree.ElementTree as ET
import structlog
from pypdf import PdfReader

logger = structlog.get_logger(__name__)


async def parse_document(file_path: str, content_type: str) -> str:
    """
    Parse a document file and return its plain text content.

    Args:
        file_path: Path to the downloaded file (from MinIO).
        content_type: MIME type (application/pdf, text/plain, etc.).

    Returns:
        Extracted plain text string.
    """
    logger.info("parse_document called", file_path=file_path, content_type=content_type)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Canonicalize content type and extension
    content_type = content_type.lower()
    ext = os.path.splitext(file_path)[1].lower()

    if content_type == "application/pdf" or ext == ".pdf":
        return await _parse_pdf(file_path)
    elif content_type in ["text/plain", "text/markdown"] or ext in [".txt", ".md"]:
        return await _parse_txt(file_path)
    elif (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or ext == ".docx"
    ):
        return await _parse_docx(file_path)
    else:
        # Fallback: try to read as text
        try:
            return await _parse_txt(file_path)
        except Exception as e:
            raise ValueError(f"Unsupported content type '{content_type}' and unable to parse as text: {e}")


async def _parse_pdf(file_path: str) -> str:
    """Extract text from PDF using pypdf."""
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("Failed to parse PDF file", file_path=file_path, error=str(e))
        raise


async def _parse_txt(file_path: str) -> str:
    """Extract text from a plain text/markdown file."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode text file at {file_path} with standard encodings.")


async def _parse_docx(file_path: str) -> str:
    """Extract text from a docx file using standard zipfile/xml parsing."""
    try:
        # docx is a zip file containing word/document.xml
        with zipfile.ZipFile(file_path) as z:
            doc_xml = z.read("word/document.xml")
            root = ET.fromstring(doc_xml)
            
            # Namespace map for Word ProcessingML
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            
            # Find all text elements
            text_elems = root.findall(".//w:t", ns)
            text_content = [elem.text for elem in text_elems if elem.text]
            
            return " ".join(text_content)
    except Exception as e:
        logger.error("Failed to parse DOCX file", file_path=file_path, error=str(e))
        raise

