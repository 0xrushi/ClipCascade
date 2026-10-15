from app.models import SearchHit, SearchResponse
from app.rag.embeddings import EmbeddingService
from app.rag.indexer import QdrantIndexer


class SearchService:
    def __init__(self, embedder: EmbeddingService, indexer: QdrantIndexer) -> None:
        self._embedder = embedder
        self._indexer = indexer

    def search(self, username: str, query: str, limit: int = 8) -> SearchResponse:
        vector = self._embedder.embed([query])[0]
        points = self._indexer.search(username, vector, limit)
        hits = [
            SearchHit(
                score=p.score,
                text=(p.payload or {}).get("text", ""),
                url=(p.payload or {}).get("url", ""),
                title=(p.payload or {}).get("title"),
                link_type=(p.payload or {}).get("link_type"),
                content_type=(p.payload or {}).get("content_type"),
                timestamp=(p.payload or {}).get("timestamp"),
                chunk_index=(p.payload or {}).get("chunk_index", 0),
            )
            for p in points
        ]
        return SearchResponse(query=query, hits=hits)
