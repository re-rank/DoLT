"""Chunking 모듈 테스트."""

from __future__ import annotations

from pathlib import Path

from dolt.chunking.hybrid_chunker import HybridChunker
from dolt.chunking.token_chunker import TokenChunker
from dolt.models.chunk import ChunkType
from dolt.models.config import ChunkConfig
from dolt.parsing.markdown_parser import MarkdownParser


def test_token_chunker(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc")

    config = ChunkConfig(max_tokens=100, overlap_tokens=20)
    chunker = TokenChunker(config)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.content
        assert chunk.doc_id == "test-doc"
        assert chunk.token_count > 0


def test_hybrid_chunker(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc")

    config = ChunkConfig(max_tokens=200, overlap_tokens=30)
    chunker = HybridChunker(config)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0

    # 표와 코드블록이 독립 청크로 분리되었는지 확인
    types = [c.chunk_type for c in chunks]
    assert ChunkType.TABLE in types
    assert ChunkType.CODE in types


def test_chunk_index_sequential(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc")

    config = ChunkConfig(max_tokens=200)
    chunker = HybridChunker(config)
    chunks = chunker.chunk(doc)

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
