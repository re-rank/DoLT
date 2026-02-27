"""Plugins 페이지 — 설치된 플러그인 현황 대시보드."""

from __future__ import annotations

import inspect

import streamlit as st

from dolt.plugins.loader import (
    discover_embedding_providers,
    discover_exporters,
    discover_metadata_plugins,
    discover_parsers,
)
from dolt.web.state import init_state

init_state()


def _plugin_table(plugins: list[tuple[str, type]]) -> None:
    """플러그인 목록을 테이블로 렌더링한다."""
    if not plugins:
        st.info("설치된 플러그인이 없습니다.")
        return

    for name, cls in plugins:
        doc = inspect.getdoc(cls) or ""
        first_line = doc.split("\n")[0] if doc else "(설명 없음)"
        st.markdown(f"**`{name}`** — `{cls.__name__}`")
        st.caption(first_line)


def render() -> None:
    st.header("Plugins")
    st.caption("설치된 플러그인 현황을 확인하고 메타데이터 플러그인을 선택합니다.")

    tab_parser, tab_metadata, tab_embedding, tab_exporter = st.tabs(
        ["Parser", "Metadata", "Embedding", "Exporter"]
    )

    with tab_parser:
        _plugin_table(discover_parsers())

    with tab_metadata:
        plugins = discover_metadata_plugins()
        if not plugins:
            st.info("설치된 메타데이터 플러그인이 없습니다.")
        else:
            st.subheader("활성 플러그인 선택")
            active: list[str] = st.session_state.active_metadata_plugins

            for name, cls in plugins:
                doc = inspect.getdoc(cls) or ""
                first_line = doc.split("\n")[0] if doc else "(설명 없음)"
                checked = st.checkbox(
                    f"`{name}` — {cls.__name__}: {first_line}",
                    value=name in active,
                    key=f"meta_plugin_{name}",
                )
                if checked and name not in active:
                    active.append(name)
                elif not checked and name in active:
                    active.remove(name)

            st.session_state.active_metadata_plugins = active

    with tab_embedding:
        _plugin_table(discover_embedding_providers())

    with tab_exporter:
        _plugin_table(discover_exporters())


render()
