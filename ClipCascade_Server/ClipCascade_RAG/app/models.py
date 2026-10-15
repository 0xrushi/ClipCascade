from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel


class LinkType(str, Enum):
    TWITTER = "TWITTER"
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    GENERIC_WEB = "GENERIC_WEB"


class ContentType(str, Enum):
    POST = "post"
    IMAGE = "image"
    VIDEO = "video"
    ARTICLE = "article"


class IngestRequest(BaseModel):
    """Payload sent by the ClipCascade Java server."""

    url: str
    link_type: LinkType = LinkType.GENERIC_WEB
    username: str
    timestamp: int  # epoch millis at clipboard time


class SearchHit(BaseModel):
    score: float
    text: str
    url: str
    title: str | None = None
    link_type: str | None = None
    content_type: str | None = None
    timestamp: int | None = None
    chunk_index: int = 0


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


@dataclass
class MediaItem:
    """A downloadable media attachment discovered during extraction."""

    url: str  # remote URL or local file path once downloaded
    kind: str  # "image" | "video" | "audio"
    local_path: str | None = None


@dataclass
class ExtractedContent:
    source_url: str
    content_type: ContentType
    text: str = ""
    title: str | None = None
    author: str | None = None
    media: list[MediaItem] = field(default_factory=list)
    # A representative still frame/thumbnail, used as a fallback source of
    # text when `media` (e.g. an audio track) turns out to carry no useful
    # content — e.g. a reel with generic background music and no speech.
    thumbnail: MediaItem | None = None

    def combined_text(self) -> str:
        parts = [p for p in (self.title, self.author and f"by {self.author}", self.text) if p]
        return "\n\n".join(parts)
