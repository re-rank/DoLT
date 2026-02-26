"""Ingestion 모듈 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from dolt.errors import FileNotFoundError, UnsupportedFormatError
from dolt.ingestion.ingestor import Ingestor
from dolt.models.document import IngestStatus
from dolt.storage.local_store import LocalStore


def test_ingest_file_success(store: LocalStore, sample_md: Path):
    ingestor = Ingestor(store)
    doc = ingestor.ingest_file(str(sample_md))

    assert doc.status == IngestStatus.NEW
    assert doc.file_ext == ".md"
    assert doc.file_name == "sample.md"
    assert doc.file_size_bytes > 0
    assert doc.hash


def test_ingest_file_not_found(store: LocalStore):
    ingestor = Ingestor(store)
    with pytest.raises(FileNotFoundError):
        ingestor.ingest_file("/nonexistent/path/file.pdf")


def test_ingest_file_unsupported_format(store: LocalStore, tmp_dir: Path):
    bad_file = tmp_dir / "test.exe"
    bad_file.write_text("fake")

    ingestor = Ingestor(store)
    with pytest.raises(UnsupportedFormatError):
        ingestor.ingest_file(str(bad_file))


def test_ingest_file_unchanged(store: LocalStore, sample_md: Path):
    ingestor = Ingestor(store)
    doc1 = ingestor.ingest_file(str(sample_md))
    assert doc1.status == IngestStatus.NEW

    doc2 = ingestor.ingest_file(str(sample_md))
    assert doc2.status == IngestStatus.UNCHANGED
    assert doc1.doc_id == doc2.doc_id


def test_ingest_file_updated(store: LocalStore, sample_md: Path):
    ingestor = Ingestor(store)
    doc1 = ingestor.ingest_file(str(sample_md))
    assert doc1.status == IngestStatus.NEW

    # 파일 수정
    sample_md.write_text("changed content", encoding="utf-8")
    doc2 = ingestor.ingest_file(str(sample_md))
    assert doc2.status == IngestStatus.UPDATED
    assert doc1.doc_id == doc2.doc_id


def test_ingest_directory(store: LocalStore, tmp_dir: Path, sample_md: Path):
    # 추가 파일 생성
    (tmp_dir / "another.md").write_text("# Another", encoding="utf-8")

    ingestor = Ingestor(store)
    docs = ingestor.ingest_directory(str(tmp_dir))

    assert len(docs) == 2
    assert all(d.status == IngestStatus.NEW for d in docs)


def test_ingest_empty_directory(store: LocalStore, tmp_dir: Path):
    empty_dir = tmp_dir / "empty"
    empty_dir.mkdir()

    ingestor = Ingestor(store)
    docs = ingestor.ingest_directory(str(empty_dir))

    assert docs == []
