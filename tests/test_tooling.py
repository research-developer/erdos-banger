"""Verify development tooling is correctly configured."""

import tomllib
from pathlib import Path

import pytest
import typer

from erdos import cli


def test_pyproject_has_required_sections() -> None:
    """pyproject.toml should include required tool sections."""
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert "project" in data
    assert "dependency-groups" in data
    assert "tool" in data
    assert "ruff" in data["tool"]
    assert "mypy" in data["tool"]


def test_cli_is_importable() -> None:
    """The CLI module should be importable."""
    assert hasattr(cli, "app")


def test_version_callback_covers_branches() -> None:
    """Ensure version callback behavior stays stable and covered."""
    cli.version_callback(False)
    with pytest.raises(typer.Exit):
        cli.version_callback(True)


def test_py_typed_exists() -> None:
    """PEP 561 py.typed marker should exist."""
    py_typed = Path("src/erdos/py.typed")
    assert py_typed.exists(), "Missing py.typed marker for PEP 561"
