"""청크 단위 단어/문자 수 계산."""

from __future__ import annotations

from dolt.metadata.base_plugin import MetadataPlugin
from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument


class WordCountPlugin(MetadataPlugin):
    @property
    def name(self) -> str:
        return "word_count"

    def enrich(self, chunk: Chunk, doc: StructuredDocument) -> dict:
        words = chunk.content.split()
        word_count = len(words)
        char_count = len(chunk.content)
        avg_word_length = (
            sum(len(w) for w in words) / word_count if word_count > 0 else 0.0
        )
        return {
            "word_count": word_count,
            "char_count": char_count,
            "avg_word_length": round(avg_word_length, 2),
        }
