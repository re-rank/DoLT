"""공통 테스트 픽스처."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from dolt.models.config import DoltConfig
from dolt.storage.local_store import LocalStore


@pytest.fixture
def tmp_dir():
    """임시 디렉토리를 생성하고 테스트 후 삭제한다."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def store(tmp_dir: Path) -> LocalStore:
    """테스트용 LocalStore."""
    return LocalStore(str(tmp_dir / ".dolt"))


@pytest.fixture
def config(tmp_dir: Path) -> DoltConfig:
    """테스트용 DoltConfig."""
    return DoltConfig(storage={"path": str(tmp_dir / ".dolt")})


@pytest.fixture
def sample_md(tmp_dir: Path) -> Path:
    """테스트용 Markdown 파일."""
    content = """# DoLT 테스트 문서

## 1장 소개

이것은 테스트 문서입니다.
DoLT는 Document-native ELT Engine입니다.

## 2장 기능

### 2.1 파싱

다양한 포맷을 지원합니다.

### 2.2 청킹

| 모드 | 설명 |
| --- | --- |
| token | 토큰 기반 |
| structure | 구조 기반 |
| hybrid | 하이브리드 |

## 3장 코드 예시

```python
def hello():
    print("Hello, DoLT!")
```

끝.
"""
    path = tmp_dir / "sample.md"
    path.write_text(content, encoding="utf-8")
    return path
