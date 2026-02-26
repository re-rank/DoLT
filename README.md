<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/status-in%20development-orange?style=flat-square" alt="Status">
</p>

<h1 align="center">DoLT</h1>
<p align="center"><b>Document-native ELT Engine</b></p>
<p align="center">비정형 문서를 AI/RAG에 적합한 구조화 데이터로 변환하는 오픈소스 파이프라인</p>

<p align="center">
  <a href="#-왜-dolt인가">한국어</a> | <a href="#-why-dolt">English</a>
</p>

<br>

```bash
# PDF 100페이지를 Qdrant에 적재하기까지, 명령어 한 줄이면 충분합니다.
dolt run ./documents/ --target qdrant --collection my_docs
```

---

## <a id="-왜-dolt인가"></a> 왜 DoLT인가?

RAG 시스템을 만들 때마다 반복되는 전처리 코드가 있습니다.

```
PDF를 열고 → 텍스트를 추출하고 → 적당히 자르고 → 임베딩하고 → 벡터 DB에 넣는다
```

**매번 스크립트를 새로 짭니다.** 표는 깨지고, 섹션 구조는 사라지고, 코드블록은 잘립니다.

DoLT는 이 파이프라인을 **한 번에, 제대로** 해결합니다.

| 기존 방식 | DoLT |
|-----------|------|
| 프로젝트마다 전처리 스크립트 작성 | `dolt run` 한 줄 |
| 문서 구조 무시, 텍스트만 추출 | 섹션·표·코드블록 구조 보존 |
| 프레임워크(LangChain 등)에 종속 | 독립적인 CLI 도구 |
| 클라우드 SaaS 의존 | 로컬 우선, 오프라인 가능 |

---

## 핵심 기능

**Ingest** — 파일, 폴더, URL에서 문서를 수집하고 변경을 감지합니다.

**Parse** — PDF, DOCX, HTML, Markdown에서 텍스트·섹션·표·코드블록을 구조적으로 추출합니다.

**Chunk** — Token, Structure, Hybrid 3가지 모드로 문맥을 보존하며 분할합니다.

**Enrich** — 메타데이터(제목, 저자, 섹션 경로, 단어 수)를 자동으로 부여합니다.

**Embed** — OpenAI, Cohere, 로컬 모델로 벡터를 생성합니다. 배치 처리와 자동 재시도를 지원합니다.

**Export** — Qdrant, Pinecone, Weaviate, PostgreSQL, JSON으로 내보냅니다.

---

## 파이프라인

```text
Source (File / Dir / URL)
  │
  ▼
Ingest ─── 수집, SHA-256 변경 감지
  │
  ▼
Parse ──── 텍스트·섹션·표·코드블록 추출
  │
  ▼
Chunk ──── Hybrid 분할, Overlap 적용
  │
  ▼
Enrich ─── 메타데이터 자동 부여
  │
  ▼
Embed ──── 벡터 변환 (배치 + 재시도)
  │
  ▼
Export ─── Vector DB / JSON / PostgreSQL
```

---

## 설치

```bash
pip install dolt
```

또는 소스에서 설치:

```bash
git clone https://github.com/re-rank/DoLT.git
cd dolt
pip install -e .
```

---

## 빠른 시작

### 1. 전체 파이프라인 (가장 간단한 방법)

```bash
# PDF → Qdrant
dolt run ./report.pdf --target qdrant

# 폴더 전체 → JSON
dolt run ./documents/ --target json --output ./output.json

# 로컬 임베딩 (API 키 불필요)
dolt run ./docs/ --provider local --model all-MiniLM-L6-v2 --target json
```

### 2. 단계별 실행

```bash
# 수집
dolt ingest ./documents/

# 파싱
dolt parse

# 청킹 (하이브리드 모드, 512 토큰, 50 오버랩)
dolt chunk --mode hybrid --max-tokens 512 --overlap 50

# 임베딩
dolt embed --provider openai

# 내보내기
dolt export --target qdrant --collection my_docs
```

### 3. 상태 확인

```bash
dolt status
```

```text
DoLT Status:
  Documents: 5 (3 new, 1 updated, 1 unchanged)
  Parsed:    4
  Chunks:    127
  Embedded:  127
  Exported:  0 (not yet exported)
```

---

## 지원 포맷

| 포맷 | 확장자 | 추출 항목 |
|------|--------|-----------|
| PDF | `.pdf` | 텍스트, 페이지, 섹션, 표 |
| DOCX | `.docx` | 텍스트, 헤딩, 표 |
| HTML | `.html` `.htm` | 본문 텍스트, 섹션, 표, 코드블록 |
| Markdown | `.md` | 헤딩, 코드블록, 표 |

---

## 설정

### 환경변수

```bash
export OPENAI_API_KEY="sk-..."      # OpenAI 임베딩
export COHERE_API_KEY="..."          # Cohere 임베딩
export PINECONE_API_KEY="..."        # Pinecone export
export DATABASE_URL="postgres://..." # PostgreSQL export
```

### 설정 파일 (dolt.yaml)

```yaml
chunking:
  mode: hybrid
  max_tokens: 512
  overlap_tokens: 50

embedding:
  provider: openai
  model: text-embedding-3-small

export:
  target: qdrant
  qdrant:
    url: localhost
    port: 6333
    collection: dolt_documents
```

> CLI 옵션 > 환경변수 > dolt.yaml > 기본값 순으로 우선 적용됩니다.

---

## 청킹 모드

| 모드 | 설명 | 적합한 경우 |
|------|------|-------------|
| `token` | 고정 토큰 수로 슬라이딩 윈도우 분할 | 구조 없는 긴 텍스트 |
| `structure` | 섹션(헤딩) 경계 기준 분할 | 구조가 명확한 문서 |
| `hybrid` (기본) | 섹션 기반 + 토큰 재분할 | 대부분의 경우 |

- 표 → 독립 청크 (`table` 타입, Markdown 변환)
- 코드블록 → 독립 청크 (`code` 타입)
- Overlap은 동일 섹션 내 청크 간에만 적용

---

## 임베딩 프로바이더

| 프로바이더 | 모델 | 차원 | 비고 |
|-----------|------|------|------|
| `openai` | text-embedding-3-small | 1536 | 기본값 |
| `openai` | text-embedding-3-large | 3072 | 고품질 |
| `cohere` | embed-multilingual-v3.0 | 1024 | 다국어 |
| `local` | all-MiniLM-L6-v2 | 384 | API 키 불필요 |

---

## 플러그인

DoLT는 4가지 확장 지점을 제공합니다.

| 확장 지점 | entry_point 그룹 |
|-----------|------------------|
| Parser | `dolt.parsers` |
| Metadata Enricher | `dolt.metadata_plugins` |
| Embedding Provider | `dolt.embedding_providers` |
| Exporter | `dolt.exporters` |

### 커스텀 메타데이터 플러그인 예시

```python
from dolt.metadata.base_plugin import MetadataPlugin

class LanguageDetectorPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "language_detector"

    def enrich(self, chunk, doc) -> dict:
        return {"detected_language": detect(chunk.content)}
```

```toml
# pyproject.toml
[project.entry-points."dolt.metadata_plugins"]
language_detector = "my_plugin:LanguageDetectorPlugin"
```

`pip install`만 하면 DoLT가 자동으로 플러그인을 인식합니다.

---

## Docker

```bash
# Qdrant와 함께 실행
docker compose up -d

# 파이프라인 실행
docker compose run dolt run /data/documents/ --target qdrant
```

---

## 로컬 저장소

DoLT는 `.dolt/` 디렉토리에 각 단계의 중간 결과를 저장합니다.

```text
.dolt/
├── documents.json      # 수집된 문서 목록
├── parsed/             # 파싱 결과 (문서별)
├── chunks/             # 청크 데이터 (문서별)
├── embeddings/         # 임베딩 벡터 (문서별)
└── cache/              # 다운로드 캐시
```

- 파이프라인이 중간에 실패해도 완료된 단계부터 **재개**할 수 있습니다.
- `unchanged` 상태 문서는 자동으로 **스킵**합니다.

---

## Contributing

모든 형태의 기여를 환영합니다! 버그 리포트, 기능 제안, 코드 기여, 문서 개선 등 무엇이든 좋습니다.

### 개발 환경 설정

```bash
git clone https://github.com/re-rank/DoLT.git
cd dolt
pip install -e ".[dev]"
```

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 모듈만
pytest tests/unit/test_parsing.py

# 커버리지 리포트
pytest --cov=dolt --cov-report=html
```

### 기여 절차

1. 이슈를 확인하거나 새로 생성합니다.
2. `main`에서 브랜치를 생성합니다. (`feat/기능명`, `fix/버그명`)
3. 코드를 작성하고 테스트를 추가합니다.
4. 린트를 통과하는지 확인합니다.
   ```bash
   ruff check src/
   mypy src/
   ```
5. Pull Request를 생성합니다.

### 코드 스타일

- **Linter**: ruff
- **Type Checker**: mypy (strict)
- **Line Length**: 100
- **Python**: 3.10+, type hints 필수

### 플러그인 기여

새로운 Parser, Embedding Provider, Exporter를 만들었다면 별도 패키지로 배포하거나, core에 기여할 수 있습니다. [플러그인 섹션](#플러그인)을 참고하세요.

---

<br>
<br>

<h1 align="center"><a id="-why-dolt"></a>DoLT</h1>
<p align="center"><b>Document-native ELT Engine</b></p>
<p align="center">An open-source pipeline that transforms unstructured documents into structured data for AI/RAG</p>

<br>

```bash
# One command to load 100-page PDFs into Qdrant.
dolt run ./documents/ --target qdrant --collection my_docs
```

---

## Why DoLT?

Every RAG system starts with the same repetitive preprocessing:

```
Open PDF → Extract text → Split into chunks → Embed → Push to vector DB
```

**You rewrite this script every single time.** Tables break, section structure is lost, code blocks get split in half.

DoLT solves the entire pipeline **in one shot, properly**.

| Traditional Approach | DoLT |
|---------------------|------|
| Write preprocessing scripts per project | Single `dolt run` command |
| Lose document structure, extract text only | Preserve sections, tables, code blocks |
| Lock-in to frameworks (LangChain, etc.) | Standalone CLI tool |
| Depend on cloud SaaS | Local-first, works offline |

---

## Key Features

**Ingest** -- Collect documents from files, directories, and URLs with change detection.

**Parse** -- Structurally extract text, sections, tables, and code blocks from PDF, DOCX, HTML, and Markdown.

**Chunk** -- Split with context preservation using Token, Structure, or Hybrid modes.

**Enrich** -- Automatically attach metadata (title, author, section path, word count).

**Embed** -- Generate vectors via OpenAI, Cohere, or local models with batching and auto-retry.

**Export** -- Send to Qdrant, Pinecone, Weaviate, PostgreSQL, or JSON.

---

## Pipeline

```text
Source (File / Dir / URL)
  |
  v
Ingest --- Collect, SHA-256 change detection
  |
  v
Parse ---- Extract text, sections, tables, code blocks
  |
  v
Chunk ---- Hybrid split, overlap
  |
  v
Enrich --- Auto-attach metadata
  |
  v
Embed ---- Vectorize (batch + retry)
  |
  v
Export --- Vector DB / JSON / PostgreSQL
```

---

## Installation

```bash
pip install dolt
```

Or install from source:

```bash
git clone https://github.com/re-rank/DoLT.git
cd dolt
pip install -e .
```

---

## Quick Start

### 1. Full Pipeline (simplest)

```bash
# PDF -> Qdrant
dolt run ./report.pdf --target qdrant

# Entire directory -> JSON
dolt run ./documents/ --target json --output ./output.json

# Local embedding (no API key needed)
dolt run ./docs/ --provider local --model all-MiniLM-L6-v2 --target json
```

### 2. Step by Step

```bash
dolt ingest ./documents/
dolt parse
dolt chunk --mode hybrid --max-tokens 512 --overlap 50
dolt embed --provider openai
dolt export --target qdrant --collection my_docs
```

### 3. Check Status

```bash
dolt status
```

```text
DoLT Status:
  Documents: 5 (3 new, 1 updated, 1 unchanged)
  Parsed:    4
  Chunks:    127
  Embedded:  127
  Exported:  0 (not yet exported)
```

---

## Supported Formats

| Format | Extensions | Extracted Elements |
|--------|-----------|-------------------|
| PDF | `.pdf` | Text, pages, sections, tables |
| DOCX | `.docx` | Text, headings, tables |
| HTML | `.html` `.htm` | Body text, sections, tables, code blocks |
| Markdown | `.md` | Headings, code blocks, tables |

---

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="sk-..."      # OpenAI embedding
export COHERE_API_KEY="..."          # Cohere embedding
export PINECONE_API_KEY="..."        # Pinecone export
export DATABASE_URL="postgres://..." # PostgreSQL export
```

### Config File (dolt.yaml)

```yaml
chunking:
  mode: hybrid
  max_tokens: 512
  overlap_tokens: 50

embedding:
  provider: openai
  model: text-embedding-3-small

export:
  target: qdrant
  qdrant:
    url: localhost
    port: 6333
    collection: dolt_documents
```

> Priority: CLI options > environment variables > dolt.yaml > defaults.

---

## Chunking Modes

| Mode | Description | Best For |
|------|------------|----------|
| `token` | Fixed token sliding window | Long unstructured text |
| `structure` | Split at section (heading) boundaries | Well-structured documents |
| `hybrid` (default) | Section-based + token re-split | Most cases |

- Tables become independent chunks (`table` type, converted to Markdown)
- Code blocks become independent chunks (`code` type)
- Overlap applies only between chunks within the same section

---

## Embedding Providers

| Provider | Model | Dimensions | Notes |
|----------|-------|-----------|-------|
| `openai` | text-embedding-3-small | 1536 | Default |
| `openai` | text-embedding-3-large | 3072 | Higher quality |
| `cohere` | embed-multilingual-v3.0 | 1024 | Multilingual |
| `local` | all-MiniLM-L6-v2 | 384 | No API key needed |

---

## Plugins

DoLT provides 4 extension points:

| Extension Point | entry_point Group |
|----------------|-------------------|
| Parser | `dolt.parsers` |
| Metadata Enricher | `dolt.metadata_plugins` |
| Embedding Provider | `dolt.embedding_providers` |
| Exporter | `dolt.exporters` |

### Custom Metadata Plugin Example

```python
from dolt.metadata.base_plugin import MetadataPlugin

class LanguageDetectorPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "language_detector"

    def enrich(self, chunk, doc) -> dict:
        return {"detected_language": detect(chunk.content)}
```

```toml
# pyproject.toml
[project.entry-points."dolt.metadata_plugins"]
language_detector = "my_plugin:LanguageDetectorPlugin"
```

Just `pip install` and DoLT will automatically discover the plugin.

---

## Contributing

All contributions are welcome -- bug reports, feature requests, code, documentation improvements, and more.

### Development Setup

```bash
git clone https://github.com/re-rank/DoLT.git
cd dolt
pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/unit/test_parsing.py

# Coverage report
pytest --cov=dolt --cov-report=html
```

### How to Contribute

1. Check existing issues or create a new one.
2. Create a branch from `main`. (`feat/feature-name`, `fix/bug-name`)
3. Write code and add tests.
4. Make sure linting passes:
   ```bash
   ruff check src/
   mypy src/
   ```
5. Open a Pull Request.

### Code Style

- **Linter**: ruff
- **Type Checker**: mypy (strict)
- **Line Length**: 100
- **Python**: 3.10+, type hints required

---

## License

[Apache License 2.0](LICENSE)
