"""Run Pipeline 페이지 — 전체 파이프라인 일괄 실행."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from dolt.models.config import ChunkMode, EmbeddingProvider, ExportTarget
from dolt.pipeline.orchestrator import PipelineOrchestrator, StageResult
from dolt.web.components.progress_tracker import STAGES, STAGE_LABELS
from dolt.web.state import get_config, init_state

init_state()


def render() -> None:
    st.header("Run Pipeline")
    st.caption("Ingest -> Parse -> Chunk -> Enrich -> Embed -> Export 전체 실행")

    config = get_config()

    # 소스 입력
    st.subheader("소스")
    source_type = st.radio("입력 방식", ["파일 업로드", "경로/URL"], horizontal=True)

    source_path = None
    if source_type == "파일 업로드":
        files = st.file_uploader("문서 업로드", accept_multiple_files=True, key="run_upload")
        if files:
            tmp_dir = tempfile.mkdtemp()
            for f in files:
                p = Path(tmp_dir) / f.name
                p.write_bytes(f.getbuffer())
            source_path = tmp_dir
    else:
        source_path = st.text_input("파일/디렉토리 경로 또는 URL")

    # 설정
    st.subheader("설정")
    col1, col2, col3, col4 = st.columns(4)
    mode = col1.selectbox("청킹 모드", [m.value for m in ChunkMode], index=2)
    max_tokens = col2.number_input("최대 토큰", 100, 2000, 512)
    provider = col3.selectbox("임베딩", [p.value for p in EmbeddingProvider])
    target = col4.selectbox("Export", [t.value for t in ExportTarget])

    model_name = ""
    output_path = ".dolt/export.json"
    with st.expander("고급 설정"):
        model_name = st.text_input("임베딩 모델 (빈칸=기본값)", value="")
        if target == "json":
            output_path = st.text_input("JSON 출력 경로", value=output_path)

    # 실행
    if not source_path:
        st.info("소스를 입력하세요.")
        return

    if st.button("파이프라인 실행", type="primary"):
        overrides: dict = {
            "chunking": {"mode": mode, "max_tokens": max_tokens},
            "embedding": {"provider": provider},
            "export": {"target": target},
        }
        if model_name:
            overrides["embedding"]["model"] = model_name
        if target == "json":
            overrides["export"]["json"] = {"output": output_path}

        cfg = config.model_copy(update=overrides)
        orchestrator = PipelineOrchestrator(cfg)

        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        completed: list[str] = []

        def on_stage(stage: str, result: StageResult) -> None:
            completed.append(stage)
            idx = STAGES.index(stage) + 1
            progress_bar.progress(idx / len(STAGES))
            label = STAGE_LABELS[stage]
            status_text.text(f"{label} 완료 ({result.count}건, {result.elapsed_seconds:.1f}s)")

        try:
            result = orchestrator.run(source_path, on_stage_complete=on_stage)
        except Exception as e:
            st.error(f"파이프라인 실패: {e}")
            return

        progress_bar.progress(1.0)
        status_text.empty()

        # 결과 테이블
        st.divider()
        st.subheader("결과")

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("문서", result.doc_count)
        col_b.metric("청크", result.chunk_count)
        col_c.metric("임베딩", result.embedded_count)
        col_d.metric("소요시간", f"{result.elapsed_seconds:.1f}s")

        import pandas as pd
        rows = []
        for name in STAGES:
            stage = result.stages.get(name)
            if stage:
                rows.append({
                    "단계": STAGE_LABELS[name],
                    "건수": stage.count,
                    "소요시간": f"{stage.elapsed_seconds:.1f}s",
                    "상태": stage.status,
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if result.exported_count > 0:
            st.success(f"파이프라인 완료! {result.exported_count}개 청크 내보내기 성공")
        elif result.chunk_count > 0:
            st.warning("청킹까지 완료되었으나 임베딩/내보내기에 실패했습니다.")
        else:
            st.info("처리할 새 문서가 없습니다.")


render()
