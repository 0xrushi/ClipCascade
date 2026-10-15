from abc import ABC, abstractmethod

from app.models import ExtractedContent


class ExtractionError(Exception):
    pass


class ContentExtractor(ABC):
    """Turns a URL into ExtractedContent. One subclass per source family."""

    @abstractmethod
    def supports(self, url: str) -> bool: ...

    @abstractmethod
    def extract(self, url: str) -> ExtractedContent:
        """Blocking; the worker runs extractors in a thread pool."""
        ...
