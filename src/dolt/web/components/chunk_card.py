"""청크 카드 렌더링 컴포넌트."""

from __future__ import annotations

import streamlit as st

from dolt.models.chunk import Chunk, ChunkType

_TYPE_COLORS = {
    ChunkType.TEXT: "blue",
    ChunkType.TABLE: "green",
    ChunkType.CODE: "orange",
}


def render_chunk_cards(chunks: list[Chunk]) -> None:
    """청크 목록을 카드 형태로 렌더링한다."""
    if not chunks:
        st.info("청크가 없습니다.")
        return

    # 요약 메트릭
    col1, col2, col3 = st.columns(3)
    col1.metric("총 청크", len(chunks))
    avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
    col2.metric("평균 토큰", f"{avg_tokens:.0f}")
    types = {t.value: sum(1 for c in chunks if c.chunk_type == t) for t in ChunkType}
    col3.metric("텍스트/표/코드", f"{types.get('text', 0)} / {types.get('table', 0)} / {types.get('code', 0)}")

    st.divider()

    for chunk in chunks:
        color = _TYPE_COLORS.get(chunk.chunk_type, "gray")
        with st.container(border=True):
            header_col, token_col = st.columns([4, 1])
            header_col.markdown(
                f"**#{chunk.chunk_index}** &nbsp; :{color}[{chunk.chunk_type.value}]"
            )
            token_col.caption(f"{chunk.token_count} tokens")

            preview = chunk.content[:300]
            if chunk.chunk_type == ChunkType.CODE:
                lang = chunk.metadata.get("language", "")
                st.code(preview, language=lang or None)
            else:
                st.text(preview)

            if len(chunk.content) > 300:
                with st.expander("전체 보기"):
                    st.text(chunk.content)

            if chunk.metadata:
                with st.expander("메타데이터"):
                    st.json(chunk.metadata)
