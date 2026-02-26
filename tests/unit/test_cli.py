"""CLI 모듈 테스트."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dolt.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_dir: Path, monkeypatch):
    """각 테스트를 빈 임시 디렉토리에서 실행하여 .dolt/ 격리."""
    monkeypatch.chdir(tmp_dir)


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "DoLT v" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Document-native ELT Engine" in result.output


def test_ingest_command(sample_md: Path):
    result = runner.invoke(app, ["ingest", str(sample_md)])
    assert result.exit_code == 0


def test_ingest_nonexistent():
    result = runner.invoke(app, ["ingest", "/nonexistent/path/file.pdf"])
    assert result.exit_code == 1


def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "DoLT Status" in result.output


def test_clean_without_options():
    result = runner.invoke(app, ["clean"])
    assert result.exit_code == 0


def test_parse_no_documents():
    result = runner.invoke(app, ["parse"])
    assert result.exit_code == 0
    assert "파싱 완료: 0/0" in result.output


def test_chunk_no_documents():
    result = runner.invoke(app, ["chunk"])
    assert result.exit_code == 0
    assert "청킹 완료: 0 chunks" in result.output
