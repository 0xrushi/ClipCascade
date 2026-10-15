import logging
import os
import tempfile

import httpx
from faster_whisper import WhisperModel

from app.config import settings
from app.enrich.base import MediaEnricher
from app.models import MediaItem

logger = logging.getLogger(__name__)


class WhisperTranscriber(MediaEnricher):
    """Transcribes audio/video with faster-whisper (required dependency)."""

    def __init__(self) -> None:
        self._model: WhisperModel | None = None

    def supports(self, item: MediaItem) -> bool:
        return settings.transcription_enabled and item.kind in ("audio", "video")

    def enrich(self, item: MediaItem) -> str:
        path = item.local_path or self._download(item.url)
        if not path:
            return ""
        try:
            if self._model is None:
                self._model = WhisperModel(settings.whisper_model, compute_type="int8")
            segments, _ = self._model.transcribe(path)
            return self._quality_gated_text(segments, item.url)
        except Exception as e:
            logger.warning("transcription failed for %s: %s", item.url, e)
            return ""
        finally:
            if os.path.exists(path):
                os.remove(path)

    def _quality_gated_text(self, segments, source: str) -> str:
        """Discards transcripts that are mostly background music/noise rather
        than speech (common on reels with a static image + looping audio),
        so the pipeline falls back to describing the thumbnail instead."""
        texts: list[str] = []
        no_speech_probs: list[float] = []
        for seg in segments:
            texts.append(seg.text.strip())
            no_speech_probs.append(seg.no_speech_prob)

        transcript = " ".join(t for t in texts if t)
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs) if no_speech_probs else 1.0
        word_count = len(transcript.split())

        if avg_no_speech > settings.whisper_no_speech_threshold or word_count < settings.whisper_min_words:
            logger.info(
                "discarding low-quality transcript for %s (avg_no_speech=%.2f, words=%d)",
                source, avg_no_speech, word_count,
            )
            return ""
        return transcript

    def _download(self, url: str) -> str | None:
        try:
            limit = settings.max_download_mb * 1024 * 1024
            fd, path = tempfile.mkstemp(dir=settings.download_dir)
            size = 0
            with os.fdopen(fd, "wb") as f, httpx.stream(
                "GET", url, timeout=60, follow_redirects=True
            ) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("media exceeds CCRAG_MAX_DOWNLOAD_MB")
                    f.write(chunk)
            return path
        except Exception as e:
            logger.warning("media download failed for %s: %s", url, e)
            return None
