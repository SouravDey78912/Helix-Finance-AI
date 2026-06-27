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

import structlog

logger = structlog.get_logger(__name__)


async def parse_document(file_path: str, content_type: str) -> str:
    """
    Parse a document file and return its plain text content.

    Args:
        file_path: Path to the downloaded file (from MinIO).
        content_type: MIME type (application/pdf, application/docx, text/plain).

    Returns:
        Extracted plain text string.

    TODO: Route to appropriate parser based on content_type.
    """
    logger.info("parse_document called", file_path=file_path, content_type=content_type)
    raise NotImplementedError("Document parser not yet implemented")
