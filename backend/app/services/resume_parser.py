"""
Resume text extraction.

Pure function, deliberately no I/O of its own (caller fetches the bytes
from wherever — MinIO, an upload, a test fixture). This keeps it testable
without needing a storage backend, and reusable for any future "extract
text from a document" need (offer letters, certificates) without dragging
storage concerns into it.
"""
import io

import pdfplumber
from docx import Document

from app.core.exceptions import AppError

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_text(filename: str, content: bytes) -> str:
    """Raises AppError (400) for unsupported file types or unparseable content —
    both are user-input problems, not server bugs, so they shouldn't 500."""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf_text(content)
    if lower.endswith(".docx"):
        return _extract_docx_text(content)

    raise AppError(f"Unsupported resume file type. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")


def _extract_pdf_text(content: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise AppError(f"Could not parse PDF resume: {exc}") from exc

    text = "\n".join(pages).strip()
    if not text:
        # Common cause: a scanned/image-only PDF with no extractable text layer.
        # OCR fallback (per your architecture's ai-services/ocr/) is a separate,
        # later addition — not built here.
        raise AppError("No extractable text found in PDF (it may be a scanned image without OCR support yet).")
    return text


def _extract_docx_text(content: bytes) -> str:
    try:
        doc = Document(io.BytesIO(content))
    except Exception as exc:
        raise AppError(f"Could not parse DOCX resume: {exc}") from exc

    text = "\n".join(p.text for p in doc.paragraphs).strip()
    if not text:
        raise AppError("No extractable text found in DOCX file.")
    return text
