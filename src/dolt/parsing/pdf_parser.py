"""PyMuPDF 기반 PDF 파서."""

from __future__ import annotations

import re
from collections import Counter

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
        tables: list[Table] = []
        all_text_parts: list[str] = []
        offset = 0

        # 라인 단위 폰트 정보 수집 (동적 헤딩 감지용)
        all_lines: list[tuple[int, float, str, bool]] = []

        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text("text", sort=True)

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

            # 라인별 폰트 정보 수집
            blocks = page.get_text(
                "dict", sort=True, flags=fitz.TEXT_PRESERVE_WHITESPACE
            )["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans_info: list[tuple[float, str]] = []
                    has_bold = False
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text.strip():
                            spans_info.append((round(span["size"], 1), span_text))
                            if "bold" in span.get("font", "").lower():
                                has_bold = True

                    if spans_info:
                        # 라인의 대표 폰트 크기 = 가장 긴 스팬의 크기
                        dominant_size = max(spans_info, key=lambda x: len(x[1]))[0]
                        line_text = "".join(t for _, t in spans_info).strip()
                        if line_text:
                            all_lines.append(
                                (page_num, dominant_size, line_text, has_bold)
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

        raw_text = _normalize_text("".join(all_text_parts))

        # 동적 헤딩 감지 (폰트 크기 분포 기반)
        sections = _detect_sections(all_lines)

        # 섹션 본문 채우기
        _fill_section_content(sections, raw_text)

        # 문서 메타데이터
        meta = pdf.metadata or {}
        doc_metadata = {
            k: v
            for k, v in {
                "title": meta.get("title"),
                "author": meta.get("author"),
                "subject": meta.get("subject"),
                "creator": meta.get("creator"),
            }.items()
            if v
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


def _normalize_text(text: str) -> str:
    """추출된 텍스트를 정규화한다."""
    # 제어문자 제거 (개행·탭 유지)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # 하이픈 줄바꿈 결합 (word-\nbreak → wordbreak)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # 연속 3개 이상 빈 줄 → 2줄로 축소
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 줄 끝 불필요한 공백 제거
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def _detect_sections(
    all_lines: list[tuple[int, float, str, bool]],
) -> list[Section]:
    """폰트 크기 분포를 분석하여 동적으로 헤딩을 감지한다."""
    if not all_lines:
        return []

    # 본문 폰트 크기 추정: 문자 수 가중 최빈값
    size_chars: Counter[float] = Counter()
    for _, font_size, text, _ in all_lines:
        size_chars[font_size] += len(text)

    body_size = size_chars.most_common(1)[0][0]

    # 헤딩 후보: 본문보다 유의미하게 큰 폰트 (1pt 이상 + 10% 이상)
    heading_sizes = sorted(
        [s for s in size_chars if s > body_size + 1.0 and s > body_size * 1.1],
        reverse=True,
    )

    if not heading_sizes:
        return []

    # 레벨 할당: 큰 순서대로 level 1, 2, 3
    level_map: dict[float, int] = {}
    for i, size in enumerate(heading_sizes[:3]):
        level_map[size] = i + 1
    for size in heading_sizes[3:]:
        level_map[size] = 3

    logger.debug("본문 크기: %.1fpt, 헤딩 크기 맵: %s", body_size, level_map)

    # 섹션 생성 (200자 이상은 본문으로 간주하여 제외)
    sections: list[Section] = []
    counter = 0
    for page_num, font_size, text, _ in all_lines:
        if font_size in level_map and len(text) < 200:
            counter += 1
            sections.append(
                Section(
                    section_id=f"sec-{counter:03d}",
                    title=text,
                    level=level_map[font_size],
                    content="",
                    page_number=page_num + 1,
                )
            )

    return sections


def _fill_section_content(sections: list[Section], raw_text: str) -> None:
    """각 섹션의 content와 offset을 채운다."""
    if not sections:
        return

    # 1단계: 모든 섹션 제목 위치를 순차 탐색 (search_from으로 중복 매칭 방지)
    positions: list[int] = []
    search_from = 0
    for sec in sections:
        pos = raw_text.find(sec.title, search_from)
        positions.append(pos)
        if pos != -1:
            search_from = pos + len(sec.title)

    # 2단계: 각 섹션의 본문 = 현재 제목 끝 ~ 다음 유효 제목 시작
    for i, sec in enumerate(sections):
        if positions[i] == -1:
            continue

        content_start = positions[i] + len(sec.title)

        content_end = len(raw_text)
        for j in range(i + 1, len(sections)):
            if positions[j] != -1:
                content_end = positions[j]
                break

        sec.content = raw_text[content_start:content_end].strip()
        sec.start_offset = positions[i]
        sec.end_offset = content_end


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
