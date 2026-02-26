"""PyMuPDF 기반 PDF 파서."""

from __future__ import annotations

from dolt.errors import CorruptedFileError
from dolt.models.document import StructuredDocument
from dolt.models.section import Page, Section, Table
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing.pdf")


class PDFParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        import fitz  # PyMuPDF

        try:
            pdf = fitz.open(file_path)
        except Exception as e:
            raise CorruptedFileError(file_path, str(e)) from e

        pages: list[Page] = []
        sections: list[Section] = []
        tables: list[Table] = []
        all_text_parts: list[str] = []
        offset = 0
        section_counter = 0

        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text("text")

            start = offset
            end = offset + len(text)
            pages.append(
                Page(
                    page_number=page_num + 1,
                    text=text,
                    start_offset=start,
                    end_offset=end,
                )
            )
            all_text_parts.append(text)
            offset = end

            # 섹션 추출: 폰트 크기 기반 헤딩 판별
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:  # 텍스트 블록만
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_size = span.get("size", 0)
                        span_text = span.get("text", "").strip()
                        if not span_text:
                            continue
                        # 14pt 이상을 헤딩으로 판별
                        if font_size >= 18:
                            level = 1
                        elif font_size >= 16:
                            level = 2
                        elif font_size >= 14:
                            level = 3
                        else:
                            continue

                        section_counter += 1
                        sections.append(
                            Section(
                                section_id=f"sec-{section_counter:03d}",
                                title=span_text,
                                level=level,
                                content="",  # 본문은 후처리로 채움
                                page_number=page_num + 1,
                            )
                        )

            # 표 추출
            try:
                page_tables = page.find_tables()
                for t_idx, tab in enumerate(page_tables.tables):
                    data = tab.extract()
                    if not data:
                        continue
                    headers = [str(c) if c else "" for c in data[0]]
                    rows = [[str(c) if c else "" for c in row] for row in data[1:]]
                    md = _to_markdown_table(headers, rows)
                    tables.append(
                        Table(
                            table_id=f"tbl-{page_num + 1}-{t_idx + 1}",
                            headers=headers,
                            rows=rows,
                            page_number=page_num + 1,
                            markdown=md,
                        )
                    )
            except Exception:
                pass  # 표 추출 실패는 무시

        raw_text = "".join(all_text_parts)

        # 섹션 본문 채우기: 각 섹션 제목 위치 ~ 다음 섹션 제목 위치
        _fill_section_content(sections, raw_text)

        # 문서 메타데이터
        meta = pdf.metadata or {}
        doc_metadata = {
            k: v for k, v in {
                "title": meta.get("title"),
                "author": meta.get("author"),
                "subject": meta.get("subject"),
                "creator": meta.get("creator"),
            }.items() if v
        }

        pdf.close()

        return StructuredDocument(
            doc_id=doc_id,
            source=file_path,
            raw_text=raw_text,
            pages=pages,
            sections=sections,
            tables=tables,
            metadata=doc_metadata,
            total_chars=len(raw_text),
            total_pages=len(pages),
        )


def _fill_section_content(sections: list[Section], raw_text: str) -> None:
    """각 섹션의 content와 offset을 채운다."""
    if not sections:
        return

    for i, sec in enumerate(sections):
        title_pos = raw_text.find(sec.title)
        if title_pos == -1:
            continue

        start = title_pos + len(sec.title)
        # 다음 섹션 제목까지
        if i + 1 < len(sections):
            next_pos = raw_text.find(sections[i + 1].title, start)
            end = next_pos if next_pos != -1 else len(raw_text)
        else:
            end = len(raw_text)

        sec.content = raw_text[start:end].strip()
        sec.start_offset = title_pos
        sec.end_offset = end


def _to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """헤더와 행 데이터를 Markdown 테이블로 변환한다."""
    if not headers:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        # 컬럼 수 맞추기
        padded = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
    return "\n".join(lines)
