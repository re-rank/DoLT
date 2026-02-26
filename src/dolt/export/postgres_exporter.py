"""PostgreSQL + pgvector Export."""

from __future__ import annotations

import json
import os

from dolt.export.base import BaseExporter, ExportResult
from dolt.models.chunk import EmbeddedChunk
from dolt.utils.logging import get_logger

logger = get_logger("export.postgres")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    vector vector({dim})
);
"""

_CREATE_TABLE_SQL_NO_VECTOR = """
CREATE TABLE IF NOT EXISTS {table} (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    vector FLOAT8[]
);
"""

_UPSERT_SQL = """
INSERT INTO {table} (
    chunk_id, doc_id, content, chunk_type, chunk_index,
    token_count, embedding_model, embedding_dim, metadata, vector
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chunk_id) DO UPDATE SET
    content = EXCLUDED.content,
    chunk_type = EXCLUDED.chunk_type,
    chunk_index = EXCLUDED.chunk_index,
    token_count = EXCLUDED.token_count,
    embedding_model = EXCLUDED.embedding_model,
    embedding_dim = EXCLUDED.embedding_dim,
    metadata = EXCLUDED.metadata,
    vector = EXCLUDED.vector;
"""


class PostgresExporter(BaseExporter):
    def __init__(
        self,
        dsn: str | None = None,
        table: str = "dolt_chunks",
        use_pgvector: bool = True,
    ) -> None:
        self._dsn = dsn or os.environ.get(
            "DATABASE_URL", "postgresql://localhost:5432/dolt"
        )
        self._table = table
        self._use_pgvector = use_pgvector

    def validate_connection(self) -> bool:
        try:
            conn = self._get_connection()
            conn.close()
            return True
        except Exception:
            return False

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        conn = self._get_connection()
        errors: list[str] = []
        success = 0

        try:
            cur = conn.cursor()

            # pgvector 확장 활성화
            if self._use_pgvector:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # 테이블 생성
            dim = chunks[0].embedding_dim if chunks else 1536
            if self._use_pgvector:
                cur.execute(_CREATE_TABLE_SQL.format(table=self._table, dim=dim))
            else:
                cur.execute(_CREATE_TABLE_SQL_NO_VECTOR.format(table=self._table))

            conn.commit()

            # 배치 upsert
            for chunk in chunks:
                try:
                    vector_val = chunk.vector
                    if self._use_pgvector:
                        # pgvector 형식: '[1.0, 2.0, ...]'
                        vector_val = f"[{','.join(str(v) for v in chunk.vector)}]"

                    cur.execute(
                        _UPSERT_SQL.format(table=self._table),
                        (
                            chunk.chunk_id,
                            chunk.doc_id,
                            chunk.content,
                            chunk.chunk_type.value,
                            chunk.chunk_index,
                            chunk.token_count,
                            chunk.embedding_model,
                            chunk.embedding_dim,
                            json.dumps(chunk.metadata, ensure_ascii=False),
                            vector_val,
                        ),
                    )
                    success += 1
                except Exception as e:
                    errors.append(f"{chunk.chunk_id}: {e}")
                    logger.error("Postgres upsert 실패: %s — %s", chunk.chunk_id, e)

            conn.commit()
        finally:
            conn.close()

        logger.info("Postgres export 완료: %d/%d", success, len(chunks))
        return ExportResult(
            total=len(chunks),
            success=success,
            failed=len(chunks) - success,
            errors=errors,
            destination=f"postgres://{self._table}",
        )

    def _get_connection(self):
        import psycopg2

        return psycopg2.connect(self._dsn)
