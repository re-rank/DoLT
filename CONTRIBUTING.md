# Contributing to DoLT

DoLT에 기여해 주셔서 감사합니다! 아래 가이드를 참고해 주세요.

Thank you for contributing to DoLT! Please follow the guide below.

---

## Getting Started

```bash
git clone https://github.com/re-rank/DoLT.git
cd DoLT
pip install -e ".[dev]"
pytest
```

---

## How to Contribute

### Bug Report / 버그 리포트

- [GitHub Issues](https://github.com/re-rank/DoLT/issues)에서 기존 이슈를 먼저 검색해 주세요.
- 새 이슈 작성 시 **재현 방법**, **기대 동작**, **실제 동작**을 포함해 주세요.
- 가능하면 DoLT 버전, Python 버전, OS 정보를 함께 알려주세요.

### Feature Request / 기능 제안

- Issue를 생성하고 `enhancement` 라벨을 달아주세요.
- 어떤 문제를 해결하려는지, 기대하는 동작이 무엇인지 설명해 주세요.

### Code Contribution / 코드 기여

1. Issue를 확인하거나 새로 생성합니다.
2. 저장소를 Fork합니다.
3. 브랜치를 생성합니다.
   - 기능: `feat/기능명` (예: `feat/csv-parser`)
   - 버그 수정: `fix/버그명` (예: `fix/pdf-encoding`)
   - 문서: `docs/내용` (예: `docs/readme-update`)
4. 코드를 작성하고 테스트를 추가합니다.
5. 린트와 타입 체크를 통과하는지 확인합니다.
6. Pull Request를 생성합니다.

---

## Development Guide

### 테스트

```bash
# 전체 테스트
pytest

# 특정 모듈
pytest tests/unit/test_parsing.py

# 커버리지
pytest --cov=dolt --cov-report=html
```

새 기능을 추가할 때는 반드시 테스트를 함께 작성해 주세요.

### 린트 & 타입 체크

```bash
ruff check src/
ruff format src/
mypy src/
```

### 커밋 메시지

```
<type>: <description>

예시:
feat: add CSV parser
fix: handle empty PDF pages
docs: update README installation guide
test: add chunking edge case tests
refactor: simplify token chunker logic
```

---

## Code Style

| 항목 | 기준 |
|------|------|
| Linter | ruff |
| Type Checker | mypy (strict) |
| Line Length | 100 |
| Python | >= 3.10 |
| Type Hints | 필수 |
| Docstring | 공개 API에 필수 |

---

## Plugin Contribution

새로운 Parser, Embedding Provider, Exporter를 만들었다면:

**방법 1: 별도 패키지로 배포**

`pyproject.toml`에 entry_point를 등록하면 DoLT가 자동으로 인식합니다.

```toml
[project.entry-points."dolt.parsers"]
my_parser = "my_package:MyParser"
```

**방법 2: Core에 직접 기여**

1. 해당 모듈 디렉토리에 파일을 추가합니다.
2. 테스트를 작성합니다.
3. `__init__.py`에 export를 추가합니다.
4. PR을 생성합니다.

---

## Code of Conduct

이 프로젝트는 [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md)를 따릅니다.
모든 참여자는 이를 준수해야 합니다.
