import json
import logging
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.extractors.base import ExtractionError

logger = logging.getLogger(__name__)

CHAT_COMPLETIONS_PATH = "/v1/chat/completions"

PROMPT_TEMPLATE = (
    "Fetch the content of this X (formerly Twitter) post and respond with a "
    "single JSON object with exactly these keys:\n"
    "- \"author\": the poster's handle, without the leading @, or null if unknown\n"
    "- \"text\": the full post text, verbatim\n"
    "- \"image_urls\": a list of direct URLs to any images attached to the "
    "post (empty list if none)\n"
    "- \"video_url\": a direct URL to the video/gif attached to the post, "
    "or null if there is no video/gif\n"
    "Respond with JSON only, no markdown fences or commentary.\n\n"
    "Post URL: {url}"
)


@dataclass
class TweetContent:
    text: str = ""
    author: str | None = None
    image_urls: list[str] = field(default_factory=list)
    video_url: str | None = None


def ask_tweet_content(url: str) -> TweetContent:
    """Asks the Hermes chat-completions endpoint to fetch a tweet and
    return its text, author and any attached media. Raises ExtractionError
    on failure."""
    try:
        resp = httpx.post(
            settings.hermes_api_base_url.rstrip("/") + CHAT_COMPLETIONS_PATH,
            json={
                "model": settings.hermes_model,
                "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(url=url)}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise ExtractionError(f"Hermes chat completions failed for {url}: {e}") from e

    try:
        parsed = json.loads(content)
        return TweetContent(
            text=parsed.get("text") or "",
            author=parsed.get("author"),
            image_urls=[u for u in (parsed.get("image_urls") or []) if u],
            video_url=parsed.get("video_url") or None,
        )
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning("Hermes response for %s was not valid JSON; using raw text", url)
        return TweetContent(text=content.strip())
