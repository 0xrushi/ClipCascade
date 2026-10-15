import asyncio
import logging

from app.config import settings
from app.models import IngestRequest
from app.pipeline import IngestionPipeline
from app.rag.indexer import url_hash

logger = logging.getLogger(__name__)


class IngestionWorker:
    """In-memory job queue drained by N asyncio consumers.

    Jobs are lost on restart by design (a dropped clipboard link can simply be
    re-copied). Dedup happens both at enqueue time (pending set) and at index
    time (Qdrant url_hash lookup).
    """

    def __init__(self, pipeline: IngestionPipeline) -> None:
        self._pipeline = pipeline
        self._queue: asyncio.Queue[IngestRequest] = asyncio.Queue(settings.max_queue_size)
        self._pending: set[str] = set()
        self._consumers: list[asyncio.Task] = []
        self.jobs_done = 0
        self.jobs_failed = 0

    def start(self) -> None:
        self._consumers = [
            asyncio.create_task(self._consume(), name=f"ingest-worker-{i}")
            for i in range(settings.worker_concurrency)
        ]

    async def stop(self) -> None:
        for task in self._consumers:
            task.cancel()
        await asyncio.gather(*self._consumers, return_exceptions=True)

    def enqueue(self, request: IngestRequest) -> bool:
        """Returns False when dropped (duplicate in flight or queue full)."""
        key = url_hash(request.username, request.url)
        if key in self._pending:
            return False
        try:
            self._queue.put_nowait(request)
        except asyncio.QueueFull:
            logger.warning("queue full, dropping %s", request.url)
            return False
        self._pending.add(key)
        return True

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    async def _consume(self) -> None:
        while True:
            request = await self._queue.get()
            try:
                await self._process(request)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("unrecoverable failure for %s", request.url)
                self.jobs_failed += 1
            finally:
                self._pending.discard(url_hash(request.username, request.url))
                self._queue.task_done()

    async def _process(self, request: IngestRequest) -> None:
        last_error: Exception | None = None
        for attempt in range(settings.job_max_retries + 1):
            try:
                await asyncio.to_thread(self._pipeline.ingest, request)
                self.jobs_done += 1
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    "attempt %d/%d failed for %s: %s",
                    attempt + 1, settings.job_max_retries + 1, request.url, e,
                )
                await asyncio.sleep(2**attempt)
        self.jobs_failed += 1
        logger.error("giving up on %s: %s", request.url, last_error)
