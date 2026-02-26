"""DoLT Streamlit 웹 UI — 메인 엔트리포인트."""

from __future__ import annotations

import streamlit as st

from dolt.web.state import init_state

# 페이지 설정
st.set_page_config(
    page_title="DoLT",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 초기화
init_state()

# 사이드바 네비게이션
st.sidebar.title("DoLT")
st.sidebar.caption("Document-native ELT Engine")

PAGES = {
    "Dashboard": "dashboard",
    "Ingest": "ingest",
    "Parse": "parse",
    "Chunk": "chunk",
    "Embed": "embed",
    "Export": "export",
    "Run Pipeline": "run_pipeline",
}

page = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.caption(f"Storage: `{st.session_state.config.storage.path}`")

# 페이지 라우팅
if page == "Dashboard":
    from dolt.web.pages.dashboard import render
elif page == "Ingest":
    from dolt.web.pages.ingest import render
elif page == "Parse":
    from dolt.web.pages.parse import render
elif page == "Chunk":
    from dolt.web.pages.chunk import render
elif page == "Embed":
    from dolt.web.pages.embed import render
elif page == "Export":
    from dolt.web.pages.export import render
elif page == "Run Pipeline":
    from dolt.web.pages.run_pipeline import render

render()


def main() -> None:
    """dolt-web 스크립트 엔트리포인트."""
    import sys

    from streamlit.web.cli import main as st_main

    sys.argv = ["streamlit", "run", __file__, "--server.headless=true"]
    st_main()
