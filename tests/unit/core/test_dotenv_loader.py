"""Tests for the Python .env loader used by the CLI."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from erdos.core.dotenv_loader import load_dotenv_file


def test_missing_file_is_noop(tmp_path: Path) -> None:
    loaded = load_dotenv_file(tmp_path / ".env")
    assert loaded == {}


def test_basic_key_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MY_VAR=hello\n", encoding="utf-8")
    loaded = load_dotenv_file(env_path)
    assert loaded == {"MY_VAR": "hello"}


def test_comments_and_whitespace(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        dedent(
            """
            # comment
              FOO = bar   # trailing comment

            EMPTY=
            QUOTED="a#b#c"
            export EXPORTED=ok
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = load_dotenv_file(env_path)
    assert loaded["FOO"] == "bar"
    assert loaded["EMPTY"] == ""
    assert loaded["QUOTED"] == "a#b#c"
    assert loaded["EXPORTED"] == "ok"


def test_invalid_keys_ignored(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("BAD KEY=value\nGOOD_KEY=value\n", encoding="utf-8")
    loaded = load_dotenv_file(env_path)
    assert "BAD" not in loaded
    assert loaded["GOOD_KEY"] == "value"
