"""Metadata Enrichment 테스트."""

from __future__ import annotations

from pathlib import Path

from dolt.chunking.hybrid_chunker import HybridChunker
from dolt.metadata.enricher import MetadataEnricher
from dolt.models.config import ChunkConfig
from dolt.parsing.markdown_parser import MarkdownParser


def test_enricher_adds_metadata(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc")

    config = ChunkConfig(max_tokens=200)
    chunker = HybridChunker(config)
    chunks = chunker.chunk(doc)

    enricher = MetadataEnricher()
    enriched = enricher.enrich(chunks, doc)

    assert len(enriched) == len(chunks)
    for chunk in enriched:
        # BasicMetaPlugin
        assert "title" in chunk.metadata
        assert "source" in chunk.metadata
        # WordCountPlugin
        assert "word_count" in chunk.metadata
        assert "char_count" in chunk.metadata
