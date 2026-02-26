"""DoLT 로깅 설정."""

from __future__ import annotations

import logging
import re
import sys

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# API 키 마스킹 패턴
_SECRET_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9]{3})[a-zA-Z0-9]+([a-zA-Z0-9]{4})"
    r"|(key-[a-zA-Z0-9]{3})[a-zA-Z0-9]+([a-zA-Z0-9]{4})"
)


class _MaskingFormatter(logging.Formatter):
    """민감 정보를 마스킹하는 Formatter."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return _SECRET_PATTERN.sub(r"\1***\2", message)


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """DoLT 로깅을 설정한다."""
    root = logging.getLogger("dolt")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    formatter = _MaskingFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # stdout 핸들러
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    # 파일 핸들러
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거를 반환한다."""
    return logging.getLogger(f"dolt.{name}")
