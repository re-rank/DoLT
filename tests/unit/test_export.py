"""Export 모듈 테스트."""

from __future__ import annotations

import json
from pathlib import Path

from dolt.export.json_exporter import JSONExporter
from dolt.models.chunk import ChunkType, EmbeddedChunk


def _make_chunk(chunk_id: str = "chunk-001", doc_id: str = "doc-001") -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        content="테스트 청크 내용입니다.",
        chunk_type=ChunkType.TEXT,
        chunk_index=0,
        token_count=10,
        vector=[0.1, 0.2, 0.3],
        embedding_model="test-model",
        embedding_dim=3,
        metadata={"source": "test.md"},
    )


def test_json_exporter_basic(tmp_dir: Path):
    output = str(tmp_dir / "export.json")
    exporter = JSONExporter(output_path=output)
    chunks = [_make_chunk("c1"), _make_chunk("c2", "doc-002")]

    result = exporter.export(chunks)

    assert result.total == 2
    assert result.success == 2
    assert result.failed == 0

    with open(output, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_chunks"] == 2
    assert data["embedding_model"] == "test-model"
    assert len(data["chunks"]) == 2
    assert data["chunks"][0]["vector"] == [0.1, 0.2, 0.3]


def test_json_exporter_exclude_vectors(tmp_dir: Path):
    output = str(tmp_dir / "no_vec.json")
    exporter = JSONExporter(output_path=output, include_vectors=False)
    chunks = [_make_chunk()]

    exporter.export(chunks)

    with open(output, encoding="utf-8") as f:
        data = json.load(f)

    assert "vector" not in data["chunks"][0]


def test_json_exporter_empty(tmp_dir: Path):
    output = str(tmp_dir / "empty.json")
    exporter = JSONExporter(output_path=output)

    # 빈 리스트 — IndexError 없이 작동해야 함
    result = exporter.export([])

    assert result.total == 0
    assert result.success == 0

    with open(output, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_chunks"] == 0
    assert data["chunks"] == []


def test_json_exporter_destination(tmp_dir: Path):
    output = str(tmp_dir / "out.json")
    exporter = JSONExporter(output_path=output)
    result = exporter.export([_make_chunk()])

    assert output in result.destination
