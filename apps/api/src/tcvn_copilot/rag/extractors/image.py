"""Single-image extractor — OCR + vision LLM."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.logging import get_logger
from tcvn_copilot.rag.llm import complete_json
from tcvn_copilot.rag.prompts.extraction import SYSTEM_PROMPT_VI

log = get_logger(__name__)


async def extract_image(path: Path) -> dict[str, Any]:
    settings = get_settings()
    with Image.open(path) as img:
        img = img.convert("RGB")
        text = pytesseract.image_to_string(img, lang=settings.tesseract_lang)
        buf = io.BytesIO()
        img.thumbnail((1600, 1600))
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    try:
        summary = await complete_json(
            system=SYSTEM_PROMPT_VI,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                        },
                        {"type": "text", "text": f"OCR text:\n\n{text}"},
                    ],
                }
            ],
            role="extraction",
            max_tokens=4096,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("image_vision_extract_failed", error=str(exc))
        summary = {"error": str(exc)}

    return {"pages": [{"page": 1, "ocr_text": text.strip()}], "summary": summary, "page_count": 1}
