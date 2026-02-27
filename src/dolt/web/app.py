"""DoLT Streamlit 웹 UI — 메인 엔트리포인트."""

from __future__ import annotations

import streamlit as st

# 네이티브 멀티페이지 네비게이션
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("pages/ingest.py", title="Ingest", icon=":material/upload_file:"),
    st.Page("pages/parse.py", title="Parse", icon=":material/article:"),
    st.Page("pages/chunk.py", title="Chunk", icon=":material/view_module:"),
    st.Page("pages/embed.py", title="Embed", icon=":material/hub:"),
    st.Page("pages/export.py", title="Export", icon=":material/cloud_upload:"),
    st.Page("pages/run_pipeline.py", title="Run Pipeline", icon=":material/play_circle:"),
    st.Page("pages/plugins.py", title="Plugins", icon=":material/extension:"),
]

pg = st.navigation(pages)

st.sidebar.divider()
st.sidebar.caption("DoLT — Document-native ELT Engine")

pg.run()


def main() -> None:
    """dolt-web 스크립트 엔트리포인트."""
    import sys

    from streamlit.web.cli import main as st_main

    sys.argv = ["streamlit", "run", __file__, "--server.headless=true"]
    st_main()
