"""Structure 기반 Chunker — 섹션 + 줄 경계 기준 분할."""

from __future__ import annotations

import uuid

from dolt.chunking.base import BaseChunker
from dolt.chunking.token_chunker import chunk_text_by_tokens
from dolt.models.chunk import Chunk, ChunkType
from dolt.models.document import StructuredDocument
from dolt.models.section import Section
from dolt.utils.tokens import count_tokens


class StructureChunker(BaseChunker):
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        idx = 0

        if doc.sections:
            # 첫 섹션 이전 텍스트 (프리앰블)
            first_offset = doc.sections[0].start_offset
            if first_offset > 0:
                preamble = doc.raw_text[:first_offset].strip()
                if preamble:
                    pre = _chunk_text_by_lines(
                        preamble, doc.doc_id,
                        self.config.max_tokens, self.config.tokenizer, idx,
                    )
                    chunks.extend(pre)
                    idx += len(pre)

            for sec in doc.sections:
                sec_chunks = _chunk_section(
                    sec, doc.doc_id,
                    self.config.max_tokens, self.config.overlap_tokens,
                    self.config.tokenizer, idx,
                )
                chunks.extend(sec_chunks)
                idx += len(sec_chunks)
        else:
            # 섹션 없으면 줄 기반 분할
            chunks = _chunk_text_by_lines(
                doc.raw_text, doc.doc_id,
                self.config.max_tokens, self.config.tokenizer, 0,
            )
            idx = len(chunks)

        # 표 → 독립 청크
        for table in doc.tables:
            if table.markdown.strip():
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc.doc_id,
                        content=table.markdown,
                        chunk_type=ChunkType.TABLE,
                        chunk_index=idx,
                        token_count=count_tokens(table.markdown, self.config.tokenizer),
                        metadata={"table_id": table.table_id},
                    )
                )
                idx += 1

        # 코드블록 → 독립 청크
        for code in doc.code_blocks:
            if code.content.strip():
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc.doc_id,
                        content=code.content,
                        chunk_type=ChunkType.CODE,
                        chunk_index=idx,
                        token_count=count_tokens(code.content, self.config.tokenizer),
                        metadata={"language": code.language, "code_id": code.code_id},
                    )
                )
                idx += 1

        return chunks


# ── 내부 함수 ──────────────────────────────────────────


def _chunk_section(
    sec: Section,
    doc_id: str,
    max_tokens: int,
    overlap_tokens: int,
    tokenizer: str,
    start_index: int,
) -> list[Chunk]:
    """섹션을 줄 경계 기준으로 분할한다.

    - 첫 청크: "제목\\n내용"
    - 연속 청크: "[제목]\\n내용" (문맥 유지용 프리픽스)
    """
    full_text = f"{sec.title}\n{sec.content}".strip()
    if not full_text:
        return []

    full_tokens = count_tokens(full_text, tokenizer)
    meta = {"section_title": sec.title, "section_level": sec.level}

    # 섹션이 max_tokens 이내: 하나의 청크
    if full_tokens <= max_tokens:
        return [
            Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=full_text,
                chunk_type=ChunkType.TEXT,
                chunk_index=start_index,
                start_offset=sec.start_offset,
                end_offset=sec.end_offset,
                token_count=full_tokens,
                metadata=meta,
            )
        ]

    # 큰 섹션 → 줄 단위 축적, 제목 프리픽스 포함
    first_prefix = f"{sec.title}\n"
    cont_prefix = f"[{sec.title}]\n"
    first_prefix_tok = count_tokens(first_prefix, tokenizer)
    cont_prefix_tok = count_tokens(cont_prefix, tokenizer)

    lines = sec.content.split("\n")
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    idx = start_index
    is_first = True

    for line in lines:
        line_tok = count_tokens(line, tokenizer) + 1  # +1 for \n

        prefix_tok = first_prefix_tok if is_first else cont_prefix_tok
        avail = max_tokens - prefix_tok

        # 단일 줄이 avail 초과 → TokenChunker 폴백
        if line_tok > avail:
            if buf:
                _flush(chunks, buf, doc_id, sec, meta, is_first, idx, tokenizer)
                idx += 1
                is_first = False
                buf, buf_tokens = [], 0

            prefix = first_prefix if is_first else cont_prefix
            is_first = False
            sub = chunk_text_by_tokens(
                text=prefix + line, doc_id=doc_id,
                max_tokens=max_tokens, overlap_tokens=overlap_tokens,
                tokenizer=tokenizer, start_index=idx,
            )
            for sc in sub:
                sc.metadata.update(meta)
            chunks.extend(sub)
            idx += len(sub)
            continue

        # 버퍼 용량 초과 → 현재 버퍼를 청크로 저장
        if buf_tokens + line_tok > avail and buf:
            _flush(chunks, buf, doc_id, sec, meta, is_first, idx, tokenizer)
            idx += 1
            is_first = False
            buf, buf_tokens = [], 0

        buf.append(line)
        buf_tokens += line_tok

    if buf:
        _flush(chunks, buf, doc_id, sec, meta, is_first, idx, tokenizer)

    return chunks


def _flush(
    chunks: list[Chunk],
    lines: list[str],
    doc_id: str,
    sec: Section,
    meta: dict,
    is_first: bool,
    idx: int,
    tokenizer: str,
) -> None:
    """축적된 라인을 하나의 청크로 생성."""
    body = "\n".join(lines)
    if is_first:
        text = f"{sec.title}\n{body}"
    else:
        text = f"[{sec.title}]\n{body}"

    chunks.append(
        Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            content=text.strip(),
            chunk_type=ChunkType.TEXT,
            chunk_index=idx,
            token_count=count_tokens(text, tokenizer),
            metadata=dict(meta),
        )
    )


def _chunk_text_by_lines(
    text: str,
    doc_id: str,
    max_tokens: int,
    tokenizer: str,
    start_index: int = 0,
) -> list[Chunk]:
    """섹션이 없는 텍스트를 줄 단위로 청킹한다."""
    if not text.strip():
        return []

    lines = text.split("\n")
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    idx = start_index

    for line in lines:
        line_tok = count_tokens(line, tokenizer) + 1

        if buf_tokens + line_tok > max_tokens and buf:
            chunk_text = "\n".join(buf)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text.strip(),
                    chunk_type=ChunkType.TEXT,
                    chunk_index=idx,
                    token_count=count_tokens(chunk_text, tokenizer),
                )
            )
            idx += 1
            buf, buf_tokens = [], 0

        buf.append(line)
        buf_tokens += line_tok

    if buf:
        chunk_text = "\n".join(buf)
        if chunk_text.strip():
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text.strip(),
                    chunk_type=ChunkType.TEXT,
                    chunk_index=idx,
                    token_count=count_tokens(chunk_text, tokenizer),
                )
            )

    return chunks
