"""Tests for the Python .env loader used by the CLI."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

from erdos.core.dotenv_loader import load_dotenv_file


def test_missing_file_is_noop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MY_VAR", raising=False)
    loaded = load_dotenv_file(tmp_path / ".env")
    assert loaded == {}
    assert "MY_VAR" not in os.environ


def test_basic_key_value(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MY_VAR=hello\n", encoding="utf-8")
    monkeypatch.delenv("MY_VAR", raising=False)
    loaded = load_dotenv_file(env_path)
    assert loaded == {"MY_VAR": "hello"}
    assert os.environ["MY_VAR"] == "hello"


def test_comments_and_whitespace(tmp_path: Path, monkeypatch) -> None:
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
    for key in ("FOO", "EMPTY", "QUOTED", "EXPORTED"):
        monkeypatch.delenv(key, raising=False)

    loaded = load_dotenv_file(env_path)
    assert loaded["FOO"] == "bar"
    assert loaded["EMPTY"] == ""
    assert loaded["QUOTED"] == "a#b#c"
    assert loaded["EXPORTED"] == "ok"


def test_invalid_keys_ignored(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("BAD KEY=value\nGOOD_KEY=value\n", encoding="utf-8")
    monkeypatch.delenv("BAD", raising=False)
    monkeypatch.delenv("GOOD_KEY", raising=False)
    loaded = load_dotenv_file(env_path)
    assert "BAD" not in loaded
    assert loaded["GOOD_KEY"] == "value"


def test_does_not_override_existing(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MY_VAR=from_file\n", encoding="utf-8")
    monkeypatch.setenv("MY_VAR", "already_set")
    loaded = load_dotenv_file(env_path)
    assert loaded == {}
    assert os.environ["MY_VAR"] == "already_set"


def test_override_true_overwrites_existing(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MY_VAR=from_file\n", encoding="utf-8")
    monkeypatch.setenv("MY_VAR", "already_set")
    loaded = load_dotenv_file(env_path, override=True)
    assert loaded == {"MY_VAR": "from_file"}
    assert os.environ["MY_VAR"] == "from_file"
