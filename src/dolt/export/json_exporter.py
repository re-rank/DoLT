"""JSON Export — 파일로 내보내기."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dolt.export.base import BaseExporter, ExportResult
from dolt.models.chunk import EmbeddedChunk
from dolt.utils.logging import get_logger

logger = get_logger("export.json")


class JSONExporter(BaseExporter):
    def __init__(
        self,
        output_path: str = ".dolt/export.json",
        include_vectors: bool = True,
        pretty: bool = True,
    ) -> None:
        self._output_path = output_path
        self._include_vectors = include_vectors
        self._pretty = pretty

    def validate_connection(self) -> bool:
        # 파일 시스템 기반이므로 항상 True
        parent = Path(self._output_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        return True

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        self.validate_connection()

        serialized: list[dict] = []
        for chunk in chunks:
            data = chunk.model_dump(mode="json")
            if not self._include_vectors:
                data.pop("vector", None)
            serialized.append(data)

        output = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_chunks": len(serialized),
            "embedding_model": chunks[0].embedding_model if chunks else "",
            "embedding_dim": chunks[0].embedding_dim if chunks else 0,
            "chunks": serialized,
        }

        indent = 2 if self._pretty else None
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=indent)

        logger.info("JSON export 완료: %s (%d chunks)", self._output_path, len(serialized))

        return ExportResult(
            total=len(chunks),
            success=len(chunks),
            failed=0,
            destination=f"file://{self._output_path}",
        )
