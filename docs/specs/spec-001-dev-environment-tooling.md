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

- Faster dependency resolution than pip in many workflows
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
pdf = []

[project.scripts]
erdos = "erdos.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/erdos"]
```

**Note on the `pdf` extra:** Keep this extra empty for v1. As of 2026-01, `docling==2.68.0` requires `typer<0.20.0`, which conflicts with our `typer>=0.21.1` baseline. Revisit once Docling supports newer Typer versions.

### Dependency Groups (PEP 735)

uv supports standardized dependency groups via `[dependency-groups]` (preferred over legacy `tool.uv.dev-dependencies`).

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

- Fast single-tool lint + format
- Single configuration point
- Drop-in replacement for black formatting
- Many lint rules available

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

[ty](https://docs.astral.sh/ty/) (Astral's new type checker) is promising, but it is still evolving rapidly.

**Decision:** Use mypy for v1. Re-evaluate ty in a later minor release once it is stable enough for our strict typing needs.

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
disallow_incomplete_defs = false  # Fixtures often omit arg annotations

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

  - repo: local
    hooks:
      - id: mypy
        name: mypy (uv)
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
        args: [src/, tests/]

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
.coverage*
coverage.xml
htmlcov/
.hypothesis/

# mypy
.mypy_cache/

# ruff
.ruff_cache/

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

# CI mode: lockfile must be present, up-to-date, and unchanged
uv lock --check
uv sync --frozen
# Exit code: 0, lockfile unchanged and environment synced from uv.lock

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
```

---

## 9) GitHub Actions CI/CD (Required)

The tooling in this spec is enforced in CI. Keep CI responsibilities out of `pytest` (lint/format/typecheck are separate jobs/steps, not tests).

### a) PR/Push CI (Quality Gates)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    env:
      UV_PYTHON: ${{ matrix.python-version }}

    steps:
      - uses: actions/checkout@v6
        with:
          submodules: recursive

      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: |
            uv.lock
            pyproject.toml
            .python-version
          cache-suffix: ${{ matrix.python-version }}

      - name: Install Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Verify lockfile is up-to-date
        run: uv lock --check

      - name: Install dependencies
        run: uv sync --frozen

      - name: Lint
        run: uv run ruff check .

      - name: Format (check)
        run: uv run ruff format . --check

      - name: Type check
        run: uv run mypy src/

      - name: Tests (no Lean, no network)
        run: uv run pytest --cov=erdos --cov-report=xml --cov-fail-under=80 -m "not requires_lean and not requires_network"

      - name: Build (sdist + wheel)
        run: uv build

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        with:
          files: coverage.xml

  test-with-lean:
    runs-on: ubuntu-latest
    env:
      UV_PYTHON: "3.11"

    steps:
      - uses: actions/checkout@v6
        with:
          submodules: recursive

      - name: Cache elan and mathlib
        uses: actions/cache@v5
        with:
          path: |
            ~/.elan
            formal/lean/.lake
          key: lean-${{ hashFiles('formal/lean/lean-toolchain', 'formal/lean/lakefile.lean') }}
          restore-keys: |
            lean-

      - name: Install elan and Lean
        run: |
          curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y --default-toolchain none
          echo "$HOME/.elan/bin" >> $GITHUB_PATH

      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: |
            uv.lock
            pyproject.toml
          cache-suffix: lean

      - name: Install Python 3.11
        run: uv python install 3.11

      - name: Verify lockfile is up-to-date
        run: uv lock --check

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run Lean-dependent tests
        run: uv run pytest -m "requires_lean"
```

### b) Release (Tag → Build → Publish)

Use PyPI trusted publishing (OIDC) instead of long-lived tokens.

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: read
  id-token: write

jobs:
  publish:
    runs-on: ubuntu-latest
    env:
      UV_PYTHON: "3.11"
    steps:
      - uses: actions/checkout@v6

      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: |
            uv.lock
            pyproject.toml

      - name: Install Python 3.11
        run: uv python install 3.11

      - name: Verify lockfile is up-to-date
        run: uv lock --check

      - name: Build distributions
        run: uv build

      - name: Publish to PyPI (trusted publishing)
        run: uv publish --trusted-publishing always
```

### c) Scheduled Dependency Hygiene

Weekly automated dependency updates with automatic PR creation.

```yaml
# .github/workflows/deps.yml
name: Dependency Updates

on:
  schedule:
    - cron: "0 6 * * 1"  # Every Monday at 6am UTC
  workflow_dispatch:      # Allow manual trigger

permissions:
  contents: write
  pull-requests: write

jobs:
  update-deps:
    runs-on: ubuntu-latest
    env:
      UV_PYTHON: "3.11"

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v7

      - name: Install Python 3.11
        run: uv python install 3.11

      - name: Update dependencies
        run: uv lock --upgrade

      - name: Check for changes
        id: changes
        run: |
          if git diff --quiet uv.lock; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Create Pull Request
        if: steps.changes.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v8
        with:
          commit-message: "chore(deps): update dependencies"
          title: "chore(deps): weekly dependency update"
          body: |
            Automated dependency update via `uv lock --upgrade`.

            This PR updates all dependencies to their latest compatible versions.
            Review the lockfile diff and ensure CI passes before merging.
          branch: deps/weekly-update
          delete-branch: true
          labels: dependencies
```

**Policy:**
- Treat dependency bumps as normal PRs: CI must pass
- Review lockfile changes for unexpected major version bumps
- Merge only after all tests pass

---

## 10) References

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv Project Configuration](https://docs.astral.sh/uv/concepts/projects/config/)
- [uv Dependency Groups](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups)
- [PEP 735 (Dependency Groups)](https://peps.python.org/pep-0735/)
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
