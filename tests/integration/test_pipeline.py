"""E2E 파이프라인 통합 테스트 — Ingest → Parse → Chunk → Enrich → Export(JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dolt.models.config import ChunkMode, DoltConfig, EmbeddingProvider, ExportTarget


@pytest.fixture
def sample_docs_dir(tmp_dir: Path) -> Path:
    """통합 테스트용 문서 디렉토리."""
    docs = tmp_dir / "docs"
    docs.mkdir()

    # Markdown
    (docs / "guide.md").write_text(
        "# 가이드\n\n## 소개\n\n이것은 통합 테스트 문서입니다.\n\n"
        "## 기능\n\n기능을 설명합니다.\n\n"
        "| 항목 | 값 |\n| --- | --- |\n| A | 1 |\n| B | 2 |\n",
        encoding="utf-8",
    )

    # HTML
    (docs / "page.html").write_text(
        "<html><head><title>테스트 페이지</title></head><body>"
        "<h1>제목</h1><p>본문 내용입니다.</p>"
        "<h2>섹션</h2><p>상세 설명.</p>"
        "</body></html>",
        encoding="utf-8",
    )

    # TXT
    (docs / "notes.txt").write_text(
        "릴리스 노트\n\nv1.0 출시되었습니다.\n주요 변경사항이 포함됩니다.\n\n"
        "버그 수정\n\n여러 버그가 수정되었습니다.\n",
        encoding="utf-8",
    )

    return docs


@pytest.fixture
def pipeline_config(tmp_dir: Path) -> DoltConfig:
    """통합 테스트용 설정."""
    return DoltConfig.model_validate({
        "storage": {"path": str(tmp_dir / ".dolt")},
        "chunking": {"mode": "hybrid", "max_tokens": 200, "overlap_tokens": 20},
        "embedding": {"provider": "openai"},
        "export": {
            "target": "json",
            "json": {"output": str(tmp_dir / "export.json"), "include_vectors": False},
        },
    })


def test_ingest_parse_chunk_pipeline(sample_docs_dir: Path, pipeline_config: DoltConfig):
    """Ingest → Parse → Chunk 단계를 순차 실행한다."""
    from dolt.chunking.hybrid_chunker import HybridChunker
    from dolt.ingestion.ingestor import Ingestor
    from dolt.metadata.enricher import MetadataEnricher
    from dolt.models.document import IngestStatus
    from dolt.parsing.registry import create_default_registry
    from dolt.storage.local_store import LocalStore

    store = LocalStore(pipeline_config.storage.path)
    ingestor = Ingestor(store)
    registry = create_default_registry()

    # Ingest
    docs = ingestor.ingest(str(sample_docs_dir))
    assert len(docs) == 3
    assert all(d.status == IngestStatus.NEW for d in docs)

    # Parse
    parsed_docs = []
    for doc in docs:
        parser = registry.get_parser(doc.file_ext)
        file_path = str(ingestor.get_file_path(doc))
        structured = parser.parse(file_path, doc.doc_id)
        store.save_parsed(structured)
        parsed_docs.append(structured)

    assert len(parsed_docs) == 3
    for pd in parsed_docs:
        assert pd.total_chars > 0

    # Chunk
    chunker = HybridChunker(pipeline_config.chunking)
    enricher = MetadataEnricher()
    total_chunks = 0

    for pd in parsed_docs:
        chunks = chunker.chunk(pd)
        chunks = enricher.enrich(chunks, pd)
        store.save_chunks(pd.doc_id, chunks)
        total_chunks += len(chunks)

        for c in chunks:
            assert c.content
            assert c.token_count > 0
            assert "word_count" in c.metadata

    assert total_chunks > 0


def test_full_pipeline_with_mock_embedding(
    sample_docs_dir: Path, pipeline_config: DoltConfig, tmp_dir: Path
):
    """Embed를 mock하여 전체 파이프라인(run)을 E2E 테스트한다."""
    from dolt.pipeline.orchestrator import PipelineOrchestrator

    fake_vectors = [[0.1] * 128]

    def _fake_embed(texts):
        return [[0.1] * 128 for _ in texts]

    mock_provider = MagicMock()
    mock_provider.embed = _fake_embed
    mock_provider.model_name.return_value = "mock-model"
    mock_provider.dimension.return_value = 128

    with patch(
        "dolt.pipeline.orchestrator._create_embedding_provider",
        return_value=mock_provider,
    ):
        orchestrator = PipelineOrchestrator(pipeline_config)
        result = orchestrator.run(str(sample_docs_dir))

    assert result.doc_count == 3
    assert result.chunk_count > 0
    assert result.embedded_count > 0
    assert result.exported_count > 0
    assert result.elapsed_seconds > 0

    # 각 단계 성공 확인
    for stage_name in ["ingest", "parse", "chunk", "enrich", "embed", "export"]:
        assert stage_name in result.stages
        assert result.stages[stage_name].status in ("success", "partial")

    # JSON export 파일 확인
    export_path = tmp_dir / "export.json"
    assert export_path.exists()

    with open(export_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_chunks"] == result.exported_count
    assert len(data["chunks"]) > 0
    assert "vector" not in data["chunks"][0]  # include_vectors=False


def test_pipeline_unchanged_skip(sample_docs_dir: Path, pipeline_config: DoltConfig):
    """이미 수집된 문서는 skip_unchanged=True일 때 건너뛴다."""
    from dolt.pipeline.orchestrator import PipelineOrchestrator

    mock_provider = MagicMock()
    mock_provider.embed = lambda texts: [[0.0] * 128 for _ in texts]
    mock_provider.model_name.return_value = "mock"
    mock_provider.dimension.return_value = 128

    with patch(
        "dolt.pipeline.orchestrator._create_embedding_provider",
        return_value=mock_provider,
    ):
        orchestrator = PipelineOrchestrator(pipeline_config)

        # 첫 실행
        r1 = orchestrator.run(str(sample_docs_dir))
        assert r1.doc_count == 3
        assert r1.chunk_count > 0

        # 두 번째 실행 — unchanged이므로 처리 건수 0
        r2 = orchestrator.run(str(sample_docs_dir))
        assert r2.chunk_count == 0


def test_pipeline_single_file(tmp_dir: Path, pipeline_config: DoltConfig):
    """단일 파일 파이프라인 실행."""
    from dolt.pipeline.orchestrator import PipelineOrchestrator

    md_file = tmp_dir / "single.md"
    md_file.write_text("# 단일 파일 테스트\n\n내용입니다.\n", encoding="utf-8")

    mock_provider = MagicMock()
    mock_provider.embed = lambda texts: [[0.0] * 64 for _ in texts]
    mock_provider.model_name.return_value = "mock"
    mock_provider.dimension.return_value = 64

    with patch(
        "dolt.pipeline.orchestrator._create_embedding_provider",
        return_value=mock_provider,
    ):
        orchestrator = PipelineOrchestrator(pipeline_config)
        result = orchestrator.run(str(md_file))

    assert result.doc_count == 1
    assert result.chunk_count > 0
