"""Pipeline Orchestrator 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dolt.models.config import (
    ChunkMode,
    DoltConfig,
    EmbeddingProvider,
    ExportTarget,
)
from dolt.pipeline.orchestrator import (
    PipelineOrchestrator,
    _create_chunker,
    _create_exporter,
)


def test_create_chunker_token():
    cfg = DoltConfig.model_validate({"chunking": {"mode": "token"}})
    from dolt.chunking.token_chunker import TokenChunker

    chunker = _create_chunker(cfg)
    assert isinstance(chunker, TokenChunker)


def test_create_chunker_structure():
    cfg = DoltConfig.model_validate({"chunking": {"mode": "structure"}})
    from dolt.chunking.structure_chunker import StructureChunker

    chunker = _create_chunker(cfg)
    assert isinstance(chunker, StructureChunker)


def test_create_chunker_hybrid():
    cfg = DoltConfig.model_validate({"chunking": {"mode": "hybrid"}})
    from dolt.chunking.hybrid_chunker import HybridChunker

    chunker = _create_chunker(cfg)
    assert isinstance(chunker, HybridChunker)


def test_create_exporter_json(tmp_dir: Path):
    cfg = DoltConfig.model_validate({
        "export": {"target": "json", "json": {"output": str(tmp_dir / "out.json")}},
    })
    from dolt.export.json_exporter import JSONExporter

    exporter = _create_exporter(cfg)
    assert isinstance(exporter, JSONExporter)


def test_create_exporter_qdrant():
    cfg = DoltConfig.model_validate({"export": {"target": "qdrant"}})
    from dolt.export.qdrant_exporter import QdrantExporter

    exporter = _create_exporter(cfg)
    assert isinstance(exporter, QdrantExporter)


def test_create_exporter_pinecone(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    cfg = DoltConfig.model_validate({"export": {"target": "pinecone"}})
    from dolt.export.pinecone_exporter import PineconeExporter

    exporter = _create_exporter(cfg)
    assert isinstance(exporter, PineconeExporter)


def test_create_exporter_weaviate():
    cfg = DoltConfig.model_validate({"export": {"target": "weaviate"}})
    from dolt.export.weaviate_exporter import WeaviateExporter

    exporter = _create_exporter(cfg)
    assert isinstance(exporter, WeaviateExporter)


def test_create_exporter_postgres():
    cfg = DoltConfig.model_validate({"export": {"target": "postgres"}})
    from dolt.export.postgres_exporter import PostgresExporter

    exporter = _create_exporter(cfg)
    assert isinstance(exporter, PostgresExporter)


def test_pipeline_ingest_failure(tmp_dir: Path):
    """존재하지 않는 소스에 대해 ingest가 실패하면 빈 결과를 반환한다."""
    cfg = DoltConfig.model_validate({"storage": {"path": str(tmp_dir / ".dolt")}})
    orchestrator = PipelineOrchestrator(cfg)
    result = orchestrator.run("/nonexistent/path")

    assert result.doc_count == 0
    assert "ingest" in result.stages
    assert result.stages["ingest"].status == "failed"


def test_pipeline_result_stages(tmp_dir: Path, sample_md: Path):
    """정상 파이프라인 실행 시 모든 stage가 결과에 포함된다."""
    cfg = DoltConfig.model_validate({
        "storage": {"path": str(tmp_dir / ".dolt")},
        "export": {"target": "json", "json": {"output": str(tmp_dir / "out.json")}},
    })

    mock_provider = MagicMock()
    mock_provider.embed = lambda texts: [[0.0] * 64 for _ in texts]
    mock_provider.model_name.return_value = "mock"
    mock_provider.dimension.return_value = 64

    with patch(
        "dolt.pipeline.orchestrator._create_embedding_provider",
        return_value=mock_provider,
    ):
        orchestrator = PipelineOrchestrator(cfg)
        result = orchestrator.run(str(sample_md))

    assert result.doc_count == 1
    for stage in ["ingest", "parse", "chunk", "enrich", "embed", "export"]:
        assert stage in result.stages
