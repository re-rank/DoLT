"""Chunk 페이지 — 청킹 설정 + 결과 미리보기."""

from __future__ import annotations

import streamlit as st

from dolt.metadata.enricher import MetadataEnricher
from dolt.models.config import ChunkConfig, ChunkMode
from dolt.pipeline.orchestrator import _create_chunker
from dolt.web.components.chunk_card import render_chunk_cards
from dolt.web.state import get_config, get_store, init_state

init_state()


def render() -> None:
    st.header("Chunk")

    store = get_store()
    config = get_config()
    docs = store.load_documents()

    # 파싱 완료된 문서만 필터
    parsed_docs = []
    for doc in docs:
        p = store.load_parsed(doc.doc_id)
        if p:
            parsed_docs.append((doc, p))

    if not parsed_docs:
        st.info("파싱된 문서가 없습니다. 'Parse' 탭에서 먼저 파싱하세요.")
        return

    # 청킹 설정
    st.subheader("설정")
    col1, col2, col3 = st.columns(3)
    mode = col1.selectbox("모드", [m.value for m in ChunkMode], index=2)
    max_tokens = col2.slider("최대 토큰", 100, 2000, config.chunking.max_tokens)
    overlap = col3.slider("오버랩 토큰", 0, 500, config.chunking.overlap_tokens)

    chunk_cfg = ChunkConfig(mode=ChunkMode(mode), max_tokens=max_tokens, overlap_tokens=overlap)

    # 일괄 청킹
    if st.button("전체 청킹 실행"):
        chunker = _create_chunker(config.model_copy(update={"chunking": chunk_cfg}))
        active_names: list[str] = st.session_state.get(
            "active_metadata_plugins", [],
        )
        if active_names:
            enricher = MetadataEnricher.from_names(active_names)
        else:
            enricher = MetadataEnricher(plugins=[])
        progress = st.progress(0)
        total = 0

        for i, (doc, structured) in enumerate(parsed_docs):
            chunks = chunker.chunk(structured)
            chunks = enricher.enrich(chunks, structured)
            store.save_chunks(doc.doc_id, chunks)
            total += len(chunks)
            progress.progress((i + 1) / len(parsed_docs))

        st.success(f"청킹 완료: {total} chunks")

    st.divider()

    # 결과 조회
    names = [doc.file_name for doc, _ in parsed_docs]
    selected = st.selectbox("문서 선택", names)
    idx = names.index(selected)
    doc, _ = parsed_docs[idx]

    chunks = store.load_chunks(doc.doc_id)
    render_chunk_cards(chunks)


render()
