"""플레인 텍스트 파서."""

from __future__ import annotations

import re
from pathlib import Path

from dolt.errors import CorruptedFileError
from dolt.models.document import StructuredDocument
from dolt.models.section import Page, Section
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing.text")


class PlainTextParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        try:
            raw_text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise CorruptedFileError(file_path, str(e)) from e

        sections = _extract_sections(raw_text)

        # 첫 번째 줄을 제목으로 사용
        first_line = raw_text.split("\n", 1)[0].strip()
        doc_metadata: dict = {}
        if first_line:
            doc_metadata["title"] = first_line

        return StructuredDocument(
            doc_id=doc_id,
            source=file_path,
            raw_text=raw_text,
            pages=[
                Page(page_number=1, text=raw_text, start_offset=0, end_offset=len(raw_text))
            ],
            sections=sections,
            metadata=doc_metadata,
            total_chars=len(raw_text),
            total_pages=1,
        )


def _extract_sections(text: str) -> list[Section]:
    """빈 줄로 구분된 문단을 섹션으로 추출한다."""
    paragraphs = re.split(r"\n\s*\n", text)
    sections: list[Section] = []
    offset = 0

    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            offset += 2  # 빈 줄
            continue

        # 첫 줄을 섹션 제목으로 사용
        lines = para.split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        start = text.find(para, offset)
        end = start + len(para) if start != -1 else offset + len(para)

        sections.append(
            Section(
                section_id=f"sec-{i + 1:03d}",
                title=title,
                level=1,
                content=content,
                start_offset=start if start != -1 else offset,
                end_offset=end,
            )
        )

        offset = end

    return sections
