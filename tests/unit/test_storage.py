"""로컬 저장소 테스트."""

from __future__ import annotations

from dolt.models.document import IngestedDocument, IngestStatus
from dolt.storage.local_store import LocalStore


def test_save_and_load_documents(store: LocalStore):
    doc = IngestedDocument(
        doc_id="test-001",
        source="/path/to/file.pdf",
        file_name="file.pdf",
        file_ext=".pdf",
        file_size_bytes=1024,
        hash="abc123",
        status=IngestStatus.NEW,
        mime_type="application/pdf",
    )
    store.upsert_document(doc)

    loaded = store.load_documents()
    assert len(loaded) == 1
    assert loaded[0].doc_id == "test-001"


def test_find_document_by_source(store: LocalStore):
    doc = IngestedDocument(
        doc_id="test-002",
        source="/path/to/file.md",
        file_name="file.md",
        file_ext=".md",
        file_size_bytes=512,
        hash="def456",
        status=IngestStatus.NEW,
        mime_type="text/markdown",
    )
    store.upsert_document(doc)

    found = store.find_document_by_source("/path/to/file.md")
    assert found is not None
    assert found.doc_id == "test-002"

    not_found = store.find_document_by_source("/nonexistent")
    assert not_found is None


def test_upsert_updates_existing(store: LocalStore):
    doc = IngestedDocument(
        doc_id="test-003",
        source="/path/to/file.pdf",
        file_name="file.pdf",
        file_ext=".pdf",
        file_size_bytes=1024,
        hash="abc",
        status=IngestStatus.NEW,
        mime_type="application/pdf",
    )
    store.upsert_document(doc)

    updated = doc.model_copy(update={"hash": "xyz", "status": IngestStatus.UPDATED})
    store.upsert_document(updated)

    loaded = store.load_documents()
    assert len(loaded) == 1
    assert loaded[0].hash == "xyz"
    assert loaded[0].status == IngestStatus.UPDATED
