from app.extractors.base import ContentExtractor, ExtractionError
from app.extractors.social import SocialPostExtractor
from app.extractors.webpage import WebPageExtractor
from app.extractors.ytdlp import YtDlpExtractor


class ExtractorRegistry:
    """Ordered chain of responsibility; first extractor that supports() wins."""

    def __init__(self) -> None:
        self._extractors: list[ContentExtractor] = [
            SocialPostExtractor(),
            YtDlpExtractor(),
            WebPageExtractor(),  # catch-all, must stay last
        ]

    def resolve(self, url: str) -> ContentExtractor:
        for extractor in self._extractors:
            if extractor.supports(url):
                return extractor
        raise ExtractionError(f"no extractor supports {url}")
