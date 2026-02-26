"""Hybrid Chunker — Structure + Token 결합. 기본값."""

from __future__ import annotations

from dolt.chunking.base import BaseChunker
from dolt.chunking.structure_chunker import StructureChunker
from dolt.models.chunk import Chunk, ChunkType
from dolt.models.document import StructuredDocument
from dolt.utils.tokens import count_tokens

MIN_TOKENS = 100  # 이 미만의 텍스트 청크는 인접 청크와 병합


class HybridChunker(BaseChunker):
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        # 1차: Structure Chunker로 섹션 기반 분할
        structure_chunker = StructureChunker(self.config)
        chunks = structure_chunker.chunk(doc)

        # 2차: 작은 텍스트 청크 병합
        chunks = _merge_small_chunks(
            chunks, MIN_TOKENS, self.config.max_tokens, self.config.tokenizer
        )

        # chunk_index 재정렬
        for i, c in enumerate(chunks):
            c.chunk_index = i

        return chunks


def _merge_small_chunks(
    chunks: list[Chunk],
    min_tokens: int,
    max_tokens: int,
    tokenizer: str,
) -> list[Chunk]:
    """min_tokens 미만의 인접 텍스트 청크를 병합한다."""
    if not chunks:
        return chunks

    result: list[Chunk] = []
    buffer: Chunk | None = None

    for chunk in chunks:
        # 표/코드 청크는 병합하지 않음
        if chunk.chunk_type != ChunkType.TEXT:
            if buffer:
                result.append(buffer)
                buffer = None
            result.append(chunk)
            continue

        if buffer is None:
            buffer = chunk
            continue

        # 현재 buffer가 min_tokens 미만이면 병합 시도
        if buffer.token_count < min_tokens:
            merged_content = buffer.content + "\n\n" + chunk.content
            merged_tokens = count_tokens(merged_content, tokenizer)

            if merged_tokens <= max_tokens:
                buffer = buffer.model_copy(
                    update={
                        "content": merged_content,
                        "token_count": merged_tokens,
                        "end_offset": chunk.end_offset,
                    }
                )
                continue

        # 병합 불가: buffer를 결과에 추가하고 새 buffer 시작
        result.append(buffer)
        buffer = chunk

    if buffer:
        result.append(buffer)

    return result
