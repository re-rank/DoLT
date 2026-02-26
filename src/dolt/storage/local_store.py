"""로컬 저장소 (.dolt/) 관리."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dolt.models.chunk import Chunk, EmbeddedChunk
from dolt.models.document import IngestedDocument, StructuredDocument
from dolt.utils.logging import get_logger

logger = get_logger("storage")


class LocalStore:
    """DoLT 로컬 저장소 — .dolt/ 디렉토리 기반 중간 결과 관리."""

    def __init__(self, base_path: str = ".dolt") -> None:
        self.base = Path(base_path)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """필요한 하위 디렉토리를 생성한다."""
        for sub in ["parsed", "chunks", "embeddings", "exports", "cache"]:
            (self.base / sub).mkdir(parents=True, exist_ok=True)

    # ── Lock ──────────────────────────────────────────────

    def acquire_lock(self, timeout: int = 30) -> bool:
        """배타적 접근을 위한 락 획득. timeout 초 내 실패하면 False."""
        lock_file = self.base / "dolt.lock"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return True
            except FileExistsError:
                time.sleep(0.5)
        return False

    def release_lock(self) -> None:
        """락 파일 삭제."""
        lock_file = self.base / "dolt.lock"
        lock_file.unlink(missing_ok=True)

    # ── Documents ─────────────────────────────────────────

    def _documents_path(self) -> Path:
        return self.base / "documents.json"

    def load_documents(self) -> list[IngestedDocument]:
        """저장된 문서 목록을 로드한다."""
        path = self._documents_path()
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [IngestedDocument.model_validate(d) for d in data.get("documents", [])]

    def save_documents(self, docs: list[IngestedDocument]) -> None:
        """문서 목록을 저장한다."""
        payload = {
            "version": "1.0",
            "documents": [d.model_dump(mode="json") for d in docs],
        }
        with open(self._documents_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def find_document_by_source(self, source: str) -> IngestedDocument | None:
        """source 경로로 기존 문서를 검색한다."""
        for doc in self.load_documents():
            if doc.source == source:
                return doc
        return None

    def upsert_document(self, doc: IngestedDocument) -> None:
        """문서를 추가하거나 갱신한다."""
        docs = self.load_documents()
        for i, existing in enumerate(docs):
            if existing.doc_id == doc.doc_id or existing.source == doc.source:
                docs[i] = doc
                self.save_documents(docs)
                return
        docs.append(doc)
        self.save_documents(docs)

    # ── Parsed ────────────────────────────────────────────

    def save_parsed(self, doc: StructuredDocument) -> None:
        """파싱 결과를 저장한다."""
        path = self.base / "parsed" / f"{doc.doc_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def load_parsed(self, doc_id: str) -> StructuredDocument | None:
        """파싱 결과를 로드한다."""
        path = self.base / "parsed" / f"{doc_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return StructuredDocument.model_validate(json.load(f))

    # ── Chunks ────────────────────────────────────────────

    def save_chunks(self, doc_id: str, chunks: list[Chunk]) -> None:
        """청크 데이터를 저장한다."""
        path = self.base / "chunks" / f"{doc_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                [c.model_dump(mode="json") for c in chunks],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load_chunks(self, doc_id: str) -> list[Chunk]:
        """청크 데이터를 로드한다."""
        path = self.base / "chunks" / f"{doc_id}.json"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return [Chunk.model_validate(c) for c in json.load(f)]

    # ── Embeddings ────────────────────────────────────────

    def save_embeddings(self, doc_id: str, chunks: list[EmbeddedChunk]) -> None:
        """임베딩 데이터를 저장한다."""
        path = self.base / "embeddings" / f"{doc_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                [c.model_dump(mode="json") for c in chunks],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load_embeddings(self, doc_id: str) -> list[EmbeddedChunk]:
        """임베딩 데이터를 로드한다."""
        path = self.base / "embeddings" / f"{doc_id}.json"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return [EmbeddedChunk.model_validate(c) for c in json.load(f)]
