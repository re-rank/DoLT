"""Status 대시보드 페이지."""

from __future__ import annotations

import streamlit as st

from dolt.web.state import get_store


def render() -> None:
    st.header("Dashboard")

    store = get_store()
    docs = store.load_documents()

    if not docs:
        st.info("수집된 문서가 없습니다. 'Ingest' 탭에서 문서를 업로드하세요.")
        return

    # 집계
    new = sum(1 for d in docs if d.status.value == "new")
    updated = sum(1 for d in docs if d.status.value == "updated")
    unchanged = sum(1 for d in docs if d.status.value == "unchanged")
    parsed = sum(1 for d in docs if store.load_parsed(d.doc_id) is not None)
    chunked = sum(len(store.load_chunks(d.doc_id)) for d in docs)
    embedded = sum(len(store.load_embeddings(d.doc_id)) for d in docs)

    # 메트릭
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Documents", len(docs))
    col2.metric("Parsed", parsed)
    col3.metric("Chunks", chunked)
    col4.metric("Embedded", embedded)

    # 상태 분포
    st.subheader("문서 상태")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown(f"- **New**: {new}")
        st.markdown(f"- **Updated**: {updated}")
        st.markdown(f"- **Unchanged**: {unchanged}")

    with col_b:
        import pandas as pd
        status_data = {"상태": ["new", "updated", "unchanged"], "수": [new, updated, unchanged]}
        df = pd.DataFrame(status_data)
        st.bar_chart(df, x="상태", y="수")

    # 문서 목록 테이블
    st.subheader("문서 목록")
    rows = []
    for doc in docs:
        p = store.load_parsed(doc.doc_id) is not None
        c = len(store.load_chunks(doc.doc_id))
        e = len(store.load_embeddings(doc.doc_id))
        rows.append({
            "파일명": doc.file_name,
            "포맷": doc.file_ext,
            "크기": f"{doc.file_size_bytes / 1024:.1f}KB",
            "상태": doc.status.value,
            "파싱": "O" if p else "X",
            "청크": c,
            "임베딩": e,
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
