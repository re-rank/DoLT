"""PlainTextParser 테스트."""

from __future__ import annotations

from pathlib import Path

from dolt.parsing.text_parser import PlainTextParser


def test_text_parser_basic(tmp_dir: Path):
    txt_file = tmp_dir / "sample.txt"
    txt_file.write_text(
        "제목입니다\n\n첫 번째 문단\n내용이 있습니다.\n\n두 번째 문단\n추가 내용.\n",
        encoding="utf-8",
    )

    parser = PlainTextParser()
    doc = parser.parse(str(txt_file), "test-txt")

    assert doc.doc_id == "test-txt"
    assert doc.total_chars > 0
    assert doc.total_pages == 1
    assert len(doc.sections) >= 2
    assert doc.metadata.get("title") == "제목입니다"


def test_text_parser_single_paragraph(tmp_dir: Path):
    txt_file = tmp_dir / "one.txt"
    txt_file.write_text("단일 문단 텍스트입니다.", encoding="utf-8")

    parser = PlainTextParser()
    doc = parser.parse(str(txt_file), "test-one")

    assert len(doc.sections) == 1
    assert doc.sections[0].title == "단일 문단 텍스트입니다."


def test_text_parser_empty(tmp_dir: Path):
    txt_file = tmp_dir / "empty.txt"
    txt_file.write_text("", encoding="utf-8")

    parser = PlainTextParser()
    doc = parser.parse(str(txt_file), "test-empty")

    assert doc.total_chars == 0
    assert doc.sections == []


def test_text_parser_supported_extensions():
    parser = PlainTextParser()
    assert parser.supported_extensions() == [".txt"]
