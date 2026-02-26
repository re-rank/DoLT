"""문서 수준 기본 메타데이터를 청크에 전파."""

from __future__ import annotations

from pathlib import Path

from dolt.metadata.base_plugin import MetadataPlugin
from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument


class BasicMetaPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "basic_meta"

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        title = doc.metadata.get("title") or Path(doc.source).stem
        author = doc.metadata.get("author", "unknown")
        return {
            "title": title,
            "author": author,
            "source": doc.source,
            "file_type": Path(doc.source).suffix.lower(),
            "total_pages": doc.total_pages,
            "doc_id": doc.doc_id,
        }
