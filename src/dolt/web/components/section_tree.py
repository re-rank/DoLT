"""섹션 트리 렌더링 컴포넌트."""

from __future__ import annotations

import streamlit as st

from dolt.models.section import Section


def render_section_tree(sections: list[Section]) -> None:
    """섹션 목록을 트리 형태로 렌더링한다."""
    if not sections:
        st.info("섹션이 없습니다.")
        return

    for sec in sections:
        indent = "\u2003" * (sec.level - 1)  # em space로 들여쓰기
        label = f"{indent}{'#' * sec.level} {sec.title}"

        with st.expander(label, expanded=sec.level <= 1):
            if sec.content:
                st.markdown(sec.content[:500])
                if len(sec.content) > 500:
                    st.caption(f"... ({len(sec.content)}자)")
            else:
                st.caption("(본문 없음)")
