"""MetadataEnricher — 등록된 플러그인을 순서대로 실행."""

from __future__ import annotations

from dolt.metadata.base_plugin import MetadataPlugin
from dolt.models.chunk import Chunk
from dolt.models.document import StructuredDocument
from dolt.utils.logging import get_logger

logger = get_logger("metadata")


class MetadataEnricher:
    """청크에 메타데이터를 부여하는 오케스트레이터."""

    def __init__(self, plugins: list[MetadataPlugin] | None = None) -> None:
        if plugins is None:
            plugins = _default_plugins()
        self._plugins = list(plugins)

    def add_plugin(self, plugin: MetadataPlugin) -> None:
        """플러그인을 추가 등록한다."""
        self._plugins.append(plugin)

    def enrich(self, chunks: list[Chunk], doc: StructuredDocument) -> list[Chunk]:
        """모든 청크에 대해 등록된 플러그인을 순차 실행한다."""
        result: list[Chunk] = []
        for chunk in chunks:
            new_meta = dict(chunk.metadata)
            for plugin in self._plugins:
                try:
                    extra = plugin.enrich(chunk, doc)
                    new_meta.update(extra)
                except Exception as e:
                    logger.warning(
                        "플러그인 %s 실행 실패 (chunk=%s): %s",
                        plugin.name, chunk.chunk_id, e,
                    )
            result.append(chunk.model_copy(update={"metadata": new_meta}))
        return result


def _default_plugins() -> list[MetadataPlugin]:
    from dolt.metadata.builtin.basic_meta import BasicMetaPlugin
    from dolt.metadata.builtin.word_count import WordCountPlugin
    from dolt.metadata.builtin.section_path import SectionPathPlugin

    return [BasicMetaPlugin(), WordCountPlugin(), SectionPathPlugin()]
