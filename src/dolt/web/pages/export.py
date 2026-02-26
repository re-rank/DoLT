"""Export 페이지 — 내보내기 설정 + 실행."""

from __future__ import annotations

import streamlit as st

from dolt.models.config import ExportTarget
from dolt.pipeline.orchestrator import _create_exporter
from dolt.web.state import get_config, get_store, init_state

init_state()


def render() -> None:
    st.header("Export")

    store = get_store()
    config = get_config()

    # 임베딩된 청크 수집
    docs = store.load_documents()
    all_chunks = []
    for doc in docs:
        emb = store.load_embeddings(doc.doc_id)
        all_chunks.extend(emb)

    if not all_chunks:
        st.info("임베딩된 데이터가 없습니다. 'Embed' 탭에서 먼저 임베딩하세요.")
        return

    st.caption(f"내보내기 대상: {len(all_chunks)}개 청크")

    # 타겟 설정
    target = st.selectbox("Export Target", [t.value for t in ExportTarget])

    overrides: dict = {"export": {"target": target}}

    if target == "json":
        col1, col2 = st.columns(2)
        output = col1.text_input("출력 경로", value=".dolt/export.json")
        include_vectors = col2.checkbox("벡터 포함", value=True)
        overrides["export"]["json"] = {"output": output, "include_vectors": include_vectors}

    elif target == "qdrant":
        col1, col2, col3 = st.columns(3)
        url = col1.text_input("URL", value="localhost")
        port = col2.number_input("Port", value=6333)
        collection = col3.text_input("Collection", value="dolt_documents")
        overrides["export"]["qdrant"] = {"url": url, "port": port, "collection": collection}

    elif target == "pinecone":
        col1, col2 = st.columns(2)
        index = col1.text_input("Index", value="dolt-documents")
        namespace = col2.text_input("Namespace", value="")
        overrides["export"]["pinecone"] = {"index": index, "namespace": namespace}

    elif target == "weaviate":
        col1, col2 = st.columns(2)
        url = col1.text_input("URL", value="http://localhost:8080")
        collection = col2.text_input("Collection", value="DoltDocuments")
        overrides["export"]["weaviate"] = {"url": url, "collection": collection}

    elif target == "postgres":
        col1, col2 = st.columns(2)
        dsn = col1.text_input("DSN", value="postgresql://localhost:5432/dolt")
        table = col2.text_input("Table", value="dolt_chunks")
        overrides["export"]["postgres"] = {"dsn": dsn, "table": table}

    if st.button("Export 실행"):
        cfg = config.model_copy(update=overrides)
        try:
            exporter = _create_exporter(cfg)
            result = exporter.export(all_chunks)
            st.success(
                f"Export 완료: {result.success}/{result.total} -> {result.destination}"
            )
            if result.errors:
                for err in result.errors:
                    st.warning(err)
        except Exception as e:
            st.error(f"Export 실패: {e}")


render()
