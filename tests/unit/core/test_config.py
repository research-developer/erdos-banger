"""Unit tests for centralized configuration (AppConfig).

Tests verify that:
1. AppConfig.from_env() correctly reads environment variables.
2. AppConfig can be instantiated with explicit values (no env dependency).
3. AppContext.from_config() allows tests to bypass env reads entirely.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from erdos.core.config import (
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAILTO,
    DEFAULT_RUN_LOG_PATH,
    AppConfig,
    initialize_environment,
)
from erdos.core.context import AppContext


class TestAppConfigDefaults:
    """Test AppConfig default values."""

    def test_default_values(self) -> None:
        """AppConfig with no args uses sensible defaults."""
        config = AppConfig()

        assert config.data_path is None
        assert config.index_path is None
        assert config.run_log_path == DEFAULT_RUN_LOG_PATH
        assert config.repo_root is None
        assert config.mailto == DEFAULT_MAILTO
        assert config.llm_command == ""
        assert config.aristotle_api_key == ""
        assert config.aristotle_command == "aristotle"
        assert config.openalex_api_key == ""
        assert config.http_timeout == DEFAULT_HTTP_TIMEOUT

    def test_explicit_values_override_defaults(self) -> None:
        """Explicit constructor values override defaults."""
        config = AppConfig(
            data_path=Path("/custom/data"),
            index_path=Path("/custom/index.sqlite"),
            run_log_path=Path("/custom/logs.jsonl"),
            repo_root=Path("/custom/repo"),
            mailto="test@example.com",
            llm_command="llm run",
            aristotle_api_key="test-key",
            aristotle_command="/usr/bin/aristotle",
            openalex_api_key="openalex-key",
            http_timeout=60.0,
        )

        assert config.data_path == Path("/custom/data")
        assert config.index_path == Path("/custom/index.sqlite")
        assert config.run_log_path == Path("/custom/logs.jsonl")
        assert config.repo_root == Path("/custom/repo")
        assert config.mailto == "test@example.com"
        assert config.llm_command == "llm run"
        assert config.aristotle_api_key == "test-key"
        assert config.aristotle_command == "/usr/bin/aristotle"
        assert config.openalex_api_key == "openalex-key"
        assert config.http_timeout == 60.0

    def test_frozen_immutability(self) -> None:
        """AppConfig is frozen (immutable)."""
        config = AppConfig()

        with pytest.raises(AttributeError):
            config.mailto = "changed@example.com"  # type: ignore[misc]


class TestAppConfigFromEnv:
    """Test AppConfig.from_env() environment variable reading."""

    def test_reads_all_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_env() reads all configured environment variables."""
        monkeypatch.setenv("ERDOS_DATA_PATH", "/env/data")
        monkeypatch.setenv("ERDOS_INDEX_PATH", "/env/index.sqlite")
        monkeypatch.setenv("ERDOS_RUN_LOG_PATH", "/env/logs.jsonl")
        monkeypatch.setenv("ERDOS_REPO_ROOT", "/env/repo")
        monkeypatch.setenv("ERDOS_MAILTO", "env@example.com")
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "env-llm")
        monkeypatch.setenv("ARISTOTLE_API_KEY", "env-aristotle-key")
        monkeypatch.setenv("ERDOS_ARISTOTLE_COMMAND", "/env/aristotle")
        monkeypatch.setenv("OPENALEX_API_KEY", "env-openalex-key")

        config = AppConfig.from_env()

        assert config.data_path == Path("/env/data")
        assert config.index_path == Path("/env/index.sqlite")
        assert config.run_log_path == Path("/env/logs.jsonl")
        assert config.repo_root == Path("/env/repo")
        assert config.mailto == "env@example.com"
        assert config.llm_command == "env-llm"
        assert config.aristotle_api_key == "env-aristotle-key"
        assert config.aristotle_command == "/env/aristotle"
        assert config.openalex_api_key == "env-openalex-key"

    def test_defaults_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_env() uses defaults when env vars are not set."""
        # Clear all relevant env vars
        for var in [
            "ERDOS_DATA_PATH",
            "ERDOS_INDEX_PATH",
            "ERDOS_RUN_LOG_PATH",
            "ERDOS_REPO_ROOT",
            "ERDOS_MAILTO",
            "OPENALEX_EMAIL",
            "ERDOS_LLM_COMMAND",
            "ARISTOTLE_API_KEY",
            "ERDOS_ARISTOTLE_COMMAND",
            "OPENALEX_API_KEY",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = AppConfig.from_env()

        assert config.data_path is None
        assert config.index_path is None
        assert config.run_log_path == DEFAULT_RUN_LOG_PATH
        assert config.repo_root is None
        assert config.mailto == DEFAULT_MAILTO
        assert config.llm_command == ""
        assert config.aristotle_api_key == ""
        assert config.aristotle_command == "aristotle"
        assert config.openalex_api_key == ""

    def test_strips_whitespace_from_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API keys have whitespace stripped."""
        monkeypatch.setenv("ARISTOTLE_API_KEY", "  key-with-spaces  ")
        monkeypatch.setenv("ERDOS_ARISTOTLE_COMMAND", "  /path/to/cmd  ")

        config = AppConfig.from_env()

        assert config.aristotle_api_key == "key-with-spaces"
        assert config.aristotle_command == "/path/to/cmd"

    def test_openalex_email_alias_with_appconfig(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppConfig.from_env() prefers ERDOS_MAILTO over OPENALEX_EMAIL."""
        monkeypatch.setenv("ERDOS_MAILTO", "primary@example.com")
        monkeypatch.setenv("OPENALEX_EMAIL", "alias@example.com")

        config = AppConfig.from_env()
        assert config.mailto == "primary@example.com"

        monkeypatch.delenv("ERDOS_MAILTO", raising=False)
        config = AppConfig.from_env()
        assert config.mailto == "alias@example.com"

    def test_mailto_env_values_are_stripped_and_blank_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Whitespace-only env values should not override alias/defaults."""
        monkeypatch.setenv("ERDOS_MAILTO", "   ")
        monkeypatch.setenv("OPENALEX_EMAIL", "  alias@example.com  ")

        config = AppConfig.from_env()
        assert config.mailto == "alias@example.com"

        monkeypatch.setenv("OPENALEX_EMAIL", "   ")
        config = AppConfig.from_env()
        assert config.mailto == DEFAULT_MAILTO

    def test_initialize_environment_loads_dotenv_when_enabled(
        self, tmp_path: Path
    ) -> None:
        """initialize_environment() loads `.env` when enabled."""
        (tmp_path / ".env").write_text(
            "ARISTOTLE_API_KEY=dotenv-key\n", encoding="utf-8"
        )

        env = {"ERDOS_LOAD_DOTENV": "1", "ERDOS_REPO_ROOT": str(tmp_path)}
        with patch.dict(os.environ, env, clear=True):
            initialize_environment()
            config = AppConfig.from_env()
            assert config.aristotle_api_key == "dotenv-key"

    def test_dotenv_does_not_override_non_empty_env_var(self, tmp_path: Path) -> None:
        """Non-empty env vars win over `.env` defaults."""
        (tmp_path / ".env").write_text(
            "ARISTOTLE_API_KEY=from-dotenv\n", encoding="utf-8"
        )

        env = {
            "ERDOS_LOAD_DOTENV": "1",
            "ERDOS_REPO_ROOT": str(tmp_path),
            "ARISTOTLE_API_KEY": "from-env",
        }
        with patch.dict(os.environ, env, clear=True):
            initialize_environment()
            config = AppConfig.from_env()
            assert config.aristotle_api_key == "from-env"

    def test_dotenv_overrides_empty_env_var(self, tmp_path: Path) -> None:
        """Empty/whitespace env vars are treated as unset when loading `.env`."""
        (tmp_path / ".env").write_text(
            "ARISTOTLE_API_KEY=dotenv-key\n", encoding="utf-8"
        )

        env = {
            "ERDOS_LOAD_DOTENV": "1",
            "ERDOS_REPO_ROOT": str(tmp_path),
            "ARISTOTLE_API_KEY": "   ",
        }
        with patch.dict(os.environ, env, clear=True):
            initialize_environment()
            config = AppConfig.from_env()
            assert config.aristotle_api_key == "dotenv-key"

    def test_initialize_environment_loads_dotenv_from_project_root_when_run_from_subdir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`.env` is discovered from the repo root when running in subdirectories."""
        repo_root = tmp_path / "repo"
        (repo_root / "src" / "erdos").mkdir(parents=True)
        (repo_root / "pyproject.toml").write_text(
            '[project]\nname = "erdos-banger"\n', encoding="utf-8"
        )
        (repo_root / ".env").write_text(
            "ARISTOTLE_API_KEY=dotenv-key\n", encoding="utf-8"
        )
        subdir = repo_root / "formal" / "lean"
        subdir.mkdir(parents=True)

        env = {"ERDOS_LOAD_DOTENV": "1"}
        with patch.dict(os.environ, env, clear=True):
            monkeypatch.chdir(subdir)
            initialize_environment()
            config = AppConfig.from_env()
            assert config.aristotle_api_key == "dotenv-key"


class TestAppContextFromConfig:
    """Test AppContext.from_config() for testability."""

    def test_from_config_uses_explicit_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """from_config() bypasses environment variables entirely."""
        # Create a test problems file
        problems_file = tmp_path / "problems.yaml"
        problems_file.write_text("problems: []\n")

        # Clear env vars to prove we're not using them
        monkeypatch.delenv("ERDOS_DATA_PATH", raising=False)
        monkeypatch.delenv("ERDOS_MAILTO", raising=False)

        # Create config with explicit path
        config = AppConfig(
            data_path=problems_file,
            mailto="explicit@test.com",
        )

        # from_config should work without env vars
        context = AppContext.from_config(config)

        assert context.config.mailto == "explicit@test.com"
        assert context.config.data_path == problems_file

    def test_ensure_index_uses_config_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ensure_index() uses config.index_path when set."""
        # Create a test problems file
        problems_file = tmp_path / "problems.yaml"
        problems_file.write_text("problems: []\n")

        # Create explicit index path
        index_path = tmp_path / "test_index.sqlite"

        # Clear env var to prove we're not using it
        monkeypatch.delenv("ERDOS_INDEX_PATH", raising=False)

        config = AppConfig(data_path=problems_file, index_path=index_path)
        context = AppContext.from_config(config)

        # ensure_index should create at the explicit path
        _ = context.ensure_index()

        # Verify index was created at the configured path
        assert index_path.exists()
