"""Cohere Embedding Provider."""

from __future__ import annotations

import os
import time

from dolt.embedding.base import BaseEmbeddingProvider
from dolt.errors import APIKeyMissingError, RateLimitError
from dolt.utils.logging import get_logger

logger = get_logger("embedding.cohere")

_DEFAULT_MODEL = "embed-multilingual-v3.0"


class CohereEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        input_type: str = "search_document",
        batch_size: int = 96,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("COHERE_API_KEY")
        if not self._api_key:
            raise APIKeyMissingError("Cohere")
        self._input_type = input_type
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def model_name(self) -> str:
        return self._model

    def dimension(self) -> int:
        return 1024  # embed-multilingual-v3.0

    def embed(self, texts: list[str]) -> list[list[float]]:
        import cohere

        client = cohere.ClientV2(api_key=self._api_key)
        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            vectors = self._embed_batch(client, batch)
            all_vectors.extend(vectors)
            logger.info("배치 %d/%d 완료 (%d chunks)", i // self._batch_size + 1,
                       (len(texts) + self._batch_size - 1) // self._batch_size,
                       len(batch))

        return all_vectors

    def _embed_batch(self, client, batch: list[str]) -> list[list[float]]:
        for attempt in range(self._max_retries + 1):
            try:
                response = client.embed(
                    model=self._model,
                    texts=batch,
                    input_type=self._input_type,
                    embedding_types=["float"],
                )
                return [list(e) for e in response.embeddings.float_]
            except Exception as e:
                if "rate" in str(e).lower() and attempt < self._max_retries:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning("Rate limit, %0.1f초 후 재시도", delay)
                    time.sleep(delay)
                    continue
                if attempt == self._max_retries:
                    raise RateLimitError("Cohere") from e
                raise
        raise RateLimitError("Cohere")
