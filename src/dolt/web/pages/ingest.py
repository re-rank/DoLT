"""Ingest 페이지 — 파일 업로드 + URL 수집."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from dolt.ingestion.ingestor import SUPPORTED_EXTENSIONS, Ingestor
from dolt.web.state import get_store


def render() -> None:
    st.header("Ingest")
    st.caption("파일, 디렉토리 경로, 또는 URL에서 문서를 수집합니다.")

    store = get_store()
    ingestor = Ingestor(store)

    tab_upload, tab_path, tab_url = st.tabs(["파일 업로드", "경로 입력", "URL"])

    # --- 파일 업로드 ---
    with tab_upload:
        exts = [e.lstrip(".") for e in SUPPORTED_EXTENSIONS]
        files = st.file_uploader(
            "문서를 드래그하거나 클릭하여 업로드",
            accept_multiple_files=True,
            type=exts,
        )
        if files and st.button("수집 시작", key="ingest_upload"):
            results = []
            for f in files:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(f.name).suffix
                ) as tmp:
                    tmp.write(f.getbuffer())
                    tmp_path = tmp.name

                try:
                    doc = ingestor.ingest_file(tmp_path)
                    results.append((f.name, doc.status.value, None))
                except Exception as e:
                    results.append((f.name, "error", str(e)))

            _show_results(results)

    # --- 경로 입력 ---
    with tab_path:
        source_path = st.text_input("파일 또는 디렉토리 경로", placeholder="/path/to/documents/")
        recursive = st.checkbox("하위 디렉토리 포함", value=True)
        if source_path and st.button("수집 시작", key="ingest_path"):
            try:
                docs = ingestor.ingest(source_path, recursive=recursive)
                results = [(d.file_name, d.status.value, None) for d in docs]
                _show_results(results)
            except Exception as e:
                st.error(f"오류: {e}")

    # --- URL ---
    with tab_url:
        url = st.text_input("URL", placeholder="https://example.com/document.pdf")
        if url and st.button("수집 시작", key="ingest_url"):
            try:
                doc = ingestor.ingest_url(url)
                st.success(f"{doc.file_name} ({doc.status.value})")
            except Exception as e:
                st.error(f"오류: {e}")


def _show_results(results: list[tuple[str, str, str | None]]) -> None:
    success = sum(1 for _, s, _ in results if s != "error")
    errors = sum(1 for _, s, _ in results if s == "error")

    if success:
        st.success(f"{success}개 문서 수집 완료")
    if errors:
        st.error(f"{errors}개 실패")

    for name, status, err in results:
        if err:
            st.error(f"{name}: {err}")
        else:
            st.write(f"- {name} — `{status}`")
