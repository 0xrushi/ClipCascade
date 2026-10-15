from abc import ABC, abstractmethod

from fastembed import TextEmbedding

from app.config import settings


class EmbeddingService(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder(EmbeddingService):
    """Local ONNX embeddings via fastembed; no GPU or API key needed."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.embedding_model
        self._model = TextEmbedding(model_name=self._model_name)
        self._dimension = len(next(iter(self._model.embed(["probe"]))))

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]
