"""DoLT 예외 클래스 계층."""

from __future__ import annotations


class DoltError(Exception):
    """DoLT 최상위 예외."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ── Ingestion ─────────────────────────────────────────────

class IngestionError(DoltError):
    """수집 단계 에러."""


class FileNotFoundError(IngestionError):
    """ING-ERR-01: 파일 없음."""

    def __init__(self, path: str) -> None:
        super().__init__("ING-ERR-01", f"파일을 찾을 수 없습니다: {path}")


class UnsupportedFormatError(IngestionError):
    """ING-ERR-02: 지원하지 않는 포맷."""

    def __init__(self, ext: str) -> None:
        super().__init__("ING-ERR-02", f"지원하지 않는 파일 포맷입니다: {ext}")


class URLFetchError(IngestionError):
    """ING-ERR-03: URL 연결 실패."""

    def __init__(self, url: str, reason: str = "") -> None:
        msg = f"URL 수집 실패: {url}"
        if reason:
            msg += f" ({reason})"
        super().__init__("ING-ERR-03", msg)


class FileTooLargeError(IngestionError):
    """ING-ERR-04: 파일 크기 초과."""

    def __init__(self, path: str, size_mb: float) -> None:
        super().__init__("ING-ERR-04", f"파일 크기 초과 ({size_mb:.1f}MB): {path}")


# ── Parsing ───────────────────────────────────────────────

class ParseError(DoltError):
    """파싱 단계 에러."""


class CorruptedFileError(ParseError):
    """PAR-ERR-01: 손상된 파일."""

    def __init__(self, path: str, reason: str = "") -> None:
        msg = f"손상된 파일입니다: {path}"
        if reason:
            msg += f" ({reason})"
        super().__init__("PAR-ERR-01", msg)


class EncodingError(ParseError):
    """PAR-ERR-02: 인코딩 오류."""

    def __init__(self, path: str) -> None:
        super().__init__("PAR-ERR-02", f"인코딩을 감지할 수 없습니다: {path}")


# ── Chunking ──────────────────────────────────────────────

class ChunkError(DoltError):
    """청킹 단계 에러."""


class InvalidConfigError(ChunkError):
    """CHK-ERR-01: 잘못된 설정."""

    def __init__(self, detail: str) -> None:
        super().__init__("CHK-ERR-01", f"잘못된 청킹 설정: {detail}")


# ── Embedding ─────────────────────────────────────────────

class EmbeddingError(DoltError):
    """임베딩 단계 에러."""


class APIKeyMissingError(EmbeddingError):
    """EMB-ERR-01: API 키 미설정."""

    def __init__(self, provider: str) -> None:
        super().__init__("EMB-ERR-01", f"{provider} API 키가 설정되지 않았습니다")


class RateLimitError(EmbeddingError):
    """EMB-ERR-02: Rate limit 초과."""

    def __init__(self, provider: str) -> None:
        super().__init__("EMB-ERR-02", f"{provider} API rate limit 초과")


class ModelNotFoundError(EmbeddingError):
    """EMB-ERR-03: 모델 없음."""

    def __init__(self, model: str) -> None:
        super().__init__("EMB-ERR-03", f"임베딩 모델을 찾을 수 없습니다: {model}")


# ── Export ────────────────────────────────────────────────

class ExportError(DoltError):
    """내보내기 단계 에러."""


class ConnectionError(ExportError):
    """EXP-ERR-01: 연결 실패."""

    def __init__(self, target: str, reason: str = "") -> None:
        msg = f"연결 실패: {target}"
        if reason:
            msg += f" ({reason})"
        super().__init__("EXP-ERR-01", msg)


class CollectionNotFoundError(ExportError):
    """EXP-ERR-02: 컬렉션 없음."""

    def __init__(self, name: str) -> None:
        super().__init__("EXP-ERR-02", f"컬렉션을 찾을 수 없습니다: {name}")
