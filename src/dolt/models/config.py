"""DoLT 설정 모델."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ChunkMode(str, Enum):
    TOKEN = "token"
    STRUCTURE = "structure"
    HYBRID = "hybrid"


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    COHERE = "cohere"
    LOCAL = "local"


class ExportTarget(str, Enum):
    QDRANT = "qdrant"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    JSON = "json"
    POSTGRES = "postgres"


class ParsingConfig(BaseModel):
    encoding: str = Field(default="auto")


class ChunkConfig(BaseModel):
    mode: ChunkMode = Field(default=ChunkMode.HYBRID)
    max_tokens: int = Field(default=512, ge=100, le=2000)
    overlap_tokens: int = Field(default=50, ge=0, le=500)
    tokenizer: str = Field(default="cl100k_base")


class EmbeddingConfig(BaseModel):
    provider: EmbeddingProvider = Field(default=EmbeddingProvider.OPENAI)
    model: str | None = Field(default=None, description="None이면 provider별 기본값 사용")
    batch_size: int = Field(default=100, ge=1, le=500)
    max_retries: int = Field(default=3, ge=0, le=10)


class QdrantConfig(BaseModel):
    url: str = Field(default="localhost")
    port: int = Field(default=6333)
    collection: str = Field(default="dolt_documents")
    api_key: str | None = Field(default=None)


class PineconeConfig(BaseModel):
    index: str = Field(default="dolt-documents")
    namespace: str = Field(default="")


class JsonExportConfig(BaseModel):
    output: str = Field(default=".dolt/export.json")
    include_vectors: bool = Field(default=True)


class PostgresConfig(BaseModel):
    table: str = Field(default="dolt_chunks")
    use_pgvector: bool = Field(default=True)


class ExportConfig(BaseModel):
    model_config = {"protected_namespaces": (), "populate_by_name": True}

    target: ExportTarget = Field(default=ExportTarget.JSON)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    pinecone: PineconeConfig = Field(default_factory=PineconeConfig)
    json_export: JsonExportConfig = Field(default_factory=JsonExportConfig, alias="json")
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)


class MetadataConfig(BaseModel):
    plugins: list[str] = Field(
        default_factory=lambda: ["basic_meta", "word_count", "section_path"]
    )


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    file: str | None = Field(default=None)


class StorageConfig(BaseModel):
    path: str = Field(default=".dolt")


class DoltConfig(BaseModel):
    """DoLT 전체 설정."""

    parsing: ParsingConfig = Field(default_factory=ParsingConfig)
    chunking: ChunkConfig = Field(default_factory=ChunkConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
        cli_overrides: dict | None = None,
    ) -> DoltConfig:
        """설정 로딩: 기본값 → YAML → 환경변수 → CLI 오버라이드."""
        data: dict = {}

        # YAML 파일 로드
        if config_path:
            path = Path(config_path)
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

        # 기본 경로 시도
        if not data:
            default_path = Path("dolt.yaml")
            if default_path.exists():
                with open(default_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

        # CLI 오버라이드 병합
        if cli_overrides:
            _deep_merge(data, cli_overrides)

        return cls.model_validate(data)


def _deep_merge(base: dict, override: dict) -> dict:
    """override의 값을 base에 재귀적으로 병합."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
