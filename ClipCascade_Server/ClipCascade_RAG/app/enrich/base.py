from abc import ABC, abstractmethod

from app.models import MediaItem


class MediaEnricher(ABC):
    """Turns a media attachment into indexable text (transcript, OCR, ...)."""

    @abstractmethod
    def supports(self, item: MediaItem) -> bool: ...

    @abstractmethod
    def enrich(self, item: MediaItem) -> str:
        """Blocking; returns extra text ('' when nothing could be extracted)."""
        ...
