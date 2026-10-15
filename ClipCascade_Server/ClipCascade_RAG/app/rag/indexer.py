import hashlib
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.models import ExtractedContent, IngestRequest
from app.rag.embeddings import EmbeddingService


def url_hash(username: str, url: str) -> str:
    return hashlib.sha256(f"{username}|{url}".encode()).hexdigest()


class QdrantIndexer:
    def __init__(self, embedder: EmbeddingService) -> None:
        self._embedder = embedder
        # The public Qdrant endpoint is behind HTTPS/Caddy on port 443. Keep
        # the configured URL portless, but override qdrant-client's default
        # REST port (6333) so it does not bypass the reverse proxy.
        self._client = QdrantClient(
            url=settings.qdrant_url,
            port=443,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self._client.collection_exists(settings.collection):
            self._client.create_collection(
                collection_name=settings.collection,
                vectors_config=VectorParams(
                    size=self._embedder.dimension, distance=Distance.COSINE
                ),
            )
            for field in ("username", "url_hash"):
                self._client.create_payload_index(
                    collection_name=settings.collection,
                    field_name=field,
                    field_schema="keyword",
                )

    def already_indexed(self, username: str, url: str) -> bool:
        count = self._client.count(
            collection_name=settings.collection,
            count_filter=Filter(
                must=[
                    FieldCondition(key="username", match=MatchValue(value=username)),
                    FieldCondition(key="url_hash", match=MatchValue(value=url_hash(username, url))),
                ]
            ),
        )
        return count.count > 0

    def index(self, request: IngestRequest, content: ExtractedContent, chunks: list[str]) -> int:
        if not chunks:
            return 0
        vectors = self._embedder.embed(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "username": request.username,
                    "url": request.url,
                    "url_hash": url_hash(request.username, request.url),
                    "link_type": request.link_type.value,
                    "content_type": content.content_type.value,
                    "title": content.title,
                    "author": content.author,
                    "timestamp": request.timestamp,
                    "chunk_index": i,
                    "text": chunk,
                },
            )
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=settings.collection, points=points)
        return len(points)

    def search(self, username: str, query_vector: list[float], limit: int = 8):
        return self._client.query_points(
            collection_name=settings.collection,
            query=query_vector,
            limit=limit,
            query_filter=Filter(
                must=[FieldCondition(key="username", match=MatchValue(value=username))]
            ),
            with_payload=True,
        ).points
