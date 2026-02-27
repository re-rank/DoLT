"""플러그인 동적 로딩 — entry_points 기반."""

from __future__ import annotations

from importlib.metadata import entry_points

from dolt.utils.logging import get_logger

logger = get_logger("plugins")


def discover_plugins(group: str) -> list[type]:
    """entry_points에서 지정 그룹의 플러그인을 발견한다."""
    return [cls for _, cls in discover_plugins_with_names(group)]


def discover_plugins_with_names(group: str) -> list[tuple[str, type]]:
    """(entry_point_name, class) 튜플 리스트를 반환한다."""
    eps = entry_points(group=group)

    plugins: list[tuple[str, type]] = []
    for ep in eps:
        try:
            cls = ep.load()
            plugins.append((ep.name, cls))
            logger.debug("플러그인 발견: %s.%s", group, ep.name)
        except Exception as e:
            logger.warning("플러그인 로딩 실패: %s.%s — %s", group, ep.name, e)

    return plugins


def discover_parsers() -> list[tuple[str, type]]:
    """설치된 파서 플러그인 목록을 반환한다."""
    return discover_plugins_with_names("dolt.parsers")


def discover_metadata_plugins() -> list[tuple[str, type]]:
    """설치된 메타데이터 플러그인 목록을 반환한다."""
    return discover_plugins_with_names("dolt.metadata_plugins")


def discover_embedding_providers() -> list[tuple[str, type]]:
    """설치된 임베딩 프로바이더 목록을 반환한다."""
    return discover_plugins_with_names("dolt.embedding_providers")


def discover_exporters() -> list[tuple[str, type]]:
    """설치된 익스포터 목록을 반환한다."""
    return discover_plugins_with_names("dolt.exporters")
