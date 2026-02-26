"""Parse 페이지 — 파싱 실행 + 결과 시각화."""

from __future__ import annotations

import streamlit as st

from dolt.ingestion.ingestor import Ingestor
from dolt.parsing.registry import create_default_registry
from dolt.web.components.section_tree import render_section_tree
from dolt.web.state import get_store


def render() -> None:
    st.header("Parse")

    store = get_store()
    docs = store.load_documents()

    if not docs:
        st.info("수집된 문서가 없습니다.")
        return

    # 일괄 파싱
    if st.button("전체 파싱 실행"):
        registry = create_default_registry()
        ingestor = Ingestor(store)
        progress = st.progress(0)
        success, fail = 0, 0

        for i, doc in enumerate(docs):
            try:
                parser = registry.get_parser(doc.file_ext)
                file_path = str(ingestor.get_file_path(doc))
                structured = parser.parse(file_path, doc.doc_id)
                store.save_parsed(structured)
                success += 1
            except Exception as e:
                st.warning(f"{doc.file_name}: {e}")
                fail += 1
            progress.progress((i + 1) / len(docs))

        st.success(f"파싱 완료: {success} 성공, {fail} 실패")

    st.divider()

    # 결과 조회
    parsed_docs = []
    for doc in docs:
        p = store.load_parsed(doc.doc_id)
        if p:
            parsed_docs.append((doc, p))

    if not parsed_docs:
        st.info("파싱된 문서가 없습니다. 위 버튼을 눌러 파싱을 실행하세요.")
        return

    # 문서 선택
    names = [doc.file_name for doc, _ in parsed_docs]
    selected = st.selectbox("문서 선택", names)
    idx = names.index(selected)
    doc, structured = parsed_docs[idx]

    # 기본 정보
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("페이지", structured.total_pages)
    col2.metric("섹션", len(structured.sections))
    col3.metric("표", len(structured.tables))
    col4.metric("코드블록", len(structured.code_blocks))

    # 탭: 섹션 / 표 / 코드블록 / 원본
    tab_sec, tab_tbl, tab_code, tab_raw = st.tabs(["섹션", "표", "코드블록", "원본 텍스트"])

    with tab_sec:
        render_section_tree(structured.sections)

    with tab_tbl:
        if structured.tables:
            for tbl in structured.tables:
                st.subheader(f"Table: {tbl.table_id}")
                import pandas as pd
                if tbl.headers and tbl.rows:
                    df = pd.DataFrame(tbl.rows, columns=tbl.headers)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                elif tbl.markdown:
                    st.markdown(tbl.markdown)
        else:
            st.info("표가 없습니다.")

    with tab_code:
        if structured.code_blocks:
            for cb in structured.code_blocks:
                st.code(cb.content, language=cb.language or "text")
        else:
            st.info("코드블록이 없습니다.")

    with tab_raw:
        st.text_area("원본 텍스트", structured.raw_text, height=400, disabled=True)
