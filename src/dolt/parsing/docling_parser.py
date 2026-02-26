"""Docling 기반 PDF 파서 — OCR·이미지 테이블 지원."""

from __future__ import annotations

from collections import defaultdict

from dolt.errors import CorruptedFileError
from dolt.models.document import StructuredDocument
from dolt.models.section import Page, Section, Table
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing.docling")


class DoclingParser(BaseParser):
    """Docling 기반 PDF 파서. OCR 및 이미지 테이블 추출을 지원한다."""

    def __init__(self) -> None:
        self._converter = None

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def _get_converter(self):
        """DocumentConverter를 lazy 초기화한다 (모델 로딩 비용 최소화)."""
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
            logger.info("Docling DocumentConverter 초기화 완료")
        return self._converter

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        from docling_core.types.doc.labels import DocItemLabel

        try:
            result = self._get_converter().convert(file_path)
        except Exception as e:
            raise CorruptedFileError(file_path, str(e)) from e

        doc = result.document
        raw_text = doc.export_to_text()

        sections: list[Section] = []
        tables: list[Table] = []
        page_texts: dict[int, list[str]] = defaultdict(list)
        current_section_idx = -1
        sec_counter = 0
        tbl_counter = 0

        for item, _level in doc.iterate_items():
            page_no = (item.prov[0].page_no + 1) if item.prov else None

            if item.label in (DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER):
                sec_counter += 1
                heading_level = (
                    getattr(item, "level", 1)
                    if item.label == DocItemLabel.SECTION_HEADER
                    else 1
                )
                sections.append(
                    Section(
                        section_id=f"sec-{sec_counter:03d}",
                        title=item.text,
                        level=heading_level,
                        content="",
                        page_number=page_no,
                    )
                )
                current_section_idx = len(sections) - 1
                if page_no:
                    page_texts[page_no].append(item.text)

            elif item.label == DocItemLabel.TABLE:
                tbl_counter += 1
                headers, rows = _extract_table_data(item)
                md = _to_markdown_table(headers, rows)
                tables.append(
                    Table(
                        table_id=f"tbl-{tbl_counter}",
                        headers=headers,
                        rows=rows,
                        page_number=page_no,
                        markdown=md,
                    )
                )
                if current_section_idx >= 0:
                    sections[current_section_idx].content += md + "\n"
                if page_no:
                    page_texts[page_no].append(md)

            elif hasattr(item, "text") and item.text:
                if current_section_idx >= 0:
                    sections[current_section_idx].content += item.text + "\n"
                if page_no:
                    page_texts[page_no].append(item.text)

        # 섹션 content 트리밍 + offset 계산
        for sec in sections:
            sec.content = sec.content.strip()
        _assign_offsets(sections, raw_text)

        # 페이지 구성
        pages: list[Page] = []
        offset = 0
        for page_num in sorted(page_texts.keys()):
            text = "\n".join(page_texts[page_num])
            pages.append(
                Page(
                    page_number=page_num,
                    text=text,
                    start_offset=offset,
                    end_offset=offset + len(text),
                )
            )
            offset += len(text)

        total_pages = len(doc.pages) if doc.pages else len(pages)

        return StructuredDocument(
            doc_id=doc_id,
            source=file_path,
            raw_text=raw_text,
            pages=pages,
            sections=sections,
            tables=tables,
            metadata={},
            total_chars=len(raw_text),
            total_pages=total_pages,
        )


def _extract_table_data(table_item) -> tuple[list[str], list[list[str]]]:
    """Docling 테이블에서 headers와 rows를 추출한다."""
    try:
        data = table_item.data
        if not data or not data.grid:
            return [], []
        grid = data.grid
        headers = [cell.text for cell in grid[0]]
        rows = [[cell.text for cell in row] for row in grid[1:]]
        return headers, rows
    except Exception:
        return [], []


def _assign_offsets(sections: list[Section], raw_text: str) -> None:
    """섹션의 start_offset / end_offset을 raw_text 기준으로 설정한다."""
    if not sections:
        return

    search_from = 0
    positions: list[int] = []
    for sec in sections:
        pos = raw_text.find(sec.title, search_from)
        positions.append(pos)
        if pos != -1:
            search_from = pos + len(sec.title)

    for i, sec in enumerate(sections):
        if positions[i] == -1:
            continue
        sec.start_offset = positions[i]
        # end_offset = 다음 섹션 시작 or 텍스트 끝
        sec.end_offset = len(raw_text)
        for j in range(i + 1, len(sections)):
            if positions[j] != -1:
                sec.end_offset = positions[j]
                break


def _to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """헤더와 행 데이터를 Markdown 테이블로 변환한다."""
    if not headers:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        padded = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
    return "\n".join(lines)
