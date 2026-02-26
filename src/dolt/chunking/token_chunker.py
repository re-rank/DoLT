"""Token 기반 Chunker — 고정 토큰 수 슬라이딩 윈도우 분할."""

from __future__ import annotations

import uuid

from dolt.chunking.base import BaseChunker
from dolt.models.chunk import Chunk, ChunkType
from dolt.models.document import StructuredDocument
from dolt.utils.tokens import detokenize, tokenize


class TokenChunker(BaseChunker):
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        return chunk_text_by_tokens(
            text=doc.raw_text,
            doc_id=doc.doc_id,
            max_tokens=self.config.max_tokens,
            overlap_tokens=self.config.overlap_tokens,
            tokenizer=self.config.tokenizer,
        )


def chunk_text_by_tokens(
    text: str,
    doc_id: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    tokenizer: str = "cl100k_base",
    start_index: int = 0,
    chunk_type: ChunkType = ChunkType.TEXT,
) -> list[Chunk]:
    """텍스트를 토큰 기반으로 분할한다. 문장 경계 보정 포함."""
    if not text.strip():
        return []

    tokens = tokenize(text, tokenizer)
    total = len(tokens)
    if total == 0:
        return []

    chunks: list[Chunk] = []
    pos = 0
    idx = start_index

    while pos < total:
        end = min(pos + max_tokens, total)
        chunk_tokens = tokens[pos:end]
        chunk_text = detokenize(chunk_tokens, tokenizer)

        # 문장 경계 보정: 마지막 마침표/줄바꿈 위치로 조정
        if end < total:
            adjusted = _snap_to_sentence(chunk_text)
            if adjusted and len(adjusted) > len(chunk_text) * 0.5:
                chunk_text = adjusted
                # 보정된 텍스트로 토큰 수 재계산
                chunk_tokens_len = len(tokenize(chunk_text, tokenizer))
            else:
                chunk_tokens_len = len(chunk_tokens)
        else:
            chunk_tokens_len = len(chunk_tokens)

        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=chunk_text.strip(),
                chunk_type=chunk_type,
                chunk_index=idx,
                token_count=chunk_tokens_len,
            )
        )

        # 다음 시작점: overlap 적용
        step = max(chunk_tokens_len - overlap_tokens, 1)
        pos += step
        idx += 1

    return chunks


def _snap_to_sentence(text: str) -> str | None:
    """마지막 문장 경계(마침표, 줄바꿈)에서 자른다."""
    for sep in ["\n\n", "\n", ". ", "。", "? ", "! "]:
        last = text.rfind(sep)
        if last > len(text) * 0.5:
            return text[: last + len(sep)]
    return None
