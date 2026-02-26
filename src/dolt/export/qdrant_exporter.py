"""Qdrant Export."""

from __future__ import annotations

from dolt.export.base import BaseExporter, ExportResult
from dolt.models.chunk import EmbeddedChunk
from dolt.utils.logging import get_logger

logger = get_logger("export.qdrant")


class QdrantExporter(BaseExporter):
    def __init__(
        self,
        url: str = "localhost",
        port: int = 6333,
        collection_name: str = "dolt_documents",
        api_key: str | None = None,
        recreate_collection: bool = False,
    ) -> None:
        self._url = url
        self._port = port
        self._collection = collection_name
        self._api_key = api_key
        self._recreate = recreate_collection

    def validate_connection(self) -> bool:
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception:
            return False

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        client = self._get_client()

        # 컬렉션 생성/확인
        dim = chunks[0].embedding_dim if chunks else 1536
        collections = [c.name for c in client.get_collections().collections]

        if self._recreate and self._collection in collections:
            client.delete_collection(self._collection)
            collections.remove(self._collection)

        if self._collection not in collections:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info("컬렉션 생성: %s (dim=%d)", self._collection, dim)

        # Upsert
        errors: list[str] = []
        success = 0
        batch_size = 100

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            points = [
                PointStruct(
                    id=chunk.chunk_id,
                    vector=chunk.vector,
                    payload={
                        "content": chunk.content,
                        "doc_id": chunk.doc_id,
                        "chunk_type": chunk.chunk_type.value,
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                        "embedding_model": chunk.embedding_model,
                        **chunk.metadata,
                    },
                )
                for chunk in batch
            ]
            try:
                client.upsert(collection_name=self._collection, points=points)
                success += len(batch)
            except Exception as e:
                errors.append(str(e))
                logger.error("Qdrant upsert 실패: %s", e)

        logger.info("Qdrant export 완료: %d/%d", success, len(chunks))
        return ExportResult(
            total=len(chunks),
            success=success,
            failed=len(chunks) - success,
            errors=errors,
            destination=f"qdrant://{self._url}:{self._port}/{self._collection}",
        )

    def _get_client(self):
        from qdrant_client import QdrantClient
        return QdrantClient(url=self._url, port=self._port, api_key=self._api_key)
