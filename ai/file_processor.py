"""
File content extraction utilities for uploaded documents and images.

Supports:
- PDF: text extraction via pdfplumber
- DOCX: text extraction via python-docx
- TXT: plain text
- Images (PNG, JPG, WebP): base64 encoding for vision AI
"""
from __future__ import annotations

import base64
import io


SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}

IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_SESSION = 5

# Text extraction truncation limit (chars) to avoid overflowing the context window
MAX_TEXT_CHARS = 12_000


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF file. Returns empty string on failure."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
    except Exception:
        return ""


def extract_text_from_docx(data: bytes) -> str:
    """Extract text from a DOCX file. Returns empty string on failure."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(data))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)
    except Exception:
        return ""


def encode_image_b64(data: bytes) -> str:
    """Encode image bytes as a base64 string."""
    return base64.standard_b64encode(data).decode()


def process_uploaded_file(
    filename: str,
    mime_type: str,
    data: bytes,
) -> dict:
    """
    Process an uploaded file and return a metadata dict.

    Returns:
        {
            "name": str,
            "mime_type": str,
            "size": int,
            "is_image": bool,
            "text_content": str | None,   # for text-based files
            "b64_data": str | None,       # for image files
        }
    """
    file_type = SUPPORTED_MIME_TYPES.get(mime_type, "")
    is_image = mime_type in IMAGE_MIME_TYPES

    text_content: str | None = None
    b64_data: str | None = None

    if file_type == "pdf":
        text_content = extract_text_from_pdf(data)[:MAX_TEXT_CHARS]
    elif file_type == "docx":
        text_content = extract_text_from_docx(data)[:MAX_TEXT_CHARS]
    elif file_type == "txt":
        text_content = data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
    elif is_image:
        b64_data = encode_image_b64(data)

    return {
        "name": filename,
        "mime_type": mime_type,
        "size": len(data),
        "is_image": is_image,
        "text_content": text_content,
        "b64_data": b64_data,
    }
