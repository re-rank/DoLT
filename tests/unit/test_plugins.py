"""Plugin loader 테스트."""

from __future__ import annotations

from dolt.plugins.loader import discover_plugins


def test_discover_parsers():
    """dolt.parsers entry_points에서 파서를 발견한다."""
    plugins = discover_plugins("dolt.parsers")
    # 패키지가 editable install 되어 있으면 등록된 파서가 반환됨
    # 아니면 빈 리스트 (정상 동작)
    assert isinstance(plugins, list)


def test_discover_metadata_plugins():
    plugins = discover_plugins("dolt.metadata_plugins")
    assert isinstance(plugins, list)


def test_discover_unknown_group():
    """존재하지 않는 그룹은 빈 리스트를 반환한다."""
    plugins = discover_plugins("dolt.nonexistent_group")
    assert plugins == []
