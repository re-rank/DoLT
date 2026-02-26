"""통합 Ingestor — 파일, 디렉토리, URL 수집."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

import httpx

from dolt.errors import (
    FileTooLargeError,
    FileNotFoundError,
    UnsupportedFormatError,
    URLFetchError,
)
from dolt.models.document import IngestedDocument, IngestStatus
from dolt.storage.local_store import LocalStore
from dolt.utils.hashing import hash_file
from dolt.utils.logging import get_logger

logger = get_logger("ingestion")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".md", ".txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class Ingestor:
    """파일, 디렉토리, URL에서 문서를 수집한다."""

    def __init__(self, store: LocalStore) -> None:
        self.store = store

    def ingest(self, source: str, **kwargs) -> list[IngestedDocument]:  # type: ignore[no-untyped-def]
        """소스 타입을 자동 판별하여 수집한다."""
        if source.startswith(("http://", "https://")):
            return [self.ingest_url(source)]

        path = Path(source)
        if path.is_dir():
            return self.ingest_directory(
                str(path),
                recursive=kwargs.get("recursive", True),
                glob_pattern=kwargs.get("pattern", "*"),
            )

        return [self.ingest_file(str(path))]

    def ingest_file(self, file_path: str) -> IngestedDocument:
        """단일 파일을 수집한다."""
        path = Path(file_path).resolve()

        # 존재 확인
        if not path.exists():
            raise FileNotFoundError(str(path))

        # 포맷 확인
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(ext)

        # 크기 확인
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise FileTooLargeError(str(path), size / (1024 * 1024))

        # 해시 계산
        file_hash = hash_file(path)

        # 변경 감지
        source_str = str(path)
        existing = self.store.find_document_by_source(source_str)

        if existing and existing.hash == file_hash:
            logger.info("변경 없음 (unchanged): %s", source_str)
            return existing.model_copy(update={"status": IngestStatus.UNCHANGED})

        status = IngestStatus.UPDATED if existing else IngestStatus.NEW
        doc_id = existing.doc_id if existing else str(uuid.uuid4())

        mime_type, _ = mimetypes.guess_type(str(path))

        doc = IngestedDocument(
            doc_id=doc_id,
            source=source_str,
            file_name=path.name,
            file_ext=ext,
            file_size_bytes=size,
            hash=file_hash,
            status=status,
            mime_type=mime_type or "application/octet-stream",
        )

        self.store.upsert_document(doc)
        logger.info("수집 완료 (%s): %s [%s]", status.value, source_str, doc_id)
        return doc

    def ingest_directory(
        self,
        dir_path: str,
        recursive: bool = True,
        glob_pattern: str = "*",
    ) -> list[IngestedDocument]:
        """디렉토리 내 파일을 일괄 수집한다."""
        path = Path(dir_path).resolve()
        if not path.is_dir():
            raise FileNotFoundError(str(path))

        pattern = f"**/{glob_pattern}" if recursive else glob_pattern
        results: list[IngestedDocument] = []
        errors: list[str] = []

        for file_path in sorted(path.glob(pattern)):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                doc = self.ingest_file(str(file_path))
                results.append(doc)
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                logger.warning("수집 실패: %s — %s", file_path, e)

        logger.info(
            "디렉토리 수집 완료: %d 성공, %d 실패",
            len(results),
            len(errors),
        )
        return results

    def ingest_url(self, url: str) -> IngestedDocument:
        """URL에서 문서를 수집한다."""
        try:
            with httpx.Client(timeout=30, follow_redirects=True, max_redirects=5) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise URLFetchError(url, str(e)) from e

        # Content-Type으로 확장자 추론
        content_type = response.headers.get("content-type", "")
        ext = _content_type_to_ext(content_type)
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(ext or content_type)

        # 크기 확인
        content = response.content
        if len(content) > MAX_FILE_SIZE:
            raise FileTooLargeError(url, len(content) / (1024 * 1024))

        # 캐시 파일에 저장
        file_hash = _hash_bytes_inline(content)
        cache_path = self.store.base / "cache" / f"{file_hash}{ext}"
        cache_path.write_bytes(content)

        # 변경 감지
        existing = self.store.find_document_by_source(url)
        if existing and existing.hash == file_hash:
            logger.info("변경 없음 (unchanged): %s", url)
            return existing.model_copy(update={"status": IngestStatus.UNCHANGED})

        status = IngestStatus.UPDATED if existing else IngestStatus.NEW
        doc_id = existing.doc_id if existing else str(uuid.uuid4())

        doc = IngestedDocument(
            doc_id=doc_id,
            source=url,
            file_name=cache_path.name,
            file_ext=ext,
            file_size_bytes=len(content),
            hash=file_hash,
            status=status,
            mime_type=content_type.split(";")[0].strip(),
        )

        self.store.upsert_document(doc)
        logger.info("URL 수집 완료 (%s): %s [%s]", status.value, url, doc_id)
        return doc

    def get_file_path(self, doc: IngestedDocument) -> Path:
        """IngestedDocument의 실제 파일 경로를 반환한다. URL은 캐시 경로."""
        if doc.source.startswith(("http://", "https://")):
            return self.store.base / "cache" / f"{doc.hash}{doc.file_ext}"
        return Path(doc.source)


def _content_type_to_ext(content_type: str) -> str:
    """Content-Type → 확장자 변환."""
    ct = content_type.split(";")[0].strip().lower()
    mapping = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/html": ".html",
        "text/markdown": ".md",
        "text/plain": ".txt",
    }
    return mapping.get(ct, "")


def _hash_bytes_inline(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()
