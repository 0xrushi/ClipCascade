import base64
import logging

import httpx

from app.config import settings
from app.enrich.base import MediaEnricher
from app.models import MediaItem

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = (
    "Describe this image in detail for a search index. Include any text "
    "visible in the image verbatim (OCR), the subject, setting, and any "
    "notable objects or people. Respond with plain text only."
)


class ImageDescriber(MediaEnricher):
    """Describes and OCRs images via the Gemini API (GEMINI_API_KEY env var)."""

    def supports(self, item: MediaItem) -> bool:
        return item.kind == "image"

    def enrich(self, item: MediaItem) -> str:
        if not settings.gemini_api_key:
            # GEMINI_API_KEY is required at startup (see main.py); this would
            # only trigger if it were unset out from under a running process.
            raise RuntimeError("GEMINI_API_KEY is not set; cannot describe image")
        try:
            resp = httpx.get(item.url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
            image_b64 = base64.b64encode(resp.content).decode()
            return self._describe(image_b64, mime)
        except Exception as e:
            logger.warning("image understanding failed for %s: %s", item.url, e)
            return ""

    def _describe(self, image_b64: str, mime: str) -> str:
        response = httpx.post(
            GEMINI_ENDPOINT.format(model=settings.gemini_model),
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"inline_data": {"mime_type": mime, "data": image_b64}},
                            {"text": PROMPT},
                        ]
                    }
                ]
            },
            timeout=60,
        )
        response.raise_for_status()
        candidates = response.json().get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(p["text"] for p in parts if "text" in p).strip()
