# DoLT - Document-native ELT Engine 상세 기획서

Version: v1.0
Date: 2026-02-26
Base: PRD.md v1.0

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [기술 스택](#2-기술-스택)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [핵심 데이터 모델](#4-핵심-데이터-모델)
5. [모듈 상세 설계](#5-모듈-상세-설계)
   - A. [Ingestion Module](#a-ingestion-module)
   - B. [Parsing Engine](#b-parsing-engine)
   - C. [Chunking Module](#c-chunking-module)
   - D. [Metadata Enrichment Module](#d-metadata-enrichment-module)
   - E. [Embedding Module](#e-embedding-module)
   - F. [Export Module](#f-export-module)
6. [Plugin System](#6-plugin-system)
7. [Pipeline Orchestrator](#7-pipeline-orchestrator)
8. [CLI 상세 설계](#8-cli-상세-설계)
9. [Configuration System](#9-configuration-system)
10. [로컬 저장소 설계](#10-로컬-저장소-설계)
11. [에러 처리 체계](#11-에러-처리-체계)
12. [로깅 체계](#12-로깅-체계)
13. [성능 요구사항](#13-성능-요구사항)
14. [테스트 전략](#14-테스트-전략)
15. [보안 요구사항](#15-보안-요구사항)
16. [Docker 지원](#16-docker-지원)
17. [개발 로드맵](#17-개발-로드맵)

---

## 1. 시스템 개요

### 1.1 목적

DoLT(Document-native ELT)는 비정형 문서(PDF, DOCX, HTML, Markdown 등)를 AI/RAG 파이프라인에 즉시 사용 가능한 구조화 데이터로 변환하는 오픈소스 ELT 엔진이다.

### 1.2 핵심 가치

| 가치 | 설명 |
|------|------|
| **문서 원본 중심** | 원본 문서의 구조(섹션, 표, 코드블록)를 최대한 보존 |
| **파이프라인 자동화** | Ingest → Parse → Chunk → Enrich → Embed → Export 전 과정 자동화 |
| **확장성** | Plugin 기반 아키텍처로 Parser, Enricher, Exporter 자유롭게 확장 |
| **로컬 우선** | 클라우드 의존 없이 로컬에서 완전히 동작 |

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| Document | 하나의 입력 파일 또는 URL에서 수집된 원본 단위 |
| StructuredDocument | Parser가 추출한 구조화된 문서 객체 |
| Section | 문서 내 논리적 구획 (제목 기반) |
| Chunk | 검색/임베딩 단위로 분할된 텍스트 조각 |
| Enrichment | Chunk에 부가 메타데이터를 추가하는 작업 |
| Embedding | Chunk 텍스트를 벡터로 변환하는 작업 |
| Pipeline | Ingest → Export까지의 전체 처리 흐름 |

### 1.4 전체 데이터 흐름

```text
[Source Files / URLs]
        │
        ▼
┌─────────────────┐
│  Ingestor       │  파일/URL 수집, 중복 감지, doc_id 발급
│  (ING-01~04)    │
└────────┬────────┘
         │  IngestedDocument
         ▼
┌─────────────────┐
│  Parser         │  텍스트 추출, 페이지/섹션/표/코드블록 분리
│  (PAR-01~05)    │
└────────┬────────┘
         │  StructuredDocument
         ▼
┌─────────────────┐
│  Chunker        │  Token/구조/하이브리드 분할, 오버랩 적용
│  (CHK-01~04)    │
└────────┬────────┘
         │  List[Chunk]
         ▼
┌─────────────────┐
│  Metadata       │  기본 메타 추출, 단어 수, 섹션 경로, 플러그인
│  Enricher       │
│  (MET-01~04)    │
└────────┬────────┘
         │  List[Chunk] (enriched)
         ▼
┌─────────────────┐
│  Embedder       │  OpenAI/Cohere/Local 모델, 배치/재시도
│  (EMB-01~05)    │
└────────┬────────┘
         │  List[EmbeddedChunk]
         ▼
┌─────────────────┐
│  Exporter       │  Qdrant/Pinecone/Weaviate/JSON/Postgres
│  (EXP-01~05)    │
└─────────────────┘
```

---

## 2. 기술 스택

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| Language | Python | >= 3.10 | 전체 |
| Package Manager | Poetry / pip | latest | 의존성 관리 |
| CLI Framework | Typer | >= 0.9 | CLI 인터페이스 |
| Data Validation | Pydantic | >= 2.0 | 데이터 모델, 설정 |
| PDF Parsing | PyMuPDF (fitz) | >= 1.23 | PDF 텍스트/구조 추출 |
| DOCX Parsing | python-docx | >= 1.0 | DOCX 텍스트/구조 추출 |
| HTML Parsing | BeautifulSoup4 | >= 4.12 | HTML/웹문서 파싱 |
| Markdown Parsing | markdown-it-py | >= 3.0 | Markdown 파싱 |
| Tokenizer | tiktoken | >= 0.5 | 토큰 수 계산 |
| HTTP Client | httpx | >= 0.25 | URL 수집, API 호출 |
| Embedding Client | openai / cohere | latest | 임베딩 API 호출 |
| Local Embedding | sentence-transformers | >= 2.2 | 로컬 임베딩 모델 |
| Vector DB Client | qdrant-client, pinecone-client | latest | 벡터 DB 연동 |
| Testing | pytest | >= 7.0 | 테스트 프레임워크 |
| Linting | ruff | latest | 코드 품질 |
| Type Check | mypy | latest | 정적 타입 검사 |
| Container | Docker | latest | 컨테이너 배포 |

---

## 3. 프로젝트 구조

```text
dolt/
├── pyproject.toml              # 프로젝트 메타, 의존성
├── README.md
├── LICENSE
├── Dockerfile
├── docker-compose.yml
├── dolt.yaml.example           # 설정 파일 예시
│
├── src/
│   └── dolt/
│       ├── __init__.py
│       ├── __main__.py         # python -m dolt 진입점
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py          # Typer app 정의
│       │   ├── ingest.py       # dolt ingest 명령어
│       │   ├── parse.py        # dolt parse 명령어
│       │   ├── chunk.py        # dolt chunk 명령어
│       │   ├── embed.py        # dolt embed 명령어
│       │   ├── export.py       # dolt export 명령어
│       │   └── run.py          # dolt run (전체 파이프라인)
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── document.py     # IngestedDocument, StructuredDocument
│       │   ├── chunk.py        # Chunk, EmbeddedChunk
│       │   ├── section.py      # Page, Section, Table, CodeBlock
│       │   └── config.py       # 설정 모델
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── ingestor.py     # Ingestor 메인 클래스
│       │   ├── file_ingestor.py
│       │   ├── dir_ingestor.py
│       │   └── url_ingestor.py
│       │
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── base.py         # BaseParser ABC
│       │   ├── registry.py     # ParserRegistry
│       │   ├── pdf_parser.py
│       │   ├── docx_parser.py
│       │   ├── html_parser.py
│       │   └── markdown_parser.py
│       │
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── base.py         # BaseChunker ABC
│       │   ├── token_chunker.py
│       │   ├── structure_chunker.py
│       │   └── hybrid_chunker.py
│       │
│       ├── metadata/
│       │   ├── __init__.py
│       │   ├── enricher.py     # MetadataEnricher 메인
│       │   ├── base_plugin.py  # MetadataPlugin ABC
│       │   └── builtin/
│       │       ├── __init__.py
│       │       ├── basic_meta.py
│       │       ├── word_count.py
│       │       └── section_path.py
│       │
│       ├── embedding/
│       │   ├── __init__.py
│       │   ├── base.py         # EmbeddingProvider ABC
│       │   ├── openai_provider.py
│       │   ├── cohere_provider.py
│       │   └── local_provider.py
│       │
│       ├── export/
│       │   ├── __init__.py
│       │   ├── base.py         # BaseExporter ABC
│       │   ├── qdrant_exporter.py
│       │   ├── pinecone_exporter.py
│       │   ├── weaviate_exporter.py
│       │   ├── json_exporter.py
│       │   └── postgres_exporter.py
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   └── orchestrator.py # Pipeline 전체 흐름 제어
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   └── local_store.py  # .dolt/ 로컬 저장소 관리
│       │
│       ├── plugins/
│       │   ├── __init__.py
│       │   └── loader.py       # 플러그인 동적 로딩
│       │
│       └── utils/
│           ├── __init__.py
│           ├── hashing.py      # SHA-256 해싱
│           ├── logging.py      # 로깅 설정
│           └── tokens.py       # 토큰 카운팅 유틸
│
└── tests/
    ├── conftest.py
    ├── fixtures/               # 테스트용 샘플 파일
    │   ├── sample.pdf
    │   ├── sample.docx
    │   ├── sample.html
    │   └── sample.md
    ├── unit/
    │   ├── test_ingestion.py
    │   ├── test_parsing.py
    │   ├── test_chunking.py
    │   ├── test_metadata.py
    │   ├── test_embedding.py
    │   └── test_export.py
    └── integration/
        ├── test_pipeline.py
        └── test_cli.py
```

---

## 4. 핵심 데이터 모델

### 4.1 IngestedDocument

Ingestor가 수집 완료 후 반환하는 문서 메타 객체.

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class IngestStatus(str, Enum):
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"

class IngestedDocument(BaseModel):
    doc_id: str = Field(description="UUID v4 형식 문서 고유 ID")
    source: str = Field(description="원본 파일 경로 또는 URL")
    file_name: str = Field(description="파일명 (확장자 포함)")
    file_ext: str = Field(description="확장자 (예: .pdf, .docx)")
    file_size_bytes: int = Field(description="파일 크기 (bytes)")
    hash: str = Field(description="SHA-256 해시값")
    status: IngestStatus = Field(description="수집 상태")
    ingested_at: datetime = Field(description="수집 시각 (UTC)")
    mime_type: str = Field(description="MIME 타입 (예: application/pdf)")
```

### 4.2 Page / Section / Table / CodeBlock

Parser가 추출하는 문서 구조 요소.

```python
class Page(BaseModel):
    page_number: int = Field(description="1-based 페이지 번호")
    text: str = Field(description="페이지 전체 텍스트")
    start_offset: int = Field(description="전체 텍스트 내 시작 위치")
    end_offset: int = Field(description="전체 텍스트 내 종료 위치")

class Section(BaseModel):
    section_id: str = Field(description="섹션 고유 ID (예: sec-001)")
    title: str = Field(description="섹션 제목")
    level: int = Field(description="헤딩 레벨 (1=H1, 2=H2, ...)")
    content: str = Field(description="섹션 본문 텍스트")
    parent_id: str | None = Field(default=None, description="상위 섹션 ID")
    page_number: int | None = Field(default=None, description="소속 페이지")
    start_offset: int = Field(description="전체 텍스트 내 시작 위치")
    end_offset: int = Field(description="전체 텍스트 내 종료 위치")

class Table(BaseModel):
    table_id: str = Field(description="테이블 고유 ID")
    headers: list[str] = Field(description="컬럼 헤더 목록")
    rows: list[list[str]] = Field(description="행 데이터 (2D 배열)")
    page_number: int | None = Field(default=None)
    section_id: str | None = Field(default=None, description="소속 섹션 ID")
    markdown: str = Field(description="Markdown 테이블 표현")

class CodeBlock(BaseModel):
    code_id: str = Field(description="코드블록 고유 ID")
    language: str | None = Field(default=None, description="프로그래밍 언어")
    content: str = Field(description="코드 텍스트")
    page_number: int | None = Field(default=None)
    section_id: str | None = Field(default=None)
```

### 4.3 StructuredDocument

Parser의 최종 출력.

```python
class StructuredDocument(BaseModel):
    doc_id: str
    source: str
    raw_text: str = Field(description="전체 원본 텍스트")
    pages: list[Page] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    code_blocks: list[CodeBlock] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, description="파일 메타 (제목, 저자 등)")
    total_chars: int = Field(description="전체 문자 수")
    total_pages: int = Field(description="전체 페이지 수")
```

### 4.4 Chunk

Chunker의 출력 단위.

```python
class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    CODE = "code"

class Chunk(BaseModel):
    chunk_id: str = Field(description="UUID v4 형식 청크 고유 ID")
    doc_id: str = Field(description="소속 문서 ID")
    content: str = Field(description="청크 텍스트")
    chunk_type: ChunkType = Field(default=ChunkType.TEXT)
    chunk_index: int = Field(description="문서 내 청크 순번 (0-based)")
    start_offset: int = Field(description="원본 텍스트 내 시작 위치")
    end_offset: int = Field(description="원본 텍스트 내 종료 위치")
    token_count: int = Field(description="토큰 수")
    metadata: dict = Field(default_factory=dict)
```

### 4.5 EmbeddedChunk

임베딩 완료된 청크.

```python
class EmbeddedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    content: str
    chunk_type: ChunkType
    chunk_index: int
    token_count: int
    vector: list[float] = Field(description="임베딩 벡터")
    embedding_model: str = Field(description="사용된 임베딩 모델명")
    embedding_dim: int = Field(description="벡터 차원 수")
    metadata: dict = Field(default_factory=dict)
```

---

## 5. 모듈 상세 설계

---

### A. Ingestion Module

#### A.1 책임

- 단일 파일, 디렉토리, URL로부터 문서를 수집한다.
- SHA-256 해시 기반으로 변경 여부를 감지한다.
- 지원하지 않는 포맷을 사전 차단한다.
- 수집 결과를 로컬 저장소(`.dolt/documents.json`)에 기록한다.

#### A.2 지원 포맷

| 포맷 | 확장자 | MIME Type | Phase |
|------|--------|-----------|-------|
| PDF | .pdf | application/pdf | 1 |
| DOCX | .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | 1 |
| HTML | .html, .htm | text/html | 1 |
| Markdown | .md | text/markdown | 1 |
| Plain Text | .txt | text/plain | 2 |
| CSV | .csv | text/csv | 2 |

#### A.3 클래스 설계

```python
class Ingestor:
    """통합 Ingestor - 소스 타입에 따라 적절한 sub-ingestor 위임."""

    def ingest_file(self, file_path: str) -> IngestedDocument:
        """
        단일 파일 수집.

        동작:
        1. file_path 존재 여부 확인
        2. 확장자로 지원 포맷 검증
        3. SHA-256 해시 계산
        4. 로컬 저장소에서 기존 해시 조회 → status 결정
        5. IngestedDocument 생성 및 저장소 기록

        예외:
        - FileNotFoundError → ING-ERR-01
        - UnsupportedFormatError → ING-ERR-02
        """

    def ingest_directory(
        self,
        dir_path: str,
        recursive: bool = True,
        glob_pattern: str = "*",
    ) -> list[IngestedDocument]:
        """
        디렉토리 내 파일 일괄 수집.

        동작:
        1. dir_path 존재 여부 확인
        2. glob_pattern으로 대상 파일 필터링
        3. 지원 포맷 파일만 ingest_file() 호출
        4. 결과 집계 반환 (성공/실패/스킵 카운트 로깅)
        """

    def ingest_url(self, url: str) -> IngestedDocument:
        """
        URL에서 문서 수집.

        동작:
        1. URL 유효성 검증 (scheme, domain)
        2. HTTP GET 요청 (timeout: 30초, max_size: 100MB)
        3. Content-Type으로 포맷 판별
        4. 임시 파일로 저장 후 ingest_file() 위임

        예외:
        - ConnectionError, TimeoutError → ING-ERR-03
        - Content-Type 미지원 → ING-ERR-02
        """
```

#### A.4 변경 감지 로직

```text
1. 파일의 SHA-256 해시 계산
2. .dolt/documents.json에서 동일 source의 기존 레코드 검색
3. 판정:
   - 기존 레코드 없음 → status = "new"
   - 기존 해시와 동일 → status = "unchanged"
   - 기존 해시와 다름 → status = "updated", 기존 doc_id 유지
4. "unchanged"인 경우 후속 파이프라인 스킵 가능 (설정에 따라)
```

#### A.5 에러 코드

| 코드 | 예외 클래스 | 원인 | 복구 방법 |
|------|-------------|------|-----------|
| ING-ERR-01 | `FileNotFoundError` | 파일 경로 존재하지 않음 | 경로 확인 후 재시도 |
| ING-ERR-02 | `UnsupportedFormatError` | 지원하지 않는 파일 확장자 | 지원 포맷 목록 안내 |
| ING-ERR-03 | `URLFetchError` | URL 연결 실패, 타임아웃 | 네트워크 확인, URL 검증 |
| ING-ERR-04 | `FileTooLargeError` | 100MB 초과 파일 | 파일 분할 또는 제한 완화 |

---

### B. Parsing Engine

#### B.1 책임

- 지원 포맷별 전용 Parser로 텍스트를 추출한다.
- 페이지, 섹션(헤딩 계층), 표, 코드블록을 구조적으로 분리한다.
- 원본 텍스트 내 오프셋을 정확히 기록한다.
- Parser Registry를 통해 확장자별 Parser를 자동 매핑한다.

#### B.2 BaseParser 인터페이스

```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    """모든 파서가 구현해야 하는 추상 인터페이스."""

    @abstractmethod
    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """
        파일을 파싱하여 StructuredDocument를 반환한다.

        Args:
            file_path: 원본 파일 경로
            doc_id: Ingestor가 발급한 문서 ID

        Returns:
            StructuredDocument: 구조화된 문서 객체

        Raises:
            ParseError: 파싱 실패 시
        """

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """이 파서가 처리 가능한 확장자 목록 (예: ['.pdf'])."""
```

#### B.3 Parser Registry

```python
class ParserRegistry:
    """확장자 → Parser 매핑을 관리하는 레지스트리."""

    def register(self, parser: BaseParser) -> None:
        """파서를 레지스트리에 등록. 동일 확장자 중복 등록 시 덮어쓰기."""

    def get_parser(self, file_ext: str) -> BaseParser:
        """확장자에 맞는 파서를 반환. 없으면 UnsupportedFormatError."""

    def list_supported(self) -> list[str]:
        """지원하는 모든 확장자 목록 반환."""
```

#### B.4 PDF Parser 상세

```python
class PDFParser(BaseParser):
    """PyMuPDF 기반 PDF 파서."""

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """
        PDF 파싱 절차:

        1. PyMuPDF로 문서 열기
        2. 페이지별 순회:
           a. 텍스트 블록 추출 (get_text("blocks"))
           b. 텍스트 블록을 연결하여 페이지 텍스트 구성
           c. Page 객체 생성 (offset 계산)
        3. 전체 텍스트에서 섹션 인식:
           a. 폰트 크기 기반 헤딩 판별 (큰 폰트 = 상위 레벨)
           b. Section 계층 트리 구성
        4. 표 추출:
           a. PyMuPDF의 find_tables() 활용
           b. Table 객체로 변환 (headers, rows, markdown)
        5. 문서 메타데이터 추출 (제목, 저자, 생성일 등)
        6. StructuredDocument 조립 및 반환
        """
```

#### B.5 DOCX Parser 상세

```python
class DOCXParser(BaseParser):
    """python-docx 기반 DOCX 파서."""

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """
        DOCX 파싱 절차:

        1. python-docx로 문서 열기
        2. 문단(Paragraph) 순회:
           a. 스타일명으로 헤딩 레벨 판별 (Heading 1~6)
           b. 일반 문단은 현재 섹션에 누적
        3. 표(Table) 추출:
           a. doc.tables 순회
           b. 셀 텍스트 추출 → Table 객체 생성
        4. 전체 텍스트 조합 및 Page 구성 (DOCX는 단일 페이지로 처리)
        5. 문서 속성 추출 (core_properties: 제목, 저자 등)
        """
```

#### B.6 HTML Parser 상세

```python
class HTMLParser(BaseParser):
    """BeautifulSoup4 기반 HTML 파서."""

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """
        HTML 파싱 절차:

        1. HTML 파일 읽기 (인코딩 자동 감지)
        2. BeautifulSoup으로 DOM 파싱
        3. <script>, <style>, <nav>, <footer> 등 노이즈 태그 제거
        4. <h1>~<h6> 태그로 섹션 구조 추출
        5. <table> 태그 → Table 객체 변환
        6. <pre><code> 태그 → CodeBlock 객체 변환
        7. 본문 텍스트 추출 (get_text())
        """
```

#### B.7 Markdown Parser 상세

```python
class MarkdownParser(BaseParser):
    """markdown-it-py 기반 Markdown 파서."""

    def parse(self, file_path: str, doc_id: str) -> StructuredDocument:
        """
        Markdown 파싱 절차:

        1. Markdown 파일 읽기
        2. markdown-it-py로 AST 생성
        3. heading 토큰으로 섹션 구조 추출
        4. fence 토큰 → CodeBlock 객체 (language 포함)
        5. table 토큰 → Table 객체
        6. 전체 텍스트 조합
        """
```

#### B.8 비기능 요구사항

| 항목 | 기준 | 측정 방법 |
|------|------|-----------|
| PDF 최대 크기 | 100MB | 파일 크기 사전 검증 |
| 50페이지 PDF 처리 | 5초 이내 | pytest-benchmark |
| 메모리 사용 | 파일 크기의 3배 이내 | memory_profiler |
| 인코딩 지원 | UTF-8, CP949, Latin-1 | 자동 감지 (charset-normalizer) |

---

### C. Chunking Module

#### C.1 책임

- StructuredDocument를 검색/임베딩에 적합한 크기의 Chunk로 분할한다.
- 3가지 모드(Token, Structure, Hybrid)를 지원한다.
- 문맥 보존을 위한 Overlap을 적용한다.
- 표/코드블록은 독립 청크로 분리한다.

#### C.2 BaseChunker 인터페이스

```python
from abc import ABC, abstractmethod

class ChunkMode(str, Enum):
    TOKEN = "token"
    STRUCTURE = "structure"
    HYBRID = "hybrid"

class ChunkConfig(BaseModel):
    mode: ChunkMode = ChunkMode.HYBRID
    max_tokens: int = Field(default=512, ge=100, le=2000)
    overlap_tokens: int = Field(default=50, ge=0, le=500)
    tokenizer_model: str = Field(default="cl100k_base")

class BaseChunker(ABC):
    def __init__(self, config: ChunkConfig): ...

    @abstractmethod
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        """StructuredDocument를 Chunk 리스트로 분할."""
```

#### C.3 Token Chunker (CHK-01)

```text
알고리즘:
1. raw_text를 tiktoken으로 토큰화
2. max_tokens 단위로 슬라이딩 윈도우 분할
3. overlap_tokens만큼 이전 청크 끝부분을 다음 청크 시작에 포함
4. 문장 경계(마침표, 줄바꿈)에서 분할 지점 보정
5. 각 Chunk에 start_offset, end_offset, token_count 기록
```

#### C.4 Structure Chunker (CHK-02)

```text
알고리즘:
1. sections 리스트를 순회
2. 각 섹션을 독립 청크로 생성
3. 섹션 크기가 max_tokens 초과 시:
   a. 하위 섹션이 있으면 하위 섹션 단위로 분할
   b. 하위 섹션 없으면 Token Chunker로 폴백
4. 표/코드블록은 소속 섹션과 별도 청크로 분리
   - 표 → chunk_type = "table", content = markdown 표현
   - 코드 → chunk_type = "code", content = 코드 텍스트
```

#### C.5 Hybrid Chunker (CHK-03, 기본값)

```text
알고리즘 (Structure + Token 결합):
1. 1차: Structure Chunker로 섹션 기반 분할
2. 2차: 각 섹션 청크가 max_tokens 초과 시 Token Chunker로 재분할
3. 3차: 각 섹션 청크가 min_tokens(100) 미만이면 인접 청크와 병합
4. 표/코드블록: 독립 청크 유지 (max_tokens 초과해도 분할하지 않음)
5. Overlap 적용: 동일 섹션 내 청크 간에만 적용
```

#### C.6 제약사항

| 항목 | 제약 | 근거 |
|------|------|------|
| max_tokens 상한 | 2,000 | 대부분의 임베딩 모델 입력 제한 |
| max_tokens 하한 | 100 | 의미 있는 검색 단위 최소 크기 |
| overlap 상한 | 500 | max_tokens의 25%를 넘지 않도록 권장 |
| overlap 상한 비율 | max_tokens * 0.5 이하 | 중복 과다 방지 |

---

### D. Metadata Enrichment Module

#### D.1 책임

- 모든 Chunk에 기본 메타데이터를 추가한다.
- 플러그인 방식으로 커스텀 Enricher를 확장할 수 있다.
- 빌트인 Enricher 3종을 기본 제공한다.

#### D.2 빌트인 Enricher 상세

**MET-01: BasicMetaEnricher**
```python
class BasicMetaEnricher(MetadataPlugin):
    """문서 수준 기본 메타데이터를 청크에 전파."""

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        """
        추가 필드:
        - title: 문서 제목 (metadata에서 추출, 없으면 파일명)
        - author: 저자 (metadata에서 추출, 없으면 "unknown")
        - source: 원본 소스 경로/URL
        - file_type: 파일 확장자
        - total_pages: 전체 페이지 수
        - doc_id: 문서 ID
        """
```

**MET-02: WordCountEnricher**
```python
class WordCountEnricher(MetadataPlugin):
    """청크 단위 단어/문자 수 계산."""

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        """
        추가 필드:
        - word_count: 공백 기준 단어 수
        - char_count: 문자 수 (공백 포함)
        - avg_word_length: 평균 단어 길이
        """
```

**MET-03: SectionPathEnricher**
```python
class SectionPathEnricher(MetadataPlugin):
    """청크가 속한 섹션의 계층 경로를 기록."""

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        """
        추가 필드:
        - section_path: 섹션 계층 배열 (예: ["1. 개요", "1.1 목적"])
        - section_title: 직속 섹션 제목
        - section_level: 직속 섹션 레벨 (1~6)
        - page_number: 소속 페이지 번호 (가능한 경우)
        """
```

#### D.3 MetadataPlugin 인터페이스

```python
class MetadataPlugin(ABC):
    """커스텀 메타데이터 플러그인의 추상 인터페이스."""

    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 이름 (고유 식별자)."""

    @abstractmethod
    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        """
        청크에 추가할 메타데이터 딕셔너리를 반환.
        반환된 dict는 chunk.metadata에 병합된다.

        주의:
        - 기존 metadata 키를 덮어쓰지 않도록 네임스페이스 사용 권장
          (예: "plugin_name.field_name")
        - 이 메서드는 순수 함수여야 하며 부작용이 없어야 한다.
        """
```

#### D.4 MetadataEnricher (오케스트레이터)

```python
class MetadataEnricher:
    """등록된 플러그인을 순서대로 실행하여 청크를 enrichment."""

    def __init__(self, plugins: list[MetadataPlugin] | None = None):
        """기본값: 빌트인 3종 자동 등록."""

    def add_plugin(self, plugin: MetadataPlugin) -> None:
        """플러그인 추가 등록."""

    def enrich(self, chunks: list[Chunk], doc: StructuredDocument) -> list[Chunk]:
        """
        모든 청크에 대해 등록된 플러그인을 순차 실행.
        각 플러그인 반환 dict를 chunk.metadata에 병합.
        원본 Chunk를 변경하지 않고 새 Chunk 리스트를 반환.
        """
```

---

### E. Embedding Module

#### E.1 책임

- Chunk 텍스트를 벡터로 변환한다.
- 3가지 Provider(OpenAI, Cohere, Local)를 지원한다.
- 배치 처리, Rate Limit 대응, 재시도 로직을 포함한다.

#### E.2 EmbeddingProvider 인터페이스

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 임베딩 벡터 리스트로 변환."""

    @abstractmethod
    def model_name(self) -> str:
        """사용 중인 모델명 반환."""

    @abstractmethod
    def dimension(self) -> int:
        """출력 벡터 차원 수 반환."""
```

#### E.3 OpenAI Provider 상세

```python
class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding API 사용."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,  # 없으면 OPENAI_API_KEY 환경변수
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,  # 초, 지수 백오프 적용
    ): ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        동작:
        1. texts를 batch_size 단위로 분할
        2. 각 배치에 대해 OpenAI API 호출
        3. Rate limit (429) 수신 시 지수 백오프 재시도
        4. 전체 결과 합산 반환

        지원 모델:
        - text-embedding-3-small (1536 dim, 저비용)
        - text-embedding-3-large (3072 dim, 고품질)
        - text-embedding-ada-002 (1536 dim, 레거시)
        """
```

#### E.4 Cohere Provider 상세

```python
class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere Embed API 사용."""

    def __init__(
        self,
        model: str = "embed-multilingual-v3.0",
        api_key: str | None = None,  # 없으면 COHERE_API_KEY 환경변수
        input_type: str = "search_document",  # or "search_query"
        batch_size: int = 96,  # Cohere 제한
        max_retries: int = 3,
    ): ...
```

#### E.5 Local Provider 상세

```python
class LocalEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers 기반 로컬 임베딩."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",  # or "cuda"
        batch_size: int = 64,
    ): ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        동작:
        1. 모델 로딩 (최초 1회, 이후 캐시)
        2. texts를 batch_size 단위로 encode
        3. numpy array → list[list[float]] 변환

        장점: API 키 불필요, 오프라인 동작, 무료
        단점: GPU 없으면 상대적으로 느림
        """
```

#### E.6 제약 및 설정

| 항목 | 기본값 | 범위 |
|------|--------|------|
| batch_size | 100 (OpenAI), 96 (Cohere), 64 (Local) | 1~500 |
| max_retries | 3 | 0~10 |
| retry_delay (초) | 1.0 (지수 백오프: 1, 2, 4...) | 0.1~30 |
| timeout (초) | 60 | 10~300 |

---

### F. Export Module

#### F.1 책임

- EmbeddedChunk를 목적지(Vector DB, 파일, DB)로 내보낸다.
- 각 목적지별 필수 필드를 매핑한다.
- Upsert 방식으로 중복 데이터를 처리한다.

#### F.2 BaseExporter 인터페이스

```python
class BaseExporter(ABC):
    @abstractmethod
    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """
        임베딩 완료된 청크를 목적지로 내보낸다.

        Returns:
            ExportResult: 성공/실패 건수 및 상세 정보
        """

    @abstractmethod
    def validate_connection(self) -> bool:
        """내보내기 전 연결 상태를 확인한다."""

class ExportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    destination: str  # 예: "qdrant://localhost:6333/my_collection"
```

#### F.3 Qdrant Exporter (EXP-01)

```python
class QdrantExporter(BaseExporter):
    def __init__(
        self,
        url: str = "localhost",
        port: int = 6333,
        collection_name: str = "dolt_documents",
        api_key: str | None = None,
        recreate_collection: bool = False,
    ): ...

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """
        동작:
        1. 컬렉션 존재 확인, 없으면 자동 생성 (벡터 차원 자동 감지)
        2. EmbeddedChunk → PointStruct 변환:
           - id: chunk_id (UUID)
           - vector: vector 필드
           - payload: {content, doc_id, chunk_type, chunk_index,
                       token_count, metadata(전체), embedding_model}
        3. batch upsert (batch_size=100)
        """
```

#### F.4 Pinecone Exporter (EXP-02)

```python
class PineconeExporter(BaseExporter):
    def __init__(
        self,
        api_key: str | None = None,  # PINECONE_API_KEY
        index_name: str = "dolt-documents",
        namespace: str = "",
    ): ...

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """
        동작:
        1. 인덱스 존재 확인
        2. EmbeddedChunk → (id, vector, metadata) 변환
           - metadata에 content 포함 (Pinecone은 payload 크기 제한 주의)
        3. batch upsert (batch_size=100)
        """
```

#### F.5 JSON Exporter (EXP-04)

```python
class JSONExporter(BaseExporter):
    def __init__(
        self,
        output_path: str = ".dolt/export.json",
        include_vectors: bool = True,
        pretty: bool = True,
    ): ...

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """
        동작:
        1. EmbeddedChunk 리스트를 JSON 직렬화
        2. include_vectors=False이면 vector 필드 제외 (디버깅용)
        3. output_path에 파일 저장

        출력 구조:
        {
          "export_at": "ISO datetime",
          "total_chunks": N,
          "embedding_model": "model_name",
          "embedding_dim": 1536,
          "chunks": [...]
        }
        """
```

#### F.6 Postgres Exporter (EXP-05)

```python
class PostgresExporter(BaseExporter):
    def __init__(
        self,
        connection_string: str | None = None,  # DATABASE_URL 환경변수
        table_name: str = "dolt_chunks",
        use_pgvector: bool = True,
    ): ...

    def export(self, chunks: list[EmbeddedChunk]) -> ExportResult:
        """
        동작:
        1. pgvector 확장 존재 확인, 없으면 안내 메시지
        2. 테이블 자동 생성 (없는 경우):
           CREATE TABLE dolt_chunks (
             chunk_id TEXT PRIMARY KEY,
             doc_id TEXT NOT NULL,
             content TEXT NOT NULL,
             chunk_type TEXT,
             chunk_index INT,
             token_count INT,
             vector vector(dim),
             metadata JSONB,
             embedding_model TEXT,
             created_at TIMESTAMPTZ DEFAULT NOW()
           );
        3. batch upsert (ON CONFLICT chunk_id DO UPDATE)
        """
```

---

## 6. Plugin System

### 6.1 플러그인 구조

DoLT는 4가지 확장 지점(Extension Point)을 제공한다.

| 확장 지점 | 베이스 클래스 | 등록 방법 |
|-----------|---------------|-----------|
| Parser | `BaseParser` | `ParserRegistry.register()` |
| Metadata Enricher | `MetadataPlugin` | `MetadataEnricher.add_plugin()` |
| Embedding Provider | `EmbeddingProvider` | 설정 파일 지정 |
| Exporter | `BaseExporter` | 설정 파일 지정 |

### 6.2 플러그인 로딩

```python
class PluginLoader:
    """Python entry_points 기반 플러그인 자동 발견 및 로딩."""

    def discover(self, group: str) -> list[type]:
        """
        entry_points에서 지정 그룹의 플러그인을 발견한다.

        그룹명:
        - dolt.parsers
        - dolt.metadata_plugins
        - dolt.embedding_providers
        - dolt.exporters

        사용자가 pip install로 설치한 패키지 중
        해당 entry_point 그룹에 등록된 클래스를 자동 발견한다.
        """

    def load(self, group: str, name: str) -> object:
        """특정 이름의 플러그인을 인스턴스화하여 반환."""
```

### 6.3 커스텀 플러그인 작성 예시

```python
# my_plugin/language_detector.py
from dolt.metadata.base_plugin import MetadataPlugin
from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument

class LanguageDetectorPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "language_detector"

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        # langdetect 등으로 언어 감지
        detected = detect(chunk.content)
        return {"detected_language": detected}
```

```toml
# my_plugin/pyproject.toml
[project.entry-points."dolt.metadata_plugins"]
language_detector = "my_plugin.language_detector:LanguageDetectorPlugin"
```

---

## 7. Pipeline Orchestrator

### 7.1 책임

- 전체 파이프라인(Ingest → Export)을 순차 실행한다.
- 각 단계의 결과를 로컬 저장소에 중간 저장한다.
- 특정 단계부터 재개(resume) 가능하다.
- 진행 상황을 로깅한다.

### 7.2 인터페이스

```python
class PipelineOrchestrator:
    def __init__(self, config: DoltConfig): ...

    def run(
        self,
        source: str,
        start_from: str | None = None,  # "ingest" | "parse" | "chunk" | "embed" | "export"
        skip_unchanged: bool = True,
    ) -> PipelineResult:
        """
        전체 파이프라인 실행.

        동작:
        1. Ingest: source로부터 문서 수집
           - skip_unchanged=True이면 "unchanged" 상태 문서 스킵
        2. Parse: 수집된 문서 파싱
        3. Chunk: 파싱 결과 분할
        4. Enrich: 메타데이터 추가
        5. Embed: 벡터 변환
        6. Export: 목적지로 내보내기

        각 단계 완료 시 .dolt/ 로컬 저장소에 중간 결과 저장.
        start_from 지정 시 해당 단계부터 로컬 저장소 데이터로 재개.
        """

class PipelineResult(BaseModel):
    doc_count: int
    chunk_count: int
    embedded_count: int
    exported_count: int
    elapsed_seconds: float
    stages: dict[str, StageResult]

class StageResult(BaseModel):
    stage: str
    status: str  # "success" | "partial" | "failed"
    count: int
    elapsed_seconds: float
    errors: list[str] = Field(default_factory=list)
```

---

## 8. CLI 상세 설계

### 8.1 기본 구조

```bash
dolt [global-options] <command> [command-options] [arguments]
```

### 8.2 Global Options

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `--config` | `-c` | path | `dolt.yaml` | 설정 파일 경로 |
| `--verbose` | `-v` | flag | false | 상세 로그 출력 |
| `--quiet` | `-q` | flag | false | 에러만 출력 |
| `--log-level` | | enum | INFO | DEBUG/INFO/WARNING/ERROR |
| `--version` | | flag | | 버전 출력 |
| `--help` | `-h` | flag | | 도움말 출력 |

### 8.3 명령어 상세

#### `dolt ingest`

```bash
dolt ingest <path-or-url> [options]
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `--recursive` | `-r` | flag | true | 하위 디렉토리 포함 |
| `--pattern` | `-p` | string | `*` | 파일 glob 패턴 |
| `--force` | `-f` | flag | false | unchanged 파일도 재수집 |

```bash
# 예시
dolt ingest ./docs/report.pdf
dolt ingest ./documents/ --pattern "*.pdf"
dolt ingest https://example.com/whitepaper.pdf
```

#### `dolt parse`

```bash
dolt parse [options]
```

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--doc-id` | string | all | 특정 문서만 파싱 |
| `--parser` | string | auto | 파서 지정 (auto=확장자 기반) |

#### `dolt chunk`

```bash
dolt chunk [options]
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `--mode` | `-m` | enum | hybrid | token/structure/hybrid |
| `--max-tokens` | | int | 512 | 청크 최대 토큰 수 |
| `--overlap` | | int | 50 | 오버랩 토큰 수 |
| `--doc-id` | | string | all | 특정 문서만 처리 |

#### `dolt embed`

```bash
dolt embed [options]
```

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--provider` | enum | openai | openai/cohere/local |
| `--model` | string | provider별 기본값 | 임베딩 모델 |
| `--batch-size` | int | provider별 기본값 | 배치 크기 |
| `--doc-id` | string | all | 특정 문서만 처리 |

#### `dolt export`

```bash
dolt export [options]
```

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--target` | enum | json | qdrant/pinecone/weaviate/json/postgres |
| `--url` | string | target별 기본값 | 연결 URL |
| `--collection` | string | dolt_documents | 컬렉션/인덱스명 |
| `--output` | path | .dolt/export.json | JSON export 경로 |
| `--doc-id` | string | all | 특정 문서만 처리 |

#### `dolt run` (전체 파이프라인)

```bash
dolt run <path-or-url> [options]
```

모든 단계 옵션을 통합 지원. 자주 쓰는 조합을 한 번에 실행.

```bash
# 예시: PDF를 Qdrant로 일괄 처리
dolt run ./docs/ \
  --mode hybrid \
  --max-tokens 512 \
  --provider openai \
  --target qdrant \
  --collection my_docs

# 예시: 로컬 임베딩으로 JSON 내보내기
dolt run ./report.pdf \
  --provider local \
  --model all-MiniLM-L6-v2 \
  --target json \
  --output ./output.json
```

#### `dolt status`

```bash
dolt status
```

`.dolt/` 로컬 저장소의 현재 상태를 출력한다.

```text
DoLT Status:
  Documents: 5 (3 new, 1 updated, 1 unchanged)
  Parsed:    4
  Chunks:    127
  Embedded:  127
  Exported:  0 (not yet exported)
```

#### `dolt clean`

```bash
dolt clean [options]
```

| 옵션 | 설명 |
|------|------|
| `--all` | 전체 .dolt/ 디렉토리 초기화 |
| `--doc-id <id>` | 특정 문서 관련 데이터만 삭제 |
| `--stage <name>` | 특정 단계 데이터만 삭제 |

---

## 9. Configuration System

### 9.1 설정 우선순위

```text
1. CLI 옵션 (최우선)
2. 환경변수 (DOLT_ 접두사)
3. dolt.yaml 설정 파일
4. 기본값
```

### 9.2 설정 파일 (dolt.yaml)

```yaml
# dolt.yaml

# 파싱 설정
parsing:
  encoding: auto          # auto | utf-8 | cp949 | ...

# 청킹 설정
chunking:
  mode: hybrid            # token | structure | hybrid
  max_tokens: 512
  overlap_tokens: 50
  tokenizer: cl100k_base

# 임베딩 설정
embedding:
  provider: openai        # openai | cohere | local
  model: text-embedding-3-small
  batch_size: 100
  max_retries: 3

# 내보내기 설정
export:
  target: qdrant          # qdrant | pinecone | weaviate | json | postgres
  qdrant:
    url: localhost
    port: 6333
    collection: dolt_documents
  pinecone:
    index: dolt-documents
    namespace: ""
  json:
    output: .dolt/export.json
    include_vectors: true
  postgres:
    table: dolt_chunks
    use_pgvector: true

# 메타데이터 플러그인
metadata:
  plugins:
    - basic_meta
    - word_count
    - section_path
    # - language_detector  # 커스텀 플러그인

# 로깅
logging:
  level: INFO             # DEBUG | INFO | WARNING | ERROR
  file: null              # 파일 로깅 경로 (null이면 stdout만)

# 저장소
storage:
  path: .dolt             # 로컬 저장소 경로
```

### 9.3 환경변수 매핑

| 환경변수 | 설정 경로 | 설명 |
|----------|-----------|------|
| `OPENAI_API_KEY` | - | OpenAI API 키 |
| `COHERE_API_KEY` | - | Cohere API 키 |
| `PINECONE_API_KEY` | - | Pinecone API 키 |
| `DATABASE_URL` | export.postgres.connection_string | Postgres 연결 문자열 |
| `DOLT_CHUNK_MODE` | chunking.mode | 청크 모드 |
| `DOLT_CHUNK_MAX_TOKENS` | chunking.max_tokens | 최대 토큰 |
| `DOLT_EMBED_PROVIDER` | embedding.provider | 임베딩 프로바이더 |
| `DOLT_EXPORT_TARGET` | export.target | 내보내기 대상 |
| `DOLT_LOG_LEVEL` | logging.level | 로그 레벨 |

### 9.4 DoltConfig 모델

```python
class DoltConfig(BaseModel):
    """전체 설정을 관리하는 Pydantic 모델."""

    parsing: ParsingConfig = Field(default_factory=ParsingConfig)
    chunking: ChunkConfig = Field(default_factory=ChunkConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
        cli_overrides: dict | None = None,
    ) -> "DoltConfig":
        """
        설정 로딩 순서:
        1. 기본값으로 초기화
        2. config_path의 YAML 파일 병합
        3. DOLT_ 접두사 환경변수 병합
        4. cli_overrides 병합
        """
```

---

## 10. 로컬 저장소 설계

### 10.1 디렉토리 구조

```text
.dolt/
├── documents.json          # IngestedDocument 목록
├── parsed/
│   └── {doc_id}.json       # StructuredDocument (문서별)
├── chunks/
│   └── {doc_id}.json       # Chunk 리스트 (문서별)
├── embeddings/
│   └── {doc_id}.json       # EmbeddedChunk 리스트 (문서별)
├── exports/
│   └── export_{timestamp}.json  # Export 결과 기록
├── cache/
│   └── {hash}.bin          # 다운로드 파일 캐시
└── dolt.lock               # 동시 실행 방지 락 파일
```

### 10.2 documents.json 스키마

```json
{
  "version": "1.0",
  "documents": [
    {
      "doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "./docs/report.pdf",
      "file_name": "report.pdf",
      "file_ext": ".pdf",
      "file_size_bytes": 2048576,
      "hash": "a3f2b8c9...",
      "status": "new",
      "ingested_at": "2026-02-26T12:00:00Z",
      "mime_type": "application/pdf",
      "pipeline_state": {
        "parsed": true,
        "chunked": true,
        "embedded": false,
        "exported": false
      }
    }
  ]
}
```

### 10.3 Lock 메커니즘

```python
class LocalStore:
    def acquire_lock(self, timeout: int = 30) -> bool:
        """
        .dolt/dolt.lock 파일 생성으로 배타적 접근 확보.
        lock 파일에 PID, timestamp 기록.
        timeout 초과 시 False 반환 (강제 삭제하지 않음).
        """

    def release_lock(self) -> None:
        """lock 파일 삭제."""
```

---

## 11. 에러 처리 체계

### 11.1 예외 클래스 계층

```python
class DoltError(Exception):
    """DoLT 최상위 예외."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

class IngestionError(DoltError):
    """수집 단계 에러."""

class FileNotFoundError(IngestionError): ...       # ING-ERR-01
class UnsupportedFormatError(IngestionError): ...   # ING-ERR-02
class URLFetchError(IngestionError): ...            # ING-ERR-03
class FileTooLargeError(IngestionError): ...        # ING-ERR-04

class ParseError(DoltError):
    """파싱 단계 에러."""

class CorruptedFileError(ParseError): ...           # PAR-ERR-01
class EncodingError(ParseError): ...                # PAR-ERR-02

class ChunkError(DoltError):
    """청킹 단계 에러."""

class InvalidConfigError(ChunkError): ...           # CHK-ERR-01

class EmbeddingError(DoltError):
    """임베딩 단계 에러."""

class APIKeyMissingError(EmbeddingError): ...       # EMB-ERR-01
class RateLimitError(EmbeddingError): ...           # EMB-ERR-02
class ModelNotFoundError(EmbeddingError): ...       # EMB-ERR-03

class ExportError(DoltError):
    """내보내기 단계 에러."""

class ConnectionError(ExportError): ...             # EXP-ERR-01
class CollectionNotFoundError(ExportError): ...     # EXP-ERR-02
```

### 11.2 에러 코드 전체 목록

| 코드 | 모듈 | 설명 | 심각도 |
|------|------|------|--------|
| ING-ERR-01 | Ingestion | 파일 없음 | ERROR |
| ING-ERR-02 | Ingestion | 미지원 포맷 | ERROR |
| ING-ERR-03 | Ingestion | URL 연결 실패 | ERROR |
| ING-ERR-04 | Ingestion | 파일 크기 초과 | ERROR |
| PAR-ERR-01 | Parsing | 손상된 파일 | ERROR |
| PAR-ERR-02 | Parsing | 인코딩 오류 | WARNING (폴백) |
| CHK-ERR-01 | Chunking | 잘못된 설정값 | ERROR |
| EMB-ERR-01 | Embedding | API 키 미설정 | ERROR |
| EMB-ERR-02 | Embedding | Rate limit 초과 | WARNING (재시도) |
| EMB-ERR-03 | Embedding | 모델 없음 | ERROR |
| EXP-ERR-01 | Export | 연결 실패 | ERROR |
| EXP-ERR-02 | Export | 컬렉션 없음 | WARNING (자동 생성) |

---

## 12. 로깅 체계

### 12.1 로그 포맷

```text
[2026-02-26 12:00:00] [INFO] [ingestion] Ingesting file: ./docs/report.pdf
[2026-02-26 12:00:01] [INFO] [ingestion] Document status: new (doc_id=550e8400...)
[2026-02-26 12:00:01] [INFO] [parsing] Parsing PDF: 50 pages detected
[2026-02-26 12:00:03] [INFO] [parsing] Extracted 12 sections, 3 tables
[2026-02-26 12:00:03] [INFO] [chunking] Chunking with hybrid mode (max=512, overlap=50)
[2026-02-26 12:00:04] [INFO] [chunking] Created 127 chunks
[2026-02-26 12:00:04] [INFO] [embedding] Embedding 127 chunks with openai/text-embedding-3-small
[2026-02-26 12:00:10] [INFO] [embedding] Batch 1/2 complete (100 chunks)
[2026-02-26 12:00:12] [INFO] [embedding] Batch 2/2 complete (27 chunks)
[2026-02-26 12:00:12] [INFO] [export] Exporting to qdrant://localhost:6333/dolt_documents
[2026-02-26 12:00:13] [INFO] [export] Exported 127/127 chunks successfully
[2026-02-26 12:00:13] [INFO] [pipeline] Pipeline complete in 13.2s
```

### 12.2 민감정보 마스킹

```python
# 로그 출력 시 자동 마스킹 대상:
# - API 키: sk-abc...xyz → sk-abc***xyz
# - 파일 전체 경로의 사용자명 부분
# - DB 연결 문자열의 비밀번호 부분
```

---

## 13. 성능 요구사항

| 항목 | 기준 | 측정 조건 |
|------|------|-----------|
| PDF 100페이지 파싱 | 10초 이내 | 텍스트 중심 PDF, 로컬 SSD |
| 10,000 chunks 임베딩 | 3분 이내 | OpenAI API, batch=100 |
| 메모리 최대 사용량 | 2GB 이하 | 100MB PDF 처리 시 |
| 로컬 저장소 I/O | 1초 이내 | 10,000 chunks JSON 읽기/쓰기 |
| 파이프라인 전체 (50p PDF) | 30초 이내 | Ingest~Export, OpenAI 임베딩 |

### 13.1 최적화 전략

| 전략 | 적용 대상 | 방법 |
|------|-----------|------|
| 스트리밍 파싱 | PDF Parser | 페이지 단위 순차 처리, 전체 로딩 방지 |
| 배치 처리 | Embedding | API 호출 횟수 최소화 |
| 변경 감지 스킵 | Pipeline | unchanged 문서 전체 파이프라인 스킵 |
| 중간 결과 캐싱 | Pipeline | .dolt/에 단계별 결과 저장, 재개 가능 |
| 지연 로딩 | Local Model | 실제 embed 호출 시점에 모델 로딩 |

---

## 14. 테스트 전략

### 14.1 테스트 커버리지 목표

| 구분 | 커버리지 목표 | 방법 |
|------|---------------|------|
| Unit Test | 80% 이상 | pytest, 모듈별 독립 테스트 |
| Integration Test | 주요 파이프라인 시나리오 | 실제 파일 + Mock API |
| E2E Test | CLI 명령어 전체 | subprocess 또는 Typer CliRunner |

### 14.2 테스트 시나리오

**Ingestion**
- 존재하는 PDF/DOCX/HTML/MD 파일 수집 성공
- 존재하지 않는 파일 → ING-ERR-01
- 미지원 확장자(.exe) → ING-ERR-02
- URL 수집 성공 / 실패 (mock httpx)
- 동일 파일 재수집 → status="unchanged"
- 파일 수정 후 재수집 → status="updated"
- 100MB 초과 파일 → ING-ERR-04
- 빈 디렉토리 수집 → 빈 리스트 반환
- 디렉토리 recursive + glob 패턴

**Parsing**
- PDF: 일반 텍스트 추출, 페이지 분리, 섹션 인식, 표 추출
- DOCX: 문단 추출, 헤딩 인식, 표 추출
- HTML: 노이즈 제거, 섹션/표/코드블록 추출
- Markdown: 헤딩/코드블록/표 추출
- 손상된 파일 → PAR-ERR-01
- 빈 파일 → 빈 StructuredDocument (에러 아님)
- 인코딩: UTF-8, CP949, Latin-1 자동 감지

**Chunking**
- Token 모드: 정확한 토큰 수 분할 확인
- Structure 모드: 섹션 경계 보존 확인
- Hybrid 모드: 섹션 기반 + 토큰 재분할 확인
- Overlap: 인접 청크 간 중복 텍스트 확인
- 표/코드블록: 독립 청크 분리 확인
- max_tokens 범위 초과 설정 → CHK-ERR-01
- 빈 문서 → 빈 리스트

**Embedding**
- OpenAI: Mock API로 배치 처리, 재시도 확인
- Cohere: Mock API로 배치 처리 확인
- Local: 실제 모델(all-MiniLM-L6-v2)로 임베딩 확인
- API 키 미설정 → EMB-ERR-01
- Rate limit 시뮬레이션 → 재시도 후 성공

**Export**
- JSON: 파일 생성, 스키마 검증
- Qdrant: Mock 클라이언트로 upsert 확인
- Pinecone: Mock 클라이언트로 upsert 확인
- Postgres: Mock DB로 insert 확인
- 연결 실패 → EXP-ERR-01

**Pipeline (Integration)**
- PDF → JSON 전체 파이프라인
- 디렉토리 일괄 처리
- unchanged 문서 스킵
- 중간 단계에서 재개

### 14.3 테스트 픽스처

```text
tests/fixtures/
├── sample.pdf          # 10페이지, 텍스트+표+이미지
├── sample.docx         # 5페이지, 헤딩+표
├── sample.html         # 웹 기사 형태 (nav, footer 포함)
├── sample.md           # 헤딩, 코드블록, 표 포함
├── empty.pdf           # 빈 PDF
├── corrupted.pdf       # 손상된 PDF
├── large_100p.pdf      # 100페이지 PDF (성능 테스트용)
├── cp949.txt           # CP949 인코딩 텍스트
└── sample_table.pdf    # 표가 많은 PDF
```

---

## 15. 보안 요구사항

### 15.1 API 키 관리

| 규칙 | 상세 |
|------|------|
| 저장 방식 | 환경변수만 허용, 설정 파일에 직접 입력 금지 |
| 로그 출력 | API 키 마스킹 필수 (앞 6자리 + *** + 뒤 4자리) |
| .dolt/ 내부 | API 키, 인증정보 저장 금지 |
| .gitignore | `.dolt/`, `.env` 포함 기본 제공 |

### 15.2 파일 경로 보안

```python
def validate_path(path: str, base_dir: str) -> str:
    """
    Path Traversal 공격 방지.

    검증:
    1. resolved_path = Path(path).resolve()
    2. base = Path(base_dir).resolve()
    3. resolved_path가 base 하위인지 확인
    4. 심볼릭 링크 해제 후 재검증

    위반 시 SecurityError 발생.
    """
```

### 15.3 URL 수집 보안

| 규칙 | 상세 |
|------|------|
| 허용 스킴 | http, https만 허용 |
| SSRF 방지 | 로컬 주소 (127.0.0.1, localhost, 10.x, 192.168.x) 차단 |
| 크기 제한 | 응답 100MB 초과 시 중단 |
| 타임아웃 | 연결 10초, 읽기 30초 |
| 리다이렉트 | 최대 5회 |

---

## 16. Docker 지원

### 16.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && poetry install --no-dev

COPY src/ ./src/
RUN pip install .

ENTRYPOINT ["dolt"]
```

### 16.2 docker-compose.yml

```yaml
version: "3.8"
services:
  dolt:
    build: .
    volumes:
      - ./data:/data          # 입력 파일
      - ./output:/app/.dolt   # 출력 데이터
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

### 16.3 사용 예시

```bash
# 전체 파이프라인 실행
docker compose run dolt run /data/documents/ \
  --target qdrant \
  --collection my_docs

# Qdrant만 실행
docker compose up qdrant -d
```

---

## 17. 개발 로드맵

### Phase 1 - Core MVP (4주)

| 주차 | 작업 | 산출물 |
|------|------|--------|
| 1주 | 프로젝트 세팅, 데이터 모델, 로컬 저장소 | pyproject.toml, models/, storage/ |
| 2주 | Ingestion + PDF/DOCX Parser | ingestion/, parsing/ (pdf, docx) |
| 3주 | Hybrid Chunker + Metadata Enricher | chunking/, metadata/ |
| 4주 | Embedding (OpenAI) + Qdrant Export + CLI | embedding/, export/, cli/ |

### Phase 1.5 - 확장 (2주)

| 주차 | 작업 | 산출물 |
|------|------|--------|
| 5주 | HTML/MD Parser, Plugin 시스템, Pinecone | parsing/ (html, md), plugins/ |
| 6주 | Docker, 테스트 보강, 문서화 | Dockerfile, tests/, README |

### Phase 2 - 고도화 (향후)

| 항목 | 설명 |
|------|------|
| Streaming ingestion | 대용량 파일 스트리밍 처리 |
| Incremental semantic diff | 문서 변경 시 변경된 청크만 재처리 |
| Chunk versioning | 청크 버전 관리 (시간 축) |
| Embedding version 관리 | 모델 변경 시 재임베딩 관리 |
| Weaviate / Postgres Export | 추가 Export 대상 |
| Cohere / Local Embedding | 추가 임베딩 프로바이더 |
| TXT / CSV Parser | 추가 파일 포맷 지원 |

---

## 부록: 주요 설계 결정 사항 (ADR 요약)

| 결정 | 선택 | 근거 |
|------|------|------|
| 언어 | Python 3.10+ | AI/ML 생태계 호환, 풍부한 문서 파싱 라이브러리 |
| 데이터 모델 | Pydantic v2 | 타입 안전성, 직렬화, 검증 일체화 |
| CLI | Typer | 타입 힌트 기반 자동 CLI 생성, 빠른 개발 |
| PDF 파서 | PyMuPDF | 속도 우수, 표 추출 지원, 활발한 유지보수 |
| 토크나이저 | tiktoken (cl100k_base) | OpenAI 모델과 동일 토크나이저, 정확한 토큰 카운트 |
| 로컬 저장소 | JSON 파일 기반 | DB 의존성 없음, 간단, 디버깅 용이 |
| 플러그인 | entry_points | Python 표준, pip install만으로 플러그인 등록 |
| 설정 파일 | YAML | 가독성, 중첩 구조 표현력, 주석 지원 |
