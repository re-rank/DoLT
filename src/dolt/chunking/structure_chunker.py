"""Structure 기반 Chunker — 섹션 경계 기준 분할."""

from __future__ import annotations

import uuid

from dolt.chunking.base import BaseChunker
from dolt.chunking.token_chunker import chunk_text_by_tokens
from dolt.models.chunk import Chunk, ChunkType
from dolt.models.document import StructuredDocument
from dolt.utils.tokens import count_tokens


class StructureChunker(BaseChunker):
    def chunk(self, doc: StructuredDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        idx = 0

        # 섹션 기반 분할
        if doc.sections:
            for sec in doc.sections:
                content = f"{sec.title}\n{sec.content}".strip()
                if not content:
                    continue

                token_count = count_tokens(content, self.config.tokenizer)

                if token_count <= self.config.max_tokens:
                    # 섹션이 max_tokens 이내: 하나의 청크
                    chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc.doc_id,
                            content=content,
                            chunk_type=ChunkType.TEXT,
                            chunk_index=idx,
                            start_offset=sec.start_offset,
                            end_offset=sec.end_offset,
                            token_count=token_count,
                            metadata={"section_title": sec.title, "section_level": sec.level},
                        )
                    )
                    idx += 1
                else:
                    # 섹션이 max_tokens 초과: Token Chunker로 재분할
                    sub_chunks = chunk_text_by_tokens(
                        text=content,
                        doc_id=doc.doc_id,
                        max_tokens=self.config.max_tokens,
                        overlap_tokens=self.config.overlap_tokens,
                        tokenizer=self.config.tokenizer,
                        start_index=idx,
                    )
                    for sc in sub_chunks:
                        sc.metadata["section_title"] = sec.title
                        sc.metadata["section_level"] = sec.level
                    chunks.extend(sub_chunks)
                    idx += len(sub_chunks)
        else:
            # 섹션 없으면 Token Chunker로 폴백
            chunks = chunk_text_by_tokens(
                text=doc.raw_text,
                doc_id=doc.doc_id,
                max_tokens=self.config.max_tokens,
                overlap_tokens=self.config.overlap_tokens,
                tokenizer=self.config.tokenizer,
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
