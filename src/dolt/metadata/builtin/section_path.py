"""청크가 속한 섹션의 계층 경로를 기록."""

from __future__ import annotations

from dolt.metadata.base_plugin import MetadataPlugin
from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument
from dolt.models.section import Section


class SectionPathPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "section_path"

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        if not doc.sections:
            return {}

        # chunk의 기존 metadata에서 section_title 확인
        section_title = chunk.metadata.get("section_title")
        if not section_title:
            # offset 기반으로 소속 섹션 탐색
            section = _find_section_by_offset(doc.sections, chunk.start_offset)
            if not section:
                return {}
            section_title = section.title

        # 섹션 계층 경로 구성
        path = _build_section_path(doc.sections, section_title)

        target = next((s for s in doc.sections if s.title == section_title), None)

        result: dict = {"section_path": path}
        if target:
            result["section_title"] = target.title
            result["section_level"] = target.level
            if target.page_number is not None:
                result["page_number"] = target.page_number

        return result


def _find_section_by_offset(sections: list[Section], offset: int) -> Section | None:
    """offset 위치에 해당하는 섹션을 찾는다."""
    best: Section | None = None
    for sec in sections:
        if sec.start_offset <= offset:
            if best is None or sec.start_offset > best.start_offset:
                best = sec
    return best


def _build_section_path(sections: list[Section], target_title: str) -> list[str]:
    """대상 섹션까지의 계층 경로를 구성한다."""
    target = next((s for s in sections if s.title == target_title), None)
    if not target:
        return [target_title]

    path = [target.title]
    target_idx = sections.index(target)

    # 상위 레벨 섹션을 역순으로 찾아 경로 구성
    current_level = target.level
    for i in range(target_idx - 1, -1, -1):
        sec = sections[i]
        if sec.level < current_level:
            path.insert(0, sec.title)
            current_level = sec.level

    return path
