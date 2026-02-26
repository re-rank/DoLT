"""Parsing 모듈 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from dolt.parsing.markdown_parser import MarkdownParser


def test_markdown_parser_sections(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc-001")

    assert doc.doc_id == "test-doc-001"
    assert doc.total_pages == 1
    assert len(doc.sections) > 0

    # 최상위 섹션 확인
    titles = [s.title for s in doc.sections]
    assert "DoLT 테스트 문서" in titles
    assert "1장 소개" in titles


def test_markdown_parser_code_blocks(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc-001")

    assert len(doc.code_blocks) == 1
    assert doc.code_blocks[0].language == "python"
    assert "hello" in doc.code_blocks[0].content


def test_markdown_parser_tables(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc-001")

    assert len(doc.tables) == 1
    assert "모드" in doc.tables[0].headers


def test_markdown_parser_raw_text(sample_md: Path):
    parser = MarkdownParser()
    doc = parser.parse(str(sample_md), "test-doc-001")

    assert doc.total_chars > 0
    assert "DoLT" in doc.raw_text


def test_markdown_parser_empty_file(tmp_dir: Path):
    empty_md = tmp_dir / "empty.md"
    empty_md.write_text("", encoding="utf-8")

    parser = MarkdownParser()
    doc = parser.parse(str(empty_md), "test-empty")

    assert doc.total_chars == 0
    assert doc.sections == []
