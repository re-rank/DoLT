"""SHA-256 해싱 유틸리티."""

from __future__ import annotations

import hashlib
from pathlib import Path

BUFFER_SIZE = 65536  # 64KB


def hash_file(file_path: str | Path) -> str:
    """파일의 SHA-256 해시를 계산한다."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def hash_bytes(data: bytes) -> str:
    """바이트 데이터의 SHA-256 해시를 계산한다."""
    return hashlib.sha256(data).hexdigest()
