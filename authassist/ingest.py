"""Step 1: turn pasted text / PDF / image into note_text (the single source of
truth for evidence quotes). Uploaded bytes are processed in memory only."""

from __future__ import annotations

import base64
import io

import pymupdf
from PIL import Image
from pypdf import PdfReader

from authassist import llm

MIN_CHARS_PER_PAGE = 200
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}

VISION_PROMPT = (
    "Transcribe this clinical note faithfully, exactly as written. Preserve line breaks. "
    "Do not summarize, correct, reorder or add anything. Mark any unreadable part as [illegible]. "
    "Output only the transcription."
)


def _png_b64(img: Image.Image, max_side: int = 1800) -> str:
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def transcribe_images(images: list[Image.Image]) -> str:
    pages = []
    for i, img in enumerate(images, start=1):
        result = llm.chat(
            "vision",
            [llm.image_message(VISION_PROMPT, [_png_b64(img)])],
            step=f"ingest: read scan p{i}",
        )
        pages.append(result.text.strip())
    return "\n\n".join(pages)


def pdf_text_pages(data: bytes) -> list[str]:
    return [(page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages]


def pdf_to_images(data: bytes, dpi: int = 150) -> list[Image.Image]:
    images = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    return images


def ingest(
    note_text: str | None = None, file_bytes: bytes | None = None, filename: str | None = None
) -> tuple[str, str]:
    """Return (note_text, method) where method is text | pdf_text | vision."""
    if note_text and note_text.strip():
        return note_text.strip(), "text"
    if not file_bytes:
        raise ValueError("Provide note text or a file")
    name = (filename or "").lower()
    ext = name[name.rfind(".") :] if "." in name else ""

    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="replace").strip(), "text"
    if ext == ".pdf" or file_bytes[:4] == b"%PDF":
        pages = pdf_text_pages(file_bytes)
        if pages and all(len(p.strip()) >= MIN_CHARS_PER_PAGE for p in pages):
            return "\n\n".join(p.strip() for p in pages), "pdf_text"
        return transcribe_images(pdf_to_images(file_bytes)), "vision"
    if ext in IMAGE_EXTS or not ext:
        return transcribe_images([Image.open(io.BytesIO(file_bytes))]), "vision"
    raise ValueError(f"Unsupported file type: {ext}")
