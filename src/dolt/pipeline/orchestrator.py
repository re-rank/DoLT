"""Pipeline Orchestrator — Ingest → Export 전체 흐름 제어."""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel, Field

from dolt.chunking.hybrid_chunker import HybridChunker
from dolt.chunking.structure_chunker import StructureChunker
from dolt.chunking.token_chunker import TokenChunker
from dolt.embedding.base import BaseEmbeddingProvider
from dolt.export.base import BaseExporter
from dolt.ingestion.ingestor import Ingestor
from dolt.metadata.enricher import MetadataEnricher
from dolt.models.chunk import Chunk, EmbeddedChunk
from dolt.models.config import ChunkMode, DoltConfig, EmbeddingProvider, ExportTarget
from dolt.models.document import IngestedDocument, IngestStatus, StructuredDocument
from dolt.parsing.registry import create_default_registry
from dolt.storage.local_store import LocalStore
from dolt.utils.logging import get_logger

logger = get_logger("pipeline")


class StageResult(BaseModel):
    stage: str
    status: str = "success"  # success | partial | failed
    count: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    doc_count: int = 0
    chunk_count: int = 0
    embedded_count: int = 0
    exported_count: int = 0
    elapsed_seconds: float = 0.0
    stages: dict[str, StageResult] = Field(default_factory=dict)


class PipelineOrchestrator:
    """전체 파이프라인을 순차 실행한다."""

    def __init__(self, config: DoltConfig) -> None:
        self.config = config
        self.store = LocalStore(config.storage.path)

    def run(
        self,
        source: str,
        skip_unchanged: bool = True,
        on_stage_complete: Callable[[str, StageResult], None] | None = None,
    ) -> PipelineResult:
        overall_start = time.time()
        result = PipelineResult()

        def _notify(stage: str) -> None:
            if on_stage_complete and stage in result.stages:
                on_stage_complete(stage, result.stages[stage])

        # 1. Ingest
        docs = self._ingest(source, result)
        _notify("ingest")
        if skip_unchanged:
            docs = [d for d in docs if d.status != IngestStatus.UNCHANGED]
        if not docs:
            logger.info("처리할 문서가 없습니다.")
            result.elapsed_seconds = time.time() - overall_start
            return result

        # 2. Parse
        parsed_docs = self._parse(docs, result)
        _notify("parse")

        # 3. Chunk
        all_chunks = self._chunk(parsed_docs, result)
        _notify("chunk")

        # 4. Enrich
        all_chunks = self._enrich(all_chunks, parsed_docs, result)
        _notify("enrich")

        # 5. Embed
        embedded_chunks = self._embed(all_chunks, result)
        _notify("embed")

        # 6. Export
        self._export(embedded_chunks, result)
        _notify("export")

        result.elapsed_seconds = time.time() - overall_start
        logger.info("파이프라인 완료: %.1f초", result.elapsed_seconds)
        return result

    def _ingest(self, source: str, result: PipelineResult) -> list[IngestedDocument]:
        start = time.time()
        ingestor = Ingestor(self.store)
        try:
            docs = ingestor.ingest(source)
        except Exception as e:
            result.stages["ingest"] = StageResult(
                stage="ingest", status="failed", errors=[str(e)],
                elapsed_seconds=time.time() - start,
            )
            return []

        result.doc_count = len(docs)
        result.stages["ingest"] = StageResult(
            stage="ingest", count=len(docs),
            elapsed_seconds=time.time() - start,
        )
        return docs

    def _parse(
        self, docs: list[IngestedDocument], result: PipelineResult,
    ) -> list[StructuredDocument]:
        start = time.time()
        registry = create_default_registry()
        ingestor = Ingestor(self.store)
        parsed: list[StructuredDocument] = []
        errors: list[str] = []

        for doc in docs:
            try:
                parser = registry.get_parser(doc.file_ext)
                file_path = str(ingestor.get_file_path(doc))
                structured = parser.parse(file_path, doc.doc_id)
                self.store.save_parsed(structured)
                parsed.append(structured)
            except Exception as e:
                errors.append(f"{doc.source}: {e}")
                logger.error("파싱 실패: %s — %s", doc.source, e)

        result.stages["parse"] = StageResult(
            stage="parse", count=len(parsed), errors=errors,
            status="partial" if errors else "success",
            elapsed_seconds=time.time() - start,
        )
        return parsed

    def _chunk(
        self, docs: list[StructuredDocument], result: PipelineResult,
    ) -> list[Chunk]:
        start = time.time()
        chunker = _create_chunker(self.config)
        all_chunks: list[Chunk] = []

        for doc in docs:
            chunks = chunker.chunk(doc)
            self.store.save_chunks(doc.doc_id, chunks)
            all_chunks.extend(chunks)

        result.chunk_count = len(all_chunks)
        result.stages["chunk"] = StageResult(
            stage="chunk", count=len(all_chunks),
            elapsed_seconds=time.time() - start,
        )
        return all_chunks

    def _enrich(
        self,
        chunks: list[Chunk],
        docs: list[StructuredDocument],
        result: PipelineResult,
    ) -> list[Chunk]:
        start = time.time()
        enricher = MetadataEnricher()

        enriched: list[Chunk] = []
        doc_map = {d.doc_id: d for d in docs}

        for chunk in chunks:
            doc = doc_map.get(chunk.doc_id)
            if doc:
                enriched.extend(enricher.enrich([chunk], doc))
            else:
                enriched.append(chunk)

        result.stages["enrich"] = StageResult(
            stage="enrich", count=len(enriched),
            elapsed_seconds=time.time() - start,
        )
        return enriched

    def _embed(
        self, chunks: list[Chunk], result: PipelineResult,
    ) -> list[EmbeddedChunk]:
        start = time.time()
        provider = _create_embedding_provider(self.config)
        texts = [c.content for c in chunks]

        try:
            vectors = provider.embed(texts)
        except Exception as e:
            result.stages["embed"] = StageResult(
                stage="embed", status="failed", errors=[str(e)],
                elapsed_seconds=time.time() - start,
            )
            return []

        embedded: list[EmbeddedChunk] = []
        for chunk, vector in zip(chunks, vectors):
            ec = EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                vector=vector,
                embedding_model=provider.model_name(),
                embedding_dim=provider.dimension(),
                metadata=chunk.metadata,
            )
            embedded.append(ec)

        # 문서별로 저장
        doc_ids = {c.doc_id for c in embedded}
        for doc_id in doc_ids:
            doc_chunks = [c for c in embedded if c.doc_id == doc_id]
            self.store.save_embeddings(doc_id, doc_chunks)

        result.embedded_count = len(embedded)
        result.stages["embed"] = StageResult(
            stage="embed", count=len(embedded),
            elapsed_seconds=time.time() - start,
        )
        return embedded

    def _export(
        self, chunks: list[EmbeddedChunk], result: PipelineResult,
    ) -> None:
        start = time.time()
        if not chunks:
            result.stages["export"] = StageResult(
                stage="export", count=0, elapsed_seconds=time.time() - start,
            )
            return

        exporter = _create_exporter(self.config)
        try:
            export_result = exporter.export(chunks)
        except Exception as e:
            result.stages["export"] = StageResult(
                stage="export", status="failed", errors=[str(e)],
                elapsed_seconds=time.time() - start,
            )
            return

        result.exported_count = export_result.success
        result.stages["export"] = StageResult(
            stage="export", count=export_result.success,
            status="partial" if export_result.failed > 0 else "success",
            errors=export_result.errors,
            elapsed_seconds=time.time() - start,
        )


def _create_chunker(config: DoltConfig):
    chunk_cfg = config.chunking
    if chunk_cfg.mode == ChunkMode.TOKEN:
        return TokenChunker(chunk_cfg)
    elif chunk_cfg.mode == ChunkMode.STRUCTURE:
        return StructureChunker(chunk_cfg)
    return HybridChunker(chunk_cfg)


def _create_embedding_provider(config: DoltConfig) -> BaseEmbeddingProvider:
    cfg = config.embedding
    if cfg.provider == EmbeddingProvider.OPENAI:
        from dolt.embedding.openai_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider(
            model=cfg.model or "text-embedding-3-small",
            batch_size=cfg.batch_size,
            max_retries=cfg.max_retries,
        )
    elif cfg.provider == EmbeddingProvider.COHERE:
        from dolt.embedding.cohere_provider import CohereEmbeddingProvider
        return CohereEmbeddingProvider(
            model=cfg.model or "embed-multilingual-v3.0",
            batch_size=cfg.batch_size,
            max_retries=cfg.max_retries,
        )
    else:
        from dolt.embedding.local_provider import LocalEmbeddingProvider
        return LocalEmbeddingProvider(
            model_name=cfg.model or "all-MiniLM-L6-v2",
            batch_size=cfg.batch_size,
        )


def _create_exporter(config: DoltConfig) -> BaseExporter:
    target = config.export.target
    if target == ExportTarget.QDRANT:
        from dolt.export.qdrant_exporter import QdrantExporter
        qdrant_cfg = config.export.qdrant
        return QdrantExporter(
            url=qdrant_cfg.url, port=qdrant_cfg.port,
            collection_name=qdrant_cfg.collection, api_key=qdrant_cfg.api_key,
        )
    elif target == ExportTarget.PINECONE:
        from dolt.export.pinecone_exporter import PineconeExporter
        pinecone_cfg = config.export.pinecone
        return PineconeExporter(
            index_name=pinecone_cfg.index, namespace=pinecone_cfg.namespace,
        )
    elif target == ExportTarget.WEAVIATE:
        from dolt.export.weaviate_exporter import WeaviateExporter
        weaviate_cfg = config.export.weaviate
        return WeaviateExporter(
            url=weaviate_cfg.url,
            collection_name=weaviate_cfg.collection,
            api_key=weaviate_cfg.api_key,
        )
    elif target == ExportTarget.POSTGRES:
        from dolt.export.postgres_exporter import PostgresExporter
        pg_cfg = config.export.postgres
        return PostgresExporter(
            dsn=pg_cfg.dsn, table=pg_cfg.table, use_pgvector=pg_cfg.use_pgvector,
        )
    elif target == ExportTarget.JSON:
        from dolt.export.json_exporter import JSONExporter
        json_cfg = config.export.json_export
        return JSONExporter(
            output_path=json_cfg.output,
            include_vectors=json_cfg.include_vectors,
        )
    else:
        from dolt.export.json_exporter import JSONExporter
        return JSONExporter()
