
# 📄 DoLT OSS 기능명세서

Version: v1.0
Scope: Open Source Core Only

---

# 1️⃣ 시스템 개요

## 1.1 목적

DoLT는 비정형 문서를 AI/RAG에 적합한 구조화 데이터로 변환하는
Document-native ELT 엔진이다.

## 1.2 범위

포함:

* Ingestion
* Parsing
* Chunking
* Metadata Enrichment
* Embedding
* Export

제외 (Cloud 영역):

* Definition Graph
* Provenance Engine
* Monitoring
* Multi-tenant
* Feedback learning

---

# 2️⃣ 전체 아키텍처 구조

```text
Source
 ↓
Ingestor
 ↓
Parser
 ↓
Chunker
 ↓
Metadata
 ↓
Embedding
 ↓
Exporter
```

---

# 3️⃣ 모듈별 기능명세

---

# A. Ingestion Module

## A.1 기능

| 기능 ID  | 기능명          | 설명            |
| ------ | ------------ | ------------- |
| ING-01 | 파일 단일 ingest | 단일 파일 수집      |
| ING-02 | 폴더 ingest    | 디렉토리 전체 수집    |
| ING-03 | URL ingest   | 웹 문서 수집       |
| ING-04 | 변경 감지        | hash 기반 변경 확인 |

---

## A.2 입력

* file_path (string)
* directory_path (string)
* url (string)

---

## A.3 출력

```json
{
  "doc_id": "uuid",
  "source": "path or url",
  "hash": "sha256",
  "status": "new | unchanged | updated"
}
```

---

## A.4 예외 처리

| 코드         | 설명         |
| ---------- | ---------- |
| ING-ERR-01 | 파일 없음      |
| ING-ERR-02 | 지원하지 않는 포맷 |
| ING-ERR-03 | URL 연결 실패  |

---

# B. Parsing Engine

## B.1 기능

| 기능 ID  | 기능명     |
| ------ | ------- |
| PAR-01 | 텍스트 추출  |
| PAR-02 | 페이지 분리  |
| PAR-03 | 섹션 인식   |
| PAR-04 | 표 분리    |
| PAR-05 | 코드블록 분리 |

---

## B.2 인터페이스

```python
class BaseParser:
    def parse(file_path) -> StructuredDocument
```

---

## B.3 출력 모델

```python
class StructuredDocument:
    doc_id: str
    raw_text: str
    pages: List[Page]
    sections: List[Section]
    metadata: dict
```

---

## B.4 비기능 요구사항

* 100MB 이하 PDF 처리 가능
* 평균 50페이지 문서 5초 이내 처리

---

# C. Chunking Module

## C.1 기능

| 기능 ID  | 기능명         |
| ------ | ----------- |
| CHK-01 | Token 기반 분할 |
| CHK-02 | 구조 기반 분할    |
| CHK-03 | Hybrid 분할   |
| CHK-04 | Overlap 적용  |

---

## C.2 입력

* StructuredDocument
* max_tokens (int)
* overlap (int)
* mode (string)

---

## C.3 출력

```python
class Chunk:
    chunk_id: str
    doc_id: str
    content: str
    start_offset: int
    end_offset: int
    metadata: dict
```

---

## C.4 제약

* chunk 최대 2000 tokens
* overlap 최대 500 tokens

---

# D. Metadata Enrichment Module

## D.1 기능

| 기능 ID  | 기능명      |
| ------ | -------- |
| MET-01 | 기본 메타 추출 |
| MET-02 | 단어 수 계산  |
| MET-03 | 섹션 경로 기록 |
| MET-04 | 플러그인 확장  |

---

## D.2 플러그인 인터페이스

```python
class MetadataPlugin:
    def enrich(chunk: Chunk) -> dict
```

---

## D.3 출력 예시

```json
{
  "title": "Contract",
  "author": "John Doe",
  "word_count": 1023,
  "section_path": ["1", "1.1"]
}
```

---

# E. Embedding Module

## E.1 기능

| 기능 ID  | 기능명                   |
| ------ | --------------------- |
| EMB-01 | OpenAI embedding      |
| EMB-02 | Cohere embedding      |
| EMB-03 | Local model embedding |
| EMB-04 | Batch 처리              |
| EMB-05 | Retry 처리              |

---

## E.2 인터페이스

```python
class EmbeddingProvider:
    def embed(texts: List[str]) -> List[List[float]]
```

---

## E.3 제약

* Batch 최대 100 chunks
* API rate limit 대응

---

# F. Export Module

## F.1 기능

| 기능 ID  | 기능명             |
| ------ | --------------- |
| EXP-01 | Qdrant export   |
| EXP-02 | Pinecone export |
| EXP-03 | Weaviate export |
| EXP-04 | JSON export     |
| EXP-05 | Postgres export |

---

## F.2 인터페이스

```python
class Exporter:
    def export(chunks: List[Chunk], embeddings: List[List[float]])
```

---

## F.3 Vector DB 필수 필드

* id
* vector
* payload (metadata 포함)

---

# 4️⃣ CLI 명세

## 명령어 구조

```bash
dolt ingest <path>
dolt parse
dolt chunk
dolt embed
dolt export
```

---

## CLI 옵션

| 옵션           | 설명           |
| ------------ | ------------ |
| --mode       | chunk 모드     |
| --max-tokens | 최대 토큰        |
| --overlap    | 오버랩          |
| --vector     | vector DB 타입 |

---

# 5️⃣ 데이터 저장 구조

로컬 저장 디렉토리:

```text
.dolt/
 ├── documents.json
 ├── chunks.json
 ├── embeddings.json
 └── cache/
```

---

# 6️⃣ 성능 요구사항

| 항목                  | 기준     |
| ------------------- | ------ |
| PDF 100페이지 처리       | 10초 이내 |
| 10,000 chunks embed | 3분 이내  |
| 메모리 사용              | 2GB 이하 |

---

# 7️⃣ 테스트 요구사항

* Unit Test Coverage 80% 이상
* 대형 PDF 테스트
* 손상된 파일 테스트
* 중복 ingest 테스트

---

# 8️⃣ 보안 요구사항

* API Key 환경변수 관리
* 민감정보 로그 출력 금지
* 파일 경로 traversal 방지

---

# 9️⃣ 확장 고려사항

향후 추가 가능:

* Streaming ingestion
* Incremental semantic diff
* Chunk versioning
* Embedding version 관리

---

# 🔟 MVP 개발 우선순위

### Phase 1 (필수)
* Ingestion
* PDF/DOCX Parser
* Hybrid Chunker
* Qdrant Export
* CLI
* Plugin 시스템
* Pinecone 지원
* Docker 지원

