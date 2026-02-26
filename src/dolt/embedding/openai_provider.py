"""OpenAI Embedding Provider."""

from __future__ import annotations

import os
import time

from dolt.embedding.base import BaseEmbeddingProvider
from dolt.errors import APIKeyMissingError, RateLimitError
from dolt.utils.logging import get_logger

logger = get_logger("embedding.openai")

_DEFAULT_MODEL = "text-embedding-3-small"
_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise APIKeyMissingError("OpenAI")
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def model_name(self) -> str:
        return self._model

    def dimension(self) -> int:
        return _MODEL_DIMS.get(self._model, 1536)

    def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI, RateLimitError as OpenAIRateLimit

        client = OpenAI(api_key=self._api_key)
        all_vectors: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            vectors = self._embed_batch(client, batch, OpenAIRateLimit)
            all_vectors.extend(vectors)
            logger.info("배치 %d/%d 완료 (%d chunks)", i // self._batch_size + 1,
                       (len(texts) + self._batch_size - 1) // self._batch_size,
                       len(batch))

        return all_vectors

    def _embed_batch(self, client, batch: list[str], rate_limit_cls: type) -> list[list[float]]:
        """단일 배치를 임베딩한다. 재시도 로직 포함."""
        for attempt in range(self._max_retries + 1):
            try:
                response = client.embeddings.create(model=self._model, input=batch)
                return [item.embedding for item in response.data]
            except rate_limit_cls:
                if attempt == self._max_retries:
                    raise RateLimitError("OpenAI")
                delay = self._retry_delay * (2 ** attempt)
                logger.warning("Rate limit 도달, %0.1f초 후 재시도 (%d/%d)",
                             delay, attempt + 1, self._max_retries)
                time.sleep(delay)
        raise RateLimitError("OpenAI")  # unreachable
