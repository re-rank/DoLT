"""Embed 페이지 — 임베딩 설정 + 실행."""

from __future__ import annotations

import streamlit as st

from dolt.models.chunk import EmbeddedChunk
from dolt.pipeline.orchestrator import _create_embedding_provider
from dolt.plugins.loader import discover_embedding_providers
from dolt.web.state import get_config, get_store, init_state

init_state()


def render() -> None:
    st.header("Embed")

    store = get_store()
    config = get_config()

    # 설정
    st.subheader("설정")
    col1, col2, col3 = st.columns(3)
    embedding_plugins = discover_embedding_providers()
    provider_names = [name for name, _ in embedding_plugins]
    provider = col1.selectbox("Provider", provider_names)
    model = col2.text_input("모델명 (빈칸=기본값)", value="")
    batch_size = col3.number_input("Batch Size", 1, 500, config.embedding.batch_size)

    # 문서 목록
    docs = store.load_documents()
    docs_with_chunks = [(d, store.load_chunks(d.doc_id)) for d in docs]
    docs_with_chunks = [(d, c) for d, c in docs_with_chunks if c]

    if not docs_with_chunks:
        st.info("청킹된 문서가 없습니다. 'Chunk' 탭에서 먼저 청킹하세요.")
        return

    total_chunks = sum(len(c) for _, c in docs_with_chunks)
    st.caption(f"임베딩 대상: {len(docs_with_chunks)}개 문서, {total_chunks}개 청크")

    if st.button("임베딩 실행"):
        overrides = {"embedding": {"provider": provider, "batch_size": batch_size}}
        if model:
            overrides["embedding"]["model"] = model
        cfg = config.model_copy(update=overrides)

        try:
            emb_provider = _create_embedding_provider(cfg)
        except Exception as e:
            st.error(f"Provider 초기화 실패: {e}")
            return

        progress = st.progress(0)
        total_embedded = 0

        for i, (doc, chunks) in enumerate(docs_with_chunks):
            texts = [c.content for c in chunks]
            try:
                vectors = emb_provider.embed(texts)
                embedded = [
                    EmbeddedChunk(
                        chunk_id=c.chunk_id, doc_id=c.doc_id, content=c.content,
                        chunk_type=c.chunk_type, chunk_index=c.chunk_index,
                        token_count=c.token_count, vector=v,
                        embedding_model=emb_provider.model_name(),
                        embedding_dim=emb_provider.dimension(),
                        metadata=c.metadata,
                    )
                    for c, v in zip(chunks, vectors)
                ]
                store.save_embeddings(doc.doc_id, embedded)
                total_embedded += len(embedded)
            except Exception as e:
                st.error(f"{doc.file_name}: {e}")

            progress.progress((i + 1) / len(docs_with_chunks))

        st.success(f"임베딩 완료: {total_embedded} chunks")

    # 현재 상태
    st.divider()
    st.subheader("현황")
    for doc, _ in docs_with_chunks:
        emb = store.load_embeddings(doc.doc_id)
        if emb:
            dim = emb[0].embedding_dim
            model = emb[0].embedding_model
            st.write(f"- {doc.file_name}: {len(emb)} embedded (dim={dim}, model={model})")
        else:
            st.write(f"- {doc.file_name}: 미완료")


render()
