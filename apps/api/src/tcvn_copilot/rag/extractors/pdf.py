"""PDF drawing extractor: page-level OCR + vision LLM for sheet metadata."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.logging import get_logger
from tcvn_copilot.rag.llm import complete_json
from tcvn_copilot.rag.prompts.extraction import SYSTEM_PROMPT_VI

log = get_logger(__name__)

_MAX_PAGES_VISION = 12  # cap to keep cost bounded; the worker queues the rest


async def extract_pdf(path: Path) -> dict[str, Any]:
    """Return a dict with `pages` (OCR text per page) and `summary` (LLM-extracted)."""
    settings = get_settings()
    pages: list[dict[str, Any]] = []
    image_blocks: list[dict[str, Any]] = []

    with fitz.open(path) as doc:
        for page_idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=settings.ocr_dpi, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            text = pytesseract.image_to_string(img, lang=settings.tesseract_lang)
            pages.append({"page": page_idx + 1, "ocr_text": text.strip()})

            if page_idx < _MAX_PAGES_VISION:
                buf = io.BytesIO()
                img.thumbnail((1600, 1600))
                img.save(buf, format="JPEG", quality=85)
                image_blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(buf.getvalue()).decode("ascii"),
                        },
                    }
                )

    summary: dict[str, Any] = {}
    if image_blocks:
        # The vision LLM gets both OCR text + the page images so it can reconcile.
        ocr_blob = "\n\n".join(f"== Page {p['page']} ==\n{p['ocr_text']}" for p in pages)
        try:
            summary = await complete_json(
                system=SYSTEM_PROMPT_VI,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            *image_blocks,
                            {"type": "text", "text": f"OCR text:\n\n{ocr_blob[:30000]}"},
                        ],
                    }
                ],
                role="extraction",
                max_tokens=4096,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("pdf_vision_extract_failed", error=str(exc))
            summary = {"error": str(exc)}

    return {"pages": pages, "summary": summary, "page_count": len(pages)}
