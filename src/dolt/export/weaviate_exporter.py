"""Weaviate Export."""

from __future__ import annotations

from dolt.export.base import BaseExporter, ExportResult
from dolt.models.chunk import EmbeddedChunk
from dolt.utils.logging import get_logger

logger = get_logger("export.weaviate")


class WeaviateExporter(BaseExporter):
    def __init__(
        self,
        url: str = "http://localhost:8080",
        collection_name: str = "DoltDocuments",
        api_key: str | None = None,
    ) -> None:
        self._url = url
        self._collection = collection_name
        self._api_key = api_key

    def validate_connection(self) -> bool:
        try:
            client = self._get_client()
            client.is_ready()
            client.close()
            return True
        except Exception:
            return False

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        import weaviate.classes.config as wvc

        client = self._get_client()
        errors: list[str] = []
        success = 0

        try:
            # 컬렉션 생성 (없으면)
            if not client.collections.exists(self._collection):
                dim = chunks[0].embedding_dim if chunks else 1536
                client.collections.create(
                    name=self._collection,
                    vectorizer_config=wvc.Configure.Vectorizer.none(),
                    properties=[
                        wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="doc_id", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="chunk_type", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="chunk_index", data_type=wvc.DataType.INT),
                        wvc.Property(name="token_count", data_type=wvc.DataType.INT),
                        wvc.Property(name="embedding_model", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="metadata_json", data_type=wvc.DataType.TEXT),
                    ],
                )
                logger.info("컬렉션 생성: %s (dim=%d)", self._collection, dim)

            collection = client.collections.get(self._collection)

            # 배치 삽입
            import json

            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                with collection.batch.dynamic() as batch_ctx:
                    for chunk in batch:
                        try:
                            batch_ctx.add_object(
                                properties={
                                    "content": chunk.content,
                                    "doc_id": chunk.doc_id,
                                    "chunk_type": chunk.chunk_type.value,
                                    "chunk_index": chunk.chunk_index,
                                    "token_count": chunk.token_count,
                                    "embedding_model": chunk.embedding_model,
                                    "metadata_json": json.dumps(
                                        chunk.metadata, ensure_ascii=False
                                    ),
                                },
                                vector=chunk.vector,
                                uuid=chunk.chunk_id,
                            )
                            success += 1
                        except Exception as e:
                            errors.append(f"{chunk.chunk_id}: {e}")
                            logger.error("Weaviate 삽입 실패: %s — %s", chunk.chunk_id, e)
        finally:
            client.close()

        logger.info("Weaviate export 완료: %d/%d", success, len(chunks))
        return ExportResult(
            total=len(chunks),
            success=success,
            failed=len(chunks) - success,
            errors=errors,
            destination=f"weaviate://{self._url}/{self._collection}",
        )

    def _get_client(self):
        import weaviate

        if self._api_key:
            auth = weaviate.auth.AuthApiKey(api_key=self._api_key)
            host = self._url.replace("http://", "").replace("https://", "")
            host_part = host.split(":")[0]
            has_port = ":" in self._url.split("//")[-1]
            port = int(self._url.split(":")[-1]) if has_port else 8080
            return weaviate.connect_to_custom(
                http_host=host_part,
                http_port=port,
                http_secure=self._url.startswith("https"),
                auth_credentials=auth,
            )
        return weaviate.connect_to_local()
