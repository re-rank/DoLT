"""markdown-it-py 기반 Markdown 파서."""

from __future__ import annotations

import re
from pathlib import Path

from dolt.errors import CorruptedFileError
from dolt.models.document import StructuredDocument
from dolt.models.section import CodeBlock, Page, Section, Table
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing.markdown")


class MarkdownParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".md"]

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        try:
            raw_text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise CorruptedFileError(file_path, str(e)) from e

        sections = _extract_sections(raw_text)
        code_blocks = _extract_code_blocks(raw_text)
        tables = _extract_tables(raw_text)

        # 첫 번째 H1을 제목으로 사용
        title = ""
        for sec in sections:
            if sec.level == 1:
                title = sec.title
                break

        doc_metadata: dict = {}
        if title:
            doc_metadata["title"] = title

        return StructuredDocument(
            doc_id=doc_id,
            source=file_path,
            raw_text=raw_text,
            pages=[
                Page(page_number=1, text=raw_text, start_offset=0, end_offset=len(raw_text))
            ],
            sections=sections,
            tables=tables,
            code_blocks=code_blocks,
            metadata=doc_metadata,
            total_chars=len(raw_text),
            total_pages=1,
        )


def _extract_sections(text: str) -> list[Section]:
    """ATX 헤딩(# ~ ######)을 기반으로 섹션을 추출한다."""
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    sections: list[Section] = []
    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.start()

        # 본문: 현재 헤딩 끝 ~ 다음 헤딩 시작
        content_start = match.end()
        if i + 1 < len(matches):
            content_end = matches[i + 1].start()
        else:
            content_end = len(text)

        content = text[content_start:content_end].strip()

        sections.append(
            Section(
                section_id=f"sec-{i + 1:03d}",
                title=title,
                level=level,
                content=content,
                start_offset=start,
                end_offset=content_end,
            )
        )

    return sections


def _extract_code_blocks(text: str) -> list[CodeBlock]:
    """펜스 코드블록(```)을 추출한다."""
    pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    blocks: list[CodeBlock] = []

    for i, match in enumerate(pattern.finditer(text)):
        lang = match.group(1) or None
        content = match.group(2)
        blocks.append(
            CodeBlock(
                code_id=f"code-{i + 1}",
                language=lang,
                content=content,
            )
        )

    return blocks


def _extract_tables(text: str) -> list[Table]:
    """Markdown 테이블을 추출한다."""
    # 테이블 패턴: | col | col | 형태가 연속된 줄
    table_pattern = re.compile(
        r"((?:^\|.+\|$\n?){2,})",
        re.MULTILINE,
    )

    tables: list[Table] = []
    for t_idx, match in enumerate(table_pattern.finditer(text)):
        lines = match.group(0).strip().split("\n")
        if len(lines) < 2:
            continue

        # 구분선 행 감지 (| --- | --- |)
        rows: list[list[str]] = []
        for line in lines:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # 구분선 행 건너뛰기
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            rows.append(cells)

        if not rows:
            continue

        headers = rows[0]
        data_rows = rows[1:]

        tables.append(
            Table(
                table_id=f"tbl-{t_idx + 1}",
                headers=headers,
                rows=data_rows,
                markdown=match.group(0).strip(),
            )
        )

    return tables
