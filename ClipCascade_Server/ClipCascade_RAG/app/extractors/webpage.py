import trafilatura

from app.extractors.base import ContentExtractor, ExtractionError
from app.models import ContentType, ExtractedContent


class WebPageExtractor(ContentExtractor):
    """Catch-all for any https page: readable-text extraction via trafilatura."""

    def supports(self, url: str) -> bool:
        return url.lower().startswith("https://")

    def extract(self, url: str) -> ExtractedContent:
        html = trafilatura.fetch_url(url)
        if not html:
            raise ExtractionError(f"could not fetch {url}")
        text = trafilatura.extract(html, include_comments=False) or ""
        meta = trafilatura.extract_metadata(html)
        if not text.strip():
            raise ExtractionError(f"no readable text on {url}")
        return ExtractedContent(
            source_url=url,
            content_type=ContentType.ARTICLE,
            text=text,
            title=meta.title if meta else None,
            author=meta.author if meta else None,
        )
