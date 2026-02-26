"""파이프라인 진행률 표시 컴포넌트."""

from __future__ import annotations

import streamlit as st

STAGES = ["ingest", "parse", "chunk", "enrich", "embed", "export"]
STAGE_LABELS = {
    "ingest": "수집",
    "parse": "파싱",
    "chunk": "청킹",
    "enrich": "메타데이터",
    "embed": "임베딩",
    "export": "내보내기",
}


def render_progress(completed_stages: list[str], current_stage: str | None = None) -> None:
    """파이프라인 진행 상태를 표시한다."""
    cols = st.columns(len(STAGES))
    for i, (col, stage) in enumerate(zip(cols, STAGES)):
        label = STAGE_LABELS[stage]
        if stage in completed_stages:
            col.success(f"~~{label}~~", icon=":material/check_circle:")
        elif stage == current_stage:
            col.info(f"**{label}**", icon=":material/sync:")
        else:
            col.container(border=True).caption(label)
