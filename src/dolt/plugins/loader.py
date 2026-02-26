"""플러그인 동적 로딩 — entry_points 기반."""

from __future__ import annotations

from importlib.metadata import entry_points

from dolt.utils.logging import get_logger

logger = get_logger("plugins")


def discover_plugins(group: str) -> list[type]:
    """entry_points에서 지정 그룹의 플러그인을 발견한다."""
    eps = entry_points(group=group)

    plugins: list[type] = []
    for ep in eps:
        try:
            cls = ep.load()
            plugins.append(cls)
            logger.debug("플러그인 발견: %s.%s", group, ep.name)
        except Exception as e:
            logger.warning("플러그인 로딩 실패: %s.%s — %s", group, ep.name, e)

    return plugins
