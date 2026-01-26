"""Centralized application configuration (preferred path).

This module defines :class:`AppConfig` as the canonical configuration surface
for CLI execution. New code should **prefer** threading configuration through
`AppConfig`/`AppContext` rather than reading `os.environ` directly.

Note: a small number of legacy `from_env()` / `from_default()` helpers may still
read environment variables to support third-party tooling integrations.
These should be treated as transitional and avoided in new call sites.

Usage:
    # In composition root (context.py or CLI entry points):
    config = AppConfig.from_env()

    # Pass config to services via constructors or AppContext:
    loader = ProblemLoader(config.data_path)
    index = SearchIndex(config.index_path)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from erdos.core.constants import DEFAULT_HTTP_TIMEOUT
from erdos.core.dotenv_loader import load_dotenv_file


# Default values (matching existing behavior)
DEFAULT_MAILTO = "erdos-banger@example.com"
DEFAULT_RUN_LOG_PATH = Path("logs/runs.jsonl")
DEFAULT_INDEX_PATH = Path("index/erdos.sqlite")
DEFAULT_ARISTOTLE_COMMAND = "aristotle"

__all__ = [
    "DEFAULT_ARISTOTLE_COMMAND",
    "DEFAULT_HTTP_TIMEOUT",
    "DEFAULT_INDEX_PATH",
    "DEFAULT_MAILTO",
    "DEFAULT_RUN_LOG_PATH",
    "AppConfig",
    "build_subprocess_env",
]


def build_subprocess_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Return a subprocess environment dict with optional overrides.

    This is the preferred helper for cases where core modules must pass an explicit
    `env=` to `subprocess.run()` (e.g., to inject a vendor API key) while keeping
    raw `os.environ` access centralized in this module.
    """
    env = dict(os.environ)
    if overrides:
        env.update(overrides)
    return env


_DOTENV_FALSE_VALUES = {"0", "false", "no", "off"}


def _load_dotenv_if_enabled() -> None:
    """Load `.env` into `os.environ` for local CLI ergonomics.

    Controlled by `ERDOS_LOAD_DOTENV` (default: enabled). Values like `0`, `false`,
    `no`, `off` disable loading.

    Does not override existing environment variables (even empty strings).
    """
    raw = os.environ.get("ERDOS_LOAD_DOTENV")
    if raw is not None and raw.strip().lower() in _DOTENV_FALSE_VALUES:
        return

    repo_root = os.environ.get("ERDOS_REPO_ROOT")
    env_path = (Path(repo_root) if repo_root else Path.cwd()) / ".env"
    parsed = load_dotenv_file(env_path)
    if not parsed:
        return

    for key, value in parsed.items():
        if key in os.environ:
            continue
        os.environ[key] = value


def initialize_environment() -> None:
    """Initialize process environment for CLI execution.

    Currently this loads `.env` (unless disabled via `ERDOS_LOAD_DOTENV`).
    """
    _load_dotenv_if_enabled()


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration container.

    This dataclass centralizes all environment-based configuration. It is
    frozen (immutable) to prevent accidental mutation after construction.

    Attributes:
        data_path: Path to problems YAML (from ERDOS_DATA_PATH).
        index_path: Path to SQLite search index (from ERDOS_INDEX_PATH).
        run_log_path: Path to run log file (from ERDOS_RUN_LOG_PATH).
        repo_root: Repository root path (from ERDOS_REPO_ROOT).
        mailto: Contact email for API polite pools (from ERDOS_MAILTO).
        llm_command: External LLM command (from ERDOS_LLM_COMMAND).
        aristotle_api_key: Aristotle API key (from ARISTOTLE_API_KEY).
        aristotle_command: Path to aristotle CLI (from ERDOS_ARISTOTLE_COMMAND).
        openalex_api_key: OpenAlex API key (from OPENALEX_API_KEY).
        http_timeout: Default HTTP timeout in seconds.
    """

    # Paths (None means use runtime defaults)
    data_path: Path | None = None
    index_path: Path | None = None
    run_log_path: Path = field(default=DEFAULT_RUN_LOG_PATH)
    repo_root: Path | None = None
    submodule_path: Path | None = None

    # API configuration
    mailto: str = DEFAULT_MAILTO
    llm_command: str = ""
    aristotle_api_key: str = ""
    aristotle_command: str = DEFAULT_ARISTOTLE_COMMAND
    openalex_api_key: str = ""
    exa_api_key: str = ""
    exa_cache_ttl_hours: int = 24
    exa_cache_path: Path | None = None
    semantic_scholar_api_key: str = ""
    semantic_scholar_cache_ttl_days: int = 7
    semantic_scholar_cache_path: Path | None = None
    zbmath_cache_ttl_days: int = 30
    zbmath_cache_path: Path | None = None

    # Network
    http_timeout: float = DEFAULT_HTTP_TIMEOUT

    @classmethod
    def from_env(cls) -> AppConfig:
        """Create configuration from environment variables.

        This is the preferred place where `os.environ` reads occur for application
        configuration. All environment variable names and defaults are defined here.

        Environment variables:
            ERDOS_LOAD_DOTENV: Set to 0/false/no/off to disable auto-loading `.env`.
            ERDOS_DATA_PATH: Path to problems YAML file or directory.
            ERDOS_INDEX_PATH: Path to SQLite search index file.
            ERDOS_RUN_LOG_PATH: Path to run log JSONL file.
            ERDOS_REPO_ROOT: Repository root directory.
            ERDOS_SUBMODULE_PATH: Path to teorth/erdosproblems submodule.
            ERDOS_MAILTO: Contact email for API polite pools.
            OPENALEX_EMAIL: Optional alias for ERDOS_MAILTO (used by some OpenAlex tooling).
            ERDOS_LLM_COMMAND: External LLM command for ask/loop.
            ARISTOTLE_API_KEY: API key for Aristotle LLM service.
            ERDOS_ARISTOTLE_COMMAND: Path to aristotle CLI binary.
            OPENALEX_API_KEY: API key for OpenAlex polite pool.
            EXA_API_KEY: API key for Exa Research API.
            ERDOS_EXA_CACHE_TTL: Cache TTL in hours for Exa API (default: 24).
            ERDOS_EXA_CACHE_PATH: Path to Exa cache directory (for testing).
            SEMANTIC_SCHOLAR_API_KEY: API key for Semantic Scholar (optional).
            ERDOS_S2_CACHE_TTL: Cache TTL in days for S2 API (default: 7).
            ERDOS_S2_CACHE_PATH: Path to S2 cache directory (for testing).
            ERDOS_ZBMATH_CACHE_TTL: Cache TTL in days for zbMATH API (default: 30).
            ERDOS_ZBMATH_CACHE_PATH: Path to zbMATH cache directory (for testing).

        Returns:
            AppConfig instance with values from environment.
        """
        # Read paths (None if not set)
        data_path_str = os.environ.get("ERDOS_DATA_PATH")
        index_path_str = os.environ.get("ERDOS_INDEX_PATH")
        run_log_path_str = os.environ.get("ERDOS_RUN_LOG_PATH")
        repo_root_str = os.environ.get("ERDOS_REPO_ROOT")
        submodule_path_str = os.environ.get("ERDOS_SUBMODULE_PATH")
        exa_cache_path_str = os.environ.get("ERDOS_EXA_CACHE_PATH")
        s2_cache_path_str = os.environ.get("ERDOS_S2_CACHE_PATH")
        zbmath_cache_path_str = os.environ.get("ERDOS_ZBMATH_CACHE_PATH")

        def _clean_env(value: str | None) -> str | None:
            if value is None:
                return None
            cleaned = value.strip()
            return cleaned or None

        mailto = (
            _clean_env(os.environ.get("ERDOS_MAILTO"))
            or _clean_env(os.environ.get("OPENALEX_EMAIL"))
            or DEFAULT_MAILTO
        )

        return cls(
            data_path=Path(data_path_str) if data_path_str else None,
            index_path=Path(index_path_str) if index_path_str else None,
            run_log_path=(
                Path(run_log_path_str) if run_log_path_str else DEFAULT_RUN_LOG_PATH
            ),
            repo_root=Path(repo_root_str) if repo_root_str else None,
            submodule_path=Path(submodule_path_str) if submodule_path_str else None,
            mailto=mailto,
            llm_command=os.environ.get("ERDOS_LLM_COMMAND", ""),
            aristotle_api_key=os.environ.get("ARISTOTLE_API_KEY", "").strip(),
            aristotle_command=os.environ.get(
                "ERDOS_ARISTOTLE_COMMAND", DEFAULT_ARISTOTLE_COMMAND
            ).strip(),
            openalex_api_key=os.environ.get("OPENALEX_API_KEY", "").strip(),
            exa_api_key=os.environ.get("EXA_API_KEY", "").strip(),
            exa_cache_ttl_hours=_parse_int_env("ERDOS_EXA_CACHE_TTL", 24),
            exa_cache_path=Path(exa_cache_path_str) if exa_cache_path_str else None,
            semantic_scholar_api_key=os.environ.get(
                "SEMANTIC_SCHOLAR_API_KEY", ""
            ).strip(),
            semantic_scholar_cache_ttl_days=_parse_int_env("ERDOS_S2_CACHE_TTL", 7),
            semantic_scholar_cache_path=(
                Path(s2_cache_path_str) if s2_cache_path_str else None
            ),
            zbmath_cache_ttl_days=_parse_int_env("ERDOS_ZBMATH_CACHE_TTL", 30),
            zbmath_cache_path=(
                Path(zbmath_cache_path_str) if zbmath_cache_path_str else None
            ),
        )


def _parse_int_env(name: str, default: int) -> int:
    """Parse an integer from environment variable with fallback to default."""
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default
