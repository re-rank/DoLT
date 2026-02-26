"""Chunk 관련 데이터 모델."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    CODE = "code"


class Chunk(BaseModel):
    """Chunker의 출력 단위."""

    chunk_id: str = Field(description="UUID v4 형식 청크 고유 ID")
    doc_id: str = Field(description="소속 문서 ID")
    content: str = Field(description="청크 텍스트")
    chunk_type: ChunkType = Field(default=ChunkType.TEXT)
    chunk_index: int = Field(description="문서 내 청크 순번 (0-based)")
    start_offset: int = Field(default=0, description="원본 텍스트 내 시작 위치")
    end_offset: int = Field(default=0, description="원본 텍스트 내 종료 위치")
    token_count: int = Field(default=0, description="토큰 수")
    metadata: dict = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    """임베딩 완료된 청크."""

    chunk_id: str
    doc_id: str
    content: str
    chunk_type: ChunkType = Field(default=ChunkType.TEXT)
    chunk_index: int = Field(default=0)
    token_count: int = Field(default=0)
    vector: list[float] = Field(description="임베딩 벡터")
    embedding_model: str = Field(description="사용된 임베딩 모델명")
    embedding_dim: int = Field(description="벡터 차원 수")
    metadata: dict = Field(default_factory=dict)
