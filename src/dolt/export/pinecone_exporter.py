"""Pinecone Export."""

from __future__ import annotations

import os

from dolt.errors import APIKeyMissingError
from dolt.export.base import BaseExporter, ExportResult
from dolt.models.chunk import EmbeddedChunk
from dolt.utils.logging import get_logger

logger = get_logger("export.pinecone")


class PineconeExporter(BaseExporter):
    def __init__(
        self,
        api_key: str | None = None,
        index_name: str = "dolt-documents",
        namespace: str = "",
    ) -> None:
        self._api_key = api_key or os.environ.get("PINECONE_API_KEY")
        if not self._api_key:
            raise APIKeyMissingError("Pinecone")
        self._index_name = index_name
        self._namespace = namespace

    def validate_connection(self) -> bool:
        try:
            index = self._get_index()
            index.describe_index_stats()
            return True
        except Exception:
            return False

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        index = self._get_index()
        errors: list[str] = []
        success = 0
        batch_size = 100

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = [
                {
                    "id": chunk.chunk_id,
                    "values": chunk.vector,
                    "metadata": {
                        "content": chunk.content[:40960],  # Pinecone metadata 크기 제한
                        "doc_id": chunk.doc_id,
                        "chunk_type": chunk.chunk_type.value,
                        "chunk_index": chunk.chunk_index,
                        **{k: v for k, v in chunk.metadata.items()
                           if isinstance(v, str | int | float | bool)},
                    },
                }
                for chunk in batch
            ]
            try:
                index.upsert(vectors=vectors, namespace=self._namespace)
                success += len(batch)
            except Exception as e:
                errors.append(str(e))
                logger.error("Pinecone upsert 실패: %s", e)

        logger.info("Pinecone export 완료: %d/%d", success, len(chunks))
        return ExportResult(
            total=len(chunks),
            success=success,
            failed=len(chunks) - success,
            errors=errors,
            destination=f"pinecone://{self._index_name}/{self._namespace}",
        )

    def _get_index(self):
        from pinecone import Pinecone
        pc = Pinecone(api_key=self._api_key)
        return pc.Index(self._index_name)
