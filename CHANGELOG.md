# Changelog

All notable changes to this project will be documented in this file.

---

## v0.0.1 (2025-02-27) — Initial Release

**Core Pipeline**
- Ingest → Parse → Chunk → Enrich → Embed → Export 6단계 파이프라인 구현
- `dolt run` 단일 명령으로 전체 파이프라인 일괄 실행 지원
- `dolt ingest / parse / chunk / embed / export / status` 단계별 CLI 제공
- SHA-256 기반 문서 변경 감지 및 캐싱으로 중복 처리 방지

**Parsing**
- PDF (PyMuPDF), DOCX, HTML, Markdown, Plain Text 파서 구현
- Docling 기반 고급 PDF 파서 추가 (선택 의존성)
- 섹션·표·코드블록 구조 보존 추출
- entry_point 기반 파서 플러그인 자동 탐색

**Chunking**
- Token / Structure / Hybrid 3가지 청킹 모드 구현
- 섹션 경계 인식 라인 기반 분할 지원
- 표·코드블록 독립 청크 분리, 동일 섹션 내 오버랩 적용

**Embedding**
- OpenAI, Cohere, 로컬(sentence-transformers) 프로바이더 지원
- 배치 처리 및 자동 재시도

**Export**
- JSON, Qdrant, Pinecone, Weaviate, PostgreSQL(pgvector) 익스포터 구현

**Metadata & Plugins**
- 기본 메타데이터(basic_meta, word_count, section_path) 자동 부여
- entry_point 기반 4종 플러그인 확장 (Parser, Metadata, Embedding, Exporter)

**Web UI**
- Streamlit 기반 대시보드 (`dolt-web`)
- 수집, 파싱, 청킹, 임베딩, 내보내기, 전체 실행 페이지
- 섹션 트리 시각화, 청크 카드, 진행률 트래커 컴포넌트

**Infra**
- GitHub Actions CI (pytest, ruff, mypy)
- `.dolt/` 로컬 저장소 — 단계별 중간 결과 저장 및 파이프라인 재개 지원
