import logging
import os
import re
from urllib.parse import urlparse

import yt_dlp

from app.config import settings
from app.extractors.base import ContentExtractor, ExtractionError
from app.models import ContentType, ExtractedContent, MediaItem

logger = logging.getLogger(__name__)

VIDEO_HOSTS = re.compile(
    r"(^|\.)(youtube\.com|youtu\.be|tiktok\.com|vm\.tiktok\.com)$", re.IGNORECASE
)


def _read_subtitle_file(path: str) -> str:
    # Strip VTT/SRT cue headers and timestamps, keep unique text lines.
    lines: list[str] = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or "-->" in line or line.isdigit() or line.startswith(("WEBVTT", "Kind:", "Language:")):
                continue
            line = re.sub(r"<[^>]+>", "", line)
            if not lines or lines[-1] != line:
                lines.append(line)
    return "\n".join(lines)


class YtDlpExtractor(ContentExtractor):
    """Videos from YouTube/TikTok/Instagram (and any yt-dlp-supported URL when
    delegated to).

    Strategy: metadata + subtitles first — that is usually all the text we
    need. For an actual video post, the audio is only downloaded when there
    are no subtitles and transcription is enabled; a thumbnail is always
    captured too, so the pipeline can fall back to describing it if the
    transcript turns out to carry no real speech (e.g. a reel that's really
    just a static/looping image with background music). Posts that are pure
    images to begin with (Instagram photo posts) skip audio entirely and are
    described from the thumbnail alone.
    """

    def supports(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return bool(VIDEO_HOSTS.search(host))

    def extract(self, url: str) -> ExtractedContent:
        os.makedirs(settings.download_dir, exist_ok=True)
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-orig", "-live_chat"],
            "subtitlesformat": "vtt/srt/best",
            "outtmpl": os.path.join(settings.download_dir, "%(id)s.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)  # downloads subs only
        except Exception as e:
            raise ExtractionError(f"yt-dlp failed for {url}: {e}") from e

        text_parts = [info.get("description") or ""]
        subtitle_text = self._collect_subtitles(info)
        if subtitle_text:
            text_parts.append(subtitle_text)

        # yt-dlp sets is_video=False for photo posts (e.g. an Instagram image
        # post); default True since YouTube/TikTok entries omit the field.
        is_video = info.get("is_video", True)

        content = ExtractedContent(
            source_url=url,
            content_type=ContentType.VIDEO if is_video else ContentType.IMAGE,
            title=info.get("title"),
            author=info.get("uploader") or info.get("channel"),
            text="\n\n".join(p for p in text_parts if p),
        )

        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            content.thumbnail = MediaItem(url=thumbnail_url, kind="image")

        if not is_video:
            # Photo-only post: nothing to transcribe. The pipeline enriches
            # content.thumbnail directly since content.media is empty.
            return content

        if not subtitle_text and settings.transcription_enabled:
            local = self._download_audio(url, info.get("id", "media"))
            if local:
                content.media.append(MediaItem(url=url, kind="audio", local_path=local))
        return content

    def _collect_subtitles(self, info: dict) -> str:
        vid = info.get("id", "")
        parts = []
        for name in os.listdir(settings.download_dir):
            if vid and name.startswith(vid) and name.endswith((".vtt", ".srt")):
                path = os.path.join(settings.download_dir, name)
                try:
                    parts.append(_read_subtitle_file(path))
                finally:
                    os.remove(path)
        return "\n".join(parts)

    def _download_audio(self, url: str, media_id: str) -> str | None:
        out = os.path.join(settings.download_dir, f"{media_id}.audio.%(ext)s")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "outtmpl": out,
            "max_filesize": settings.max_download_mb * 1024 * 1024,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                path = ydl.prepare_filename(info)
            return path if os.path.exists(path) else None
        except Exception as e:
            logger.warning("audio download failed for %s: %s", url, e)
            return None
