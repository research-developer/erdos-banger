# Spec 001: Development Environment & Tooling

> Foundation spec for Python tooling stack. All other specs depend on this.

---

## Overview

This spec defines the exact development environment, package management, linting, formatting, and type checking configuration for the erdos-harness project.

### Guiding Principles

- **Single source of truth:** All configuration lives in `pyproject.toml` where possible
- **Fast feedback:** Tools must be fast enough to run on every save
- **Strict by default:** Catch errors early, relax rules only with explicit justification
- **Reproducible:** Lock files ensure identical environments across machines

---

## 1) Package Manager: uv

We use [uv](https://docs.astral.sh/uv/) (Astral's Rust-based package manager) instead of pip/Poetry/PDM.

### Why uv

- 10-100x faster than pip for dependency resolution
- Native lockfile support (`uv.lock`)
- Built-in virtual environment management
- Same team as ruff (Astral) - coherent toolchain
- Direct `pyproject.toml` support

### Configuration

**pyproject.toml:**
```toml
[project]
name = "erdos-harness"
version = "0.1.0"
description = "CLI toolkit for Erdős problem research"
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["erdos", "mathematics", "lean", "theorem-proving", "research"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Mathematics",
]

dependencies = [
    "typer>=0.21.1",
    "rich>=14.2.0",
    "pydantic>=2.12.5",
    "pyyaml>=6.0.3",
    "jinja2>=3.1.6",
]

[project.optional-dependencies]
pdf = ["docling>=2.68.0"]

[project.scripts]
erdos = "erdos.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/erdos"]
```

### uv-Specific Configuration

**pyproject.toml (continued):**
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "pytest-xdist>=3.8.0",
    "pytest-mock>=3.15.1",
    "hypothesis>=6.150.2",
    "ruff>=0.14.13",
    "mypy>=1.19.1",
    "pre-commit>=4.5.1",
    "responses>=0.25.8",
    "types-PyYAML>=6.0.12.20250915",
]
```

### Files Generated

- `uv.lock` - Exact dependency versions (commit to git)
- `.python-version` - Python version for the project
- `.venv/` - Virtual environment (gitignored)

### Commands

```bash
# Initial setup
uv sync                    # Create venv, install all deps
uv run erdos --version     # Run CLI through uv

# Add dependencies
uv add requests            # Add production dependency
uv add --dev pytest-mock   # Add dev dependency

# Update
uv lock --upgrade          # Update all deps in lockfile
uv sync                    # Apply updates to venv
```

---

## 2) Project Layout: src Layout

We use the [src layout](https://docs.pytest.org/en/stable/explanation/goodpractices.html) recommended by pytest.

```
erdos-harness/
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── LICENSE
├── src/
│   └── erdos/
│       ├── __init__.py
│       ├── cli.py
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── list_cmd.py
│       │   ├── show.py
│       │   └── ...
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── ...
│       └── py.typed            # PEP 561 marker
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── unit/
│   │   └── ...
│   ├── integration/
│   │   └── ...
│   └── e2e/
│       └── ...
├── data/
│   └── erdosproblems/          # Git submodule
├── formal/
│   └── lean/
└── docs/
    └── specs/
```

### Why src Layout

- Prevents accidental imports from the working directory
- Forces you to install the package to test it (catches packaging bugs)
- Clear separation between source code and project files
- pytest's `--import-mode=importlib` works cleanly

---

## 3) Linter & Formatter: ruff

We use [ruff](https://docs.astral.sh/ruff/) for both linting and formatting, replacing:
- black (formatting)
- isort (import sorting)
- flake8 + plugins (linting)
- pyupgrade (Python version upgrades)

### Why ruff

- 10-100x faster than individual tools
- Single configuration point
- Drop-in replacement for black formatting
- 800+ lint rules available

### Configuration

**pyproject.toml:**
```toml
[tool.ruff]
target-version = "py311"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TC",     # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate (commented-out code)
    "S",      # flake8-bandit (security)
    "PL",     # Pylint
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # line too long (formatter handles this)
    "PLR0913", # too many arguments (sometimes necessary)
    "PLR2004", # magic value comparison (too noisy)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ARG",    # Unused arguments OK in tests (fixtures)
    "S101",   # assert OK in tests
    "PLR2004", # Magic values OK in tests
]

[tool.ruff.lint.isort]
known-first-party = ["erdos"]
force-single-line = false
lines-after-imports = 2

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = true
```

### Commands

```bash
uv run ruff check .              # Lint
uv run ruff check . --fix        # Lint + autofix
uv run ruff format .             # Format
uv run ruff format . --check     # Check formatting (CI)
```

---

## 4) Type Checking: mypy (Strict Mode)

We use [mypy](https://mypy.readthedocs.io/) in strict mode for type checking.

### Why mypy over ty

[ty](https://docs.astral.sh/ty/) (Astral's new type checker) is 10-60x faster, but:
- Still in beta (released Dec 2025)
- ~15% conformance vs ~69% for mature checkers
- No plugin support (we may need Pydantic plugin)

**Decision:** Use mypy for v1. Evaluate ty for v1.2 when it reaches stable.

### Configuration

**pyproject.toml:**
```toml
[tool.mypy]
python_version = "3.11"
plugins = ["pydantic.mypy"]
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
implicit_optional = false
warn_redundant_casts = true
warn_unused_configs = true
show_error_codes = true
show_column_numbers = true

# Per-module overrides
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # Test functions don't need full typing

[[tool.mypy.overrides]]
module = "yaml.*"
ignore_missing_imports = true

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

### py.typed Marker

Create `src/erdos/py.typed` (empty file) to indicate the package ships type information (PEP 561).

### Commands

```bash
uv run mypy src/                 # Type check source
uv run mypy src/ tests/          # Include tests
```

---

## 5) Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to run checks before each commit.

### Configuration

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.13
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.19.1
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.12.5
          - types-PyYAML>=6.0.12.20250915
        args: [--config-file=pyproject.toml]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key
```

### Setup

```bash
uv run pre-commit install        # Install hooks
uv run pre-commit run --all-files # Run on all files
```

---

## 6) .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
*.egg
dist/
build/

# Virtual environments
.venv/
venv/
ENV/

# uv
.uv/

# IDE
.idea/
.vscode/
*.swp
*.swo
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/
.hypothesis/

# mypy
.mypy_cache/

# Project-specific (gitignored data)
literature/cache/
literature/extracts/
index/*.sqlite
logs/*.yaml
logs/*.json
formal/lean/build/
formal/lean/.lake/
formal/lean/lake-packages/
```

---

## 7) .python-version

```
3.11
```

Pin to 3.11 for now. CI should cover at least 3.11 and 3.12; bump the pin once the project is stable on 3.12+.

---

## 8) Verification: This Spec is Testable

### Acceptance Criteria

After implementing this spec, the following must work:

```bash
# 1. Environment setup works
uv sync
# Exit code: 0, .venv created, all deps installed

# CI mode: refuse to change uv.lock
uv sync --frozen
# Exit code: 0, lockfile unchanged

# 2. CLI is runnable
uv run erdos --version
# Output: erdos-harness 0.1.0

# 3. Linting passes
uv run ruff check src/ tests/
# Exit code: 0

# 4. Formatting is correct
uv run ruff format . --check
# Exit code: 0

# 5. Type checking passes
uv run mypy src/
# Exit code: 0

# 6. Pre-commit hooks run
uv run pre-commit run --all-files
# Exit code: 0
```

### Test File: `tests/test_tooling.py`

```python
"""Verify development tooling is correctly configured."""

from pathlib import Path
import tomllib


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
    from erdos import cli
    assert hasattr(cli, "app")


def test_ruff_check_passes() -> None:
    """Ruff linting should pass on the codebase."""
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "src/", "tests/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Ruff check failed: {result.stdout}"


def test_mypy_passes() -> None:
    """Mypy type checking should pass."""
    result = subprocess.run(
        ["uv", "run", "mypy", "src/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Mypy failed: {result.stdout}"


def test_py_typed_exists() -> None:
    """PEP 561 py.typed marker should exist."""
    py_typed = Path("src/erdos/py.typed")
    assert py_typed.exists(), "Missing py.typed marker for PEP 561"
```

---

## 9) References

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv Project Configuration](https://docs.astral.sh/uv/concepts/projects/config/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)
- [mypy Configuration](https://mypy.readthedocs.io/en/stable/config_file.html)
- [pytest Good Practices (src layout)](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [ty Type Checker](https://docs.astral.sh/ty/) (for future consideration)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
