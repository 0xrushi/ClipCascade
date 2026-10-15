import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from app.config import settings
from app.models import IngestRequest, SearchResponse
from app.pipeline import IngestionPipeline
from app.rag.embeddings import FastEmbedEmbedder
from app.rag.indexer import QdrantIndexer
from app.rag.search import SearchService
from app.worker import IngestionWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Image understanding/OCR is a required "
            "part of the ingestion pipeline (used for image posts and as the "
            "fallback for videos with no useful speech) — set GEMINI_API_KEY "
            "in the environment before starting the sidecar."
        )
    embedder = FastEmbedEmbedder()
    indexer = QdrantIndexer(embedder)
    worker = IngestionWorker(IngestionPipeline(indexer))
    worker.start()
    state["worker"] = worker
    state["search"] = SearchService(embedder, indexer)
    yield
    await worker.stop()


app = FastAPI(title="ClipCascade RAG Sidecar", lifespan=lifespan)


def check_auth(request: Request) -> None:
    if settings.auth_token and request.headers.get("X-CCRAG-Token") != settings.auth_token:
        raise HTTPException(status_code=401, detail="invalid or missing X-CCRAG-Token")


@app.post("/ingest", status_code=202, dependencies=[Depends(check_auth)])
def ingest(request: IngestRequest):
    accepted = state["worker"].enqueue(request)
    return {"accepted": accepted, "queued": state["worker"].depth}


@app.get("/search", response_model=SearchResponse, dependencies=[Depends(check_auth)])
def search(username: str, q: str, limit: int = 8):
    return state["search"].search(username, q, limit)


@app.get("/health")
def health():
    worker: IngestionWorker = state["worker"]
    return {
        "status": "ok",
        "queue_depth": worker.depth,
        "jobs_done": worker.jobs_done,
        "jobs_failed": worker.jobs_failed,
    }
