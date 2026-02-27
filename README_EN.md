<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/status-in%20development-orange?style=flat-square" alt="Status">
</p>

<h1 align="center">DoLT</h1>
<p align="center"><b>Document-native ELT Engine</b></p>
<p align="center">An open-source pipeline that transforms unstructured documents into structured data for AI/RAG</p>

<p align="center">
  <a href="README.md">한국어</a> | <b>English</b>
</p>

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

## Changelog

[View full changelog →](CHANGELOG.md)

---

## License

[Apache License 2.0](LICENSE)
