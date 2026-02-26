"""토큰 카운팅 유틸리티."""

from __future__ import annotations

import tiktoken


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """텍스트의 토큰 수를 계산한다."""
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))


def tokenize(text: str, model: str = "cl100k_base") -> list[int]:
    """텍스트를 토큰 ID 리스트로 변환한다."""
    enc = tiktoken.get_encoding(model)
    return enc.encode(text)


def detokenize(tokens: list[int], model: str = "cl100k_base") -> str:
    """토큰 ID 리스트를 텍스트로 복원한다."""
    enc = tiktoken.get_encoding(model)
    return enc.decode(tokens)
