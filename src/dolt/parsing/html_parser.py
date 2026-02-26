"""BeautifulSoup4 기반 HTML 파서."""

from __future__ import annotations

from pathlib import Path

from dolt.errors import CorruptedFileError
from dolt.models.document import StructuredDocument
from dolt.models.section import CodeBlock, Page, Section, Table
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing.html")

_NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}
_HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


class HTMLParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".html", ".htm"]

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        from bs4 import BeautifulSoup

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise CorruptedFileError(file_path, str(e)) from e

        soup = BeautifulSoup(content, "html.parser")

        # 노이즈 태그 제거
        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        # 제목 추출
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # 섹션 추출
        sections: list[Section] = []
        section_counter = 0
        for tag in soup.find_all(list(_HEADING_TAGS.keys())):
            heading_text = tag.get_text(strip=True)
            if not heading_text:
                continue
            level = _HEADING_TAGS[tag.name]

            # 헤딩 다음 형제 요소들의 텍스트를 섹션 본문으로 수집
            body_parts: list[str] = []
            for sibling in tag.next_siblings:
                if hasattr(sibling, "name") and sibling.name in _HEADING_TAGS:
                    break
                text = sibling.get_text(strip=True) if hasattr(sibling, "get_text") else str(sibling).strip()
                if text:
                    body_parts.append(text)

            section_counter += 1
            sections.append(
                Section(
                    section_id=f"sec-{section_counter:03d}",
                    title=heading_text,
                    level=level,
                    content="\n".join(body_parts),
                )
            )

        # 표 추출
        tables: list[Table] = []
        for t_idx, table_tag in enumerate(soup.find_all("table")):
            rows_data: list[list[str]] = []
            for tr in table_tag.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows_data.append(cells)

            if not rows_data:
                continue

            headers = rows_data[0]
            data_rows = rows_data[1:]
            md = _to_markdown_table(headers, data_rows)

            tables.append(
                Table(
                    table_id=f"tbl-{t_idx + 1}",
                    headers=headers,
                    rows=data_rows,
                    markdown=md,
                )
            )

        # 코드블록 추출
        code_blocks: list[CodeBlock] = []
        for c_idx, pre_tag in enumerate(soup.find_all("pre")):
            code_tag = pre_tag.find("code")
            if code_tag:
                lang = None
                css_classes = code_tag.get("class", [])
                for cls in css_classes:
                    if cls.startswith("language-"):
                        lang = cls[len("language-"):]
                        break
                code_text = code_tag.get_text()
            else:
                lang = None
                code_text = pre_tag.get_text()

            if code_text.strip():
                code_blocks.append(
                    CodeBlock(
                        code_id=f"code-{c_idx + 1}",
                        language=lang,
                        content=code_text,
                    )
                )

        # 전체 텍스트
        raw_text = soup.get_text(separator="\n", strip=True)

        doc_metadata: dict = {}
        if title:
            doc_metadata["title"] = title

        # meta 태그에서 저자 추출
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            doc_metadata["author"] = author_meta["content"]

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


def _to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
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
