import logging

from app.enrich.base import MediaEnricher
from app.enrich.image_describer import ImageDescriber
from app.enrich.transcriber import WhisperTranscriber
from app.extractors.registry import ExtractorRegistry
from app.models import IngestRequest
from app.rag.chunker import Chunker
from app.rag.indexer import QdrantIndexer

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """extract -> enrich media -> chunk -> embed -> index. Blocking; runs in
    the worker's thread pool."""

    def __init__(self, indexer: QdrantIndexer) -> None:
        self._registry = ExtractorRegistry()
        self._enrichers: list[MediaEnricher] = [WhisperTranscriber(), ImageDescriber()]
        self._chunker = Chunker()
        self._indexer = indexer

    def ingest(self, request: IngestRequest) -> int:
        """Returns the number of chunks indexed (0 = skipped as duplicate)."""
        if self._indexer.already_indexed(request.username, request.url):
            logger.info("skip (already indexed): %s", request.url)
            return 0

        content = self._registry.resolve(request.url).extract(request.url)

        extra_texts = self._enrich(content.media)
        if not extra_texts and content.thumbnail:
            # Primary media (e.g. audio) yielded nothing useful — e.g. a
            # reel with background music but no speech, or a pure image
            # post with no media at all. Fall back to describing the
            # thumbnail frame instead.
            extra_texts = self._enrich([content.thumbnail])

        full_text = "\n\n".join([content.combined_text(), *extra_texts]).strip()
        chunks = self._chunker.split(full_text)
        count = self._indexer.index(request, content, chunks)
        logger.info("indexed %d chunks for %s", count, request.url)
        return count

    def _enrich(self, items) -> list[str]:
        texts = []
        for item in items:
            for enricher in self._enrichers:
                if enricher.supports(item):
                    text = enricher.enrich(item)
                    if text:
                        texts.append(text)
                    break
        return texts
