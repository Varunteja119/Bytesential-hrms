import io

import pdfplumber
from docx import Document

from app.core.exceptions import AppError

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_text(filename: str, content: bytes) -> str:
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
