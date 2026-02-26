"""Local Embedding Provider — sentence-transformers 기반."""

from __future__ import annotations

from dolt.embedding.base import BaseEmbeddingProvider
from dolt.utils.logging import get_logger

logger = get_logger("embedding.local")

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        device: str = "cpu",
        batch_size: int = 64,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None  # 지연 로딩
        self._dim: int | None = None

    def _load_model(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info("로컬 모델 로딩: %s (device=%s)", self._model_name, self._device)
        self._model = SentenceTransformer(self._model_name, device=self._device)
        self._dim = self._model.get_sentence_embedding_dimension()

    def model_name(self) -> str:
        return self._model_name

    def dimension(self) -> int:
        if self._dim is None:
            self._load_model()
        return self._dim  # type: ignore[return-value]

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            embeddings = self._model.encode(batch, show_progress_bar=False)  # type: ignore[union-attr]
            all_vectors.extend(embeddings.tolist())
            logger.info("배치 %d/%d 완료 (%d chunks)", i // self._batch_size + 1,
                       (len(texts) + self._batch_size - 1) // self._batch_size,
                       len(batch))

        return all_vectors
