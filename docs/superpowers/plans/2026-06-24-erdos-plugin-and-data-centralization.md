# Erdős Plugin + Centralized Data Home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `erdos-banger` into an installable Claude Code plugin backed by a fixed `~/.erdos` data home, with the Lean project relocated to its own globally-reachable git repo.

**Architecture:** A single resolver, `data_home()`, decides the data base directory (`$ERDOS_HOME` → discovered repo root → `~/.erdos`). All data paths anchor on it via `repo_path()`. The CLI is installed globally (`uv tool install`); a `.claude-plugin/` manifest + `commands/` wrappers + relocated `skills/` make the repo installable via `/plugin`. The Lean project is split out (history-preserving `git subtree split`) into `research-developer/erdos-lean` and lives at `~/.erdos/formal/lean`.

**Tech Stack:** Python 3.11+, Typer, Pydantic, pytest, uv, ruff, mypy; Lean 4 (`leanprover/lean4:v4.27.0`) + elan/lake + mathlib; git/`gh`; Claude Code plugin format.

## Global Constraints

- Python 3.11+, strict mypy typing; ruff lint+format (configured in `pyproject.toml`). One line each implicitly applies to every task.
- 80% minimum coverage; `make ci` must pass before each phase-ending commit.
- Command modules ≤ 400 LOC, core modules ≤ 500 LOC, functions ≤ 120 LOC (`make audit`).
- All structural/destructive git work happens on the **fork** (`research-developer/erdos-banger`), on branch `feat/erdos-plugin-and-central-data`, never on `main` or `upstream`.
- Data home default is `~/.erdos`; `$ERDOS_HOME` overrides; per-path env overrides (`ERDOS_DATA_PATH`, `ERDOS_INDEX_PATH`, `ERDOS_SUBMODULE_PATH`, `ERDOS_LEAN_PROJECT`) win individually.
- Lean toolchain reached via `source ~/.elan/env`; never assume which `conda` is active (target `/opt/anaconda3/envs/math` explicitly).
- Tests must manage `ERDOS_HOME`/`ERDOS_LEAN_PROJECT` explicitly (monkeypatch set/delenv); never create real `~/.erdos` from a unit test.
- Reference spec: `docs/superpowers/specs/2026-06-24-erdos-plugin-and-data-centralization-design.md`.

## File Structure

**Modified (code):**
- `src/erdos/core/repo_root.py` — add `data_home()`; re-anchor `repo_path()`/`resolve_repo_root(None)`.
- `src/erdos/core/config.py` — anchor `run_log_path` default via `default_factory`; anchor index/run-log in `from_env`; remove `DEFAULT_INDEX_PATH`/`DEFAULT_RUN_LOG_PATH` constants; add `ERDOS_LEAN_PROJECT` to `get_default_lean_project_path()`; materialize `ERDOS_HOME`/`ERDOS_LEAN_PROJECT` into `os.environ` in `initialize_environment()`.
- `src/erdos/core/search/facade.py`, `src/erdos/mcp/server.py` — index fallback via `repo_path(...)`.
- `src/erdos/core/sync/submodule.py` — de-lazy `DEFAULT_SUBMODULE_PATH`.
- `src/erdos/core/clients/{exa,cache,semantic_scholar,zbmath}.py`, `src/erdos/core/batch/runner.py` — lazy `repo_path(...)` defaults.

**Created (plugin + ops):**
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- `commands/erdos-*.md` (10 files)
- `skills/erdos/SKILL.md`, `skills/erdos-prove/SKILL.md` (moved from `.claude/skills/`)
- `scripts/erdos_home_setup.sh`
- `formal/README.md` (pointer after Lean relocation)

**Created (tests):**
- `tests/unit/core/test_paths_centralization.py`

**External repos:** `research-developer/erdos-banger` (fork), `research-developer/erdos-lean` (subtree split).

---

## Phase 0 — Fork & branch (ops)

### Task 0.1: Fork upstream, set remotes, create branch, commit spec

**Files:** none (git/remote ops). Verifies the working tree from the existing clone.

- [ ] **Step 1: Confirm starting state**

Run: `git remote -v && git branch --show-current`
Expected: `origin` → `https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git`; branch `main`.

- [ ] **Step 2: Create the fork under research-developer (no clone; we already have one)**

Run: `gh repo fork The-Obstacle-Is-The-Way/erdos-banger --clone=false`
Expected: `✓ Created fork research-developer/erdos-banger` (or `! ... already exists`, which is fine).

- [ ] **Step 3: Repoint remotes deterministically (origin = fork, upstream = original)**

```bash
git remote rename origin upstream
git remote add origin https://github.com/research-developer/erdos-banger.git
git fetch origin
git remote -v
```
Expected: `origin` → `research-developer/erdos-banger`, `upstream` → `The-Obstacle-Is-The-Way/erdos-banger`.

- [ ] **Step 4: Create the feature branch off the current main**

```bash
git checkout -b feat/erdos-plugin-and-central-data
```

- [ ] **Step 5: Commit the design spec as the first commit on the branch**

```bash
git add docs/superpowers/specs/2026-06-24-erdos-plugin-and-data-centralization-design.md \
        docs/superpowers/plans/2026-06-24-erdos-plugin-and-data-centralization.md
git commit -m "docs: add plugin + central-data design spec and implementation plan

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Verify**

Run: `git log --oneline -1 && git status`
Expected: the commit is present; working tree clean.

---

## Phase 1 — Path centralization (code, TDD)

### Task 1.1: `data_home()` resolver + re-anchor `repo_path()`

**Files:**
- Modify: `src/erdos/core/repo_root.py`
- Test: `tests/unit/core/test_repo_root.py` (extend)

**Interfaces:**
- Produces: `data_home() -> Path` (precedence `$ERDOS_HOME` → `discover_repo_root()` → `~/.erdos`); `repo_path(*parts: str) -> Path` anchored on `data_home()`; `resolve_repo_root(repo_root: Path | None) -> Path` (None → `data_home()`).

- [ ] **Step 1: Write failing tests** in `tests/unit/core/test_repo_root.py` (append):

```python
class TestDataHome:
    """Tests for data_home() precedence."""

    def test_explicit_env_wins(self, monkeypatch, tmp_path: Path) -> None:
        from erdos.core.repo_root import data_home
        monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
        assert data_home() == tmp_path.resolve()

    def test_prefers_discovered_repo_when_no_env(self, monkeypatch, tmp_path: Path) -> None:
        import erdos.core.repo_root as rr
        monkeypatch.delenv("ERDOS_HOME", raising=False)
        fake = (tmp_path / "repo").resolve()
        monkeypatch.setattr(rr, "discover_repo_root", lambda start=None: fake)
        assert rr.data_home() == fake

    def test_defaults_to_dot_erdos(self, monkeypatch, tmp_path: Path) -> None:
        import erdos.core.repo_root as rr
        monkeypatch.delenv("ERDOS_HOME", raising=False)
        monkeypatch.setattr(rr, "discover_repo_root", lambda start=None: None)
        assert rr.data_home() == (Path.home() / ".erdos").resolve()

    def test_repo_path_anchors_on_data_home(self, monkeypatch, tmp_path: Path) -> None:
        from erdos.core.repo_root import repo_path
        monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
        assert repo_path("index", "erdos.sqlite") == (tmp_path / "index" / "erdos.sqlite").resolve()
```

Also add a defensive `monkeypatch.delenv("ERDOS_HOME", raising=False)` as the first line of the existing `TestResolveRepoRoot::test_discovers_when_none` and `TestRepoPath::test_result_is_under_repo_root` (they assume in-repo discovery; an inherited `ERDOS_HOME` would break them).

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/unit/core/test_repo_root.py::TestDataHome -v`
Expected: FAIL — `ImportError: cannot import name 'data_home'`.

- [ ] **Step 3: Rewrite `src/erdos/core/repo_root.py`**

```python
"""Repository root + data-home discovery helpers.

Data historically lived under the project root (data/, logs/, index/, ...).
The `erdos` CLI can now run from anywhere (installed as a global tool / Claude
plugin), so data resolves to a fixed *data home*:

    1. $ERDOS_HOME, if set (and non-empty)
    2. a discovered project root (when running inside a checkout)
    3. ~/.erdos (default)

`repo_path()` anchors all data paths on this home.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_HOME = Path.home() / ".erdos"


def _looks_like_repo_root(path: Path) -> bool:
    """Return True if `path` appears to be the erdos-banger project root."""
    return (path / "pyproject.toml").is_file() and (path / "src" / "erdos").is_dir()


def discover_repo_root(start: Path | None = None) -> Path | None:
    """Discover the repository root by walking ancestors from `start`."""
    resolved = (start or Path.cwd()).resolve()
    for candidate in (resolved, *resolved.parents):
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def data_home() -> Path:
    """Resolve the centralized data home (see module docstring)."""
    explicit = os.environ.get("ERDOS_HOME")
    if explicit and explicit.strip():
        return Path(explicit).expanduser().resolve()
    discovered = discover_repo_root()
    if discovered is not None:
        return discovered
    return DEFAULT_DATA_HOME.resolve()


def resolve_repo_root(repo_root: Path | None) -> Path:
    """Resolve a usable base directory.

    Explicit `repo_root` wins; otherwise the data home is used (which prefers a
    discovered checkout, falling back to ~/.erdos).
    """
    if repo_root is not None:
        return repo_root.resolve()
    return data_home()


def repo_path(*parts: str) -> Path:
    """Absolute path under the data home. Use instead of hardcoded `Path("data/...")`."""
    return data_home().joinpath(*parts)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/unit/core/test_repo_root.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add src/erdos/core/repo_root.py tests/unit/core/test_repo_root.py
git commit -m "feat(paths): add data_home() resolver; anchor repo_path on ~/.erdos default

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.2: Anchor stray relative defaults through `repo_path()`

Index, run-log, client caches, batch state, and submodule default currently resolve relative to **cwd** (or freeze at import). Route them all through `repo_path()`.

**Files:**
- Modify: `src/erdos/core/config.py` (run-log default; drop `DEFAULT_INDEX_PATH`/`DEFAULT_RUN_LOG_PATH`)
- Modify: `src/erdos/core/search/facade.py`, `src/erdos/mcp/server.py` (index fallback)
- Modify: `src/erdos/core/sync/submodule.py` (de-lazy submodule default)
- Modify: `src/erdos/core/clients/{exa,cache,semantic_scholar,zbmath}.py`, `src/erdos/core/batch/runner.py`
- Test: `tests/unit/core/test_paths_centralization.py` (new)

**Interfaces:**
- Consumes: `repo_path()` from Task 1.1.
- Produces: `AppConfig.from_env().run_log_path` and `AppConfig().run_log_path` resolve under data home; `SearchIndex.from_default()` and the MCP index resolve under data home; `get_submodule_path()` returns `repo_path("data","erdosproblems")` at call time.

- [ ] **Step 1: Write failing tests** — create `tests/unit/core/test_paths_centralization.py`:

```python
"""Paths centralization: relative defaults must resolve under the data home."""

from pathlib import Path

import pytest


@pytest.fixture
def home(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
    return tmp_path.resolve()


def test_run_log_path_under_home(home: Path) -> None:
    from erdos.core.config import AppConfig

    assert AppConfig.from_env().run_log_path == home / "logs" / "runs.jsonl"


def test_run_log_path_default_construction_under_home(home: Path) -> None:
    from erdos.core.config import AppConfig

    assert AppConfig().run_log_path == home / "logs" / "runs.jsonl"


def test_search_index_default_under_home(home: Path, monkeypatch) -> None:
    monkeypatch.delenv("ERDOS_INDEX_PATH", raising=False)
    from erdos.core.search.facade import SearchIndex

    idx = SearchIndex.from_default()
    assert Path(idx.db_path) == home / "index" / "erdos.sqlite"


def test_submodule_default_under_home(home: Path, monkeypatch) -> None:
    monkeypatch.delenv("ERDOS_SUBMODULE_PATH", raising=False)
    from erdos.core.sync.submodule import get_submodule_path

    assert get_submodule_path() == home / "data" / "erdosproblems"
```

> Note: `SearchIndex` exposes its path; if the attribute is not `db_path`, use the actual attribute (inspect `src/erdos/core/search/facade.py` `__init__`). Adjust the assertion accordingly — the requirement is "equals `home/index/erdos.sqlite`".

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/unit/core/test_paths_centralization.py -v`
Expected: FAIL (paths resolve to cwd-relative `logs/`, `index/`, `data/`).

- [ ] **Step 3a: `config.py` — anchor run-log; drop relative constants**

Remove lines `DEFAULT_RUN_LOG_PATH = Path("logs/runs.jsonl")` and `DEFAULT_INDEX_PATH = Path("index/erdos.sqlite")`, and their entries in `__all__`. Change the dataclass field:

```python
    run_log_path: Path = field(default_factory=lambda: repo_path("logs", "runs.jsonl"))
```

In `from_env`, replace the run-log branch:

```python
            run_log_path=(
                Path(run_log_path_str) if run_log_path_str else repo_path("logs", "runs.jsonl")
            ),
```

(`repo_path` is already imported at `config.py:28`.)

- [ ] **Step 3b: `facade.py` — index fallback**

Add import `from erdos.core.repo_root import repo_path`; replace the `DEFAULT_INDEX_PATH` import with nothing; change the final fallback:

```python
        # 3. Default path (under the data home)
        return cls(repo_path("index", "erdos.sqlite"))
```

- [ ] **Step 3c: `mcp/server.py` — index fallback**

Remove the `DEFAULT_INDEX_PATH` import; add `from erdos.core.repo_root import repo_path`; replace `default_path = DEFAULT_INDEX_PATH` with `default_path = repo_path("index", "erdos.sqlite")`.

- [ ] **Step 3d: `sync/submodule.py` — de-lazy submodule default**

Delete `DEFAULT_SUBMODULE_PATH = repo_path("data", "erdosproblems")` (import-time freeze). In `get_submodule_path`, change the final return to:

```python
    return repo_path("data", "erdosproblems")
```

- [ ] **Step 3e: client caches + batch state — lazy defaults**

For each of `clients/exa.py`, `clients/semantic_scholar.py`, `clients/zbmath.py`: replace the module constant
`DEFAULT_CACHE_PATH = Path("literature/cache/<X>")`
with a function and update references:

```python
def _default_cache_path() -> Path:
    return repo_path("literature", "cache", "<X>")
```

(`<X>` = `exa` / `s2` / `zbmath` respectively). Add `from erdos.core.repo_root import repo_path`. Replace every `DEFAULT_CACHE_PATH` use with `_default_cache_path()`.

For `clients/cache.py`: change `cache_path=Path("literature/cache/api")` to `cache_path=repo_path("literature", "cache", "api")` (add the import).

For `batch/runner.py:72`: change `self.state_dir = state_dir or Path("logs")` to `self.state_dir = state_dir or repo_path("logs")` (add the import).

- [ ] **Step 4: Run tests + grep acceptance**

Run: `uv run pytest tests/unit/core/test_paths_centralization.py -v`
Expected: PASS.

Run: `grep -rn 'Path("data\|Path("index\|Path("logs\|Path("literature\|Path("formal' src/erdos/ | grep -v -E 'docstring|example|#'`
Expected: no remaining **runtime default** bare relative data paths (matches inside docstrings/`>>>` examples in `lean/aristotle.py` and `lean/runner.py` are illustrative only — leave them).

- [ ] **Step 5: Full check + commit**

Run: `make lint && make typecheck && uv run pytest -m "not requires_lean and not requires_network and not slow" -q`
Expected: PASS.

```bash
git add -A
git commit -m "feat(paths): anchor index/run-log/cache/submodule defaults on data home

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.3: `ERDOS_LEAN_PROJECT` + subprocess env materialization

**Files:**
- Modify: `src/erdos/core/config.py` (`get_default_lean_project_path`, `initialize_environment`)
- Test: `tests/unit/core/test_config.py` (extend)

**Interfaces:**
- Consumes: `repo_path()`, `data_home()`.
- Produces: `get_default_lean_project_path() -> Path` precedence `$ERDOS_LEAN_PROJECT` → `repo_path("formal","lean")`. After `initialize_environment()`, `os.environ["ERDOS_HOME"]` and `os.environ["ERDOS_LEAN_PROJECT"]` are set (so `build_subprocess_env`, which copies `os.environ`, propagates them to spawned `lake`/LLM processes regardless of child cwd).

- [ ] **Step 1: Write failing tests** in `tests/unit/core/test_config.py` (append):

```python
class TestLeanProjectAndEnvMaterialization:
    def test_lean_project_env_override(self, monkeypatch, tmp_path):
        from erdos.core.config import get_default_lean_project_path
        monkeypatch.setenv("ERDOS_LEAN_PROJECT", str(tmp_path / "proj"))
        assert get_default_lean_project_path() == (tmp_path / "proj").resolve()

    def test_lean_project_defaults_under_home(self, monkeypatch, tmp_path):
        from erdos.core.config import get_default_lean_project_path
        monkeypatch.delenv("ERDOS_LEAN_PROJECT", raising=False)
        monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
        assert get_default_lean_project_path() == (tmp_path / "formal" / "lean").resolve()

    def test_initialize_environment_materializes_home(self, monkeypatch, tmp_path):
        from erdos.core.config import initialize_environment
        monkeypatch.setenv("ERDOS_LOAD_DOTENV", "0")
        monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
        monkeypatch.delenv("ERDOS_LEAN_PROJECT", raising=False)
        initialize_environment()
        import os
        assert os.environ["ERDOS_HOME"] == str(tmp_path)
        assert os.environ["ERDOS_LEAN_PROJECT"] == str((tmp_path / "formal" / "lean").resolve())
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/unit/core/test_config.py::TestLeanProjectAndEnvMaterialization -v`
Expected: FAIL.

- [ ] **Step 3: Edit `config.py`**

Add import near the top: `from erdos.core.repo_root import data_home, repo_path, resolve_repo_root` (extend the existing import line).

Replace `get_default_lean_project_path`:

```python
def get_default_lean_project_path() -> Path:
    """Resolve the Lean project: $ERDOS_LEAN_PROJECT, else <data-home>/formal/lean."""
    explicit = os.environ.get("ERDOS_LEAN_PROJECT")
    if explicit and explicit.strip():
        return Path(explicit).expanduser().resolve()
    return repo_path("formal", "lean")
```

Extend `initialize_environment` to materialize the resolved home so subprocesses inherit it:

```python
def initialize_environment() -> None:
    """Initialize process environment for CLI execution.

    Loads `.env` (unless disabled) then materializes the resolved data home and
    Lean project into `os.environ` so child processes (lake, LLM, aristotle)
    inherit a consistent location regardless of their working directory.
    """
    _load_dotenv_if_enabled()
    os.environ.setdefault("ERDOS_HOME", str(data_home()))
    os.environ.setdefault("ERDOS_LEAN_PROJECT", str(get_default_lean_project_path()))
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/unit/core/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/erdos/core/config.py tests/unit/core/test_config.py
git commit -m "feat(lean): ERDOS_LEAN_PROJECT resolution + materialize home for subprocesses

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.4: Make Lean-dependent tests location-agnostic

After relocation (Phase 2) `formal/lean` will not exist in-repo. Lean tests must resolve the project via `get_default_lean_project_path()` and skip when absent.

**Files:**
- Modify: `tests/integration/test_lean_runner.py`, `tests/integration/test_lean_import.py`, `tests/integration/test_cli_lean_prove.py`, `tests/unit/commands/test_lean_check.py`, `tests/unit/loop/test_runner.py`, `tests/unit/formal_conjectures/test_provenance.py` (only those that hardcode `formal/lean`).

**Interfaces:** Consumes `get_default_lean_project_path()`.

- [ ] **Step 1: Audit** which of the listed tests hardcode `Path("formal/lean")` / `repo_path("formal","lean")` vs. already use `get_default_lean_project_path()`:

Run: `grep -rn 'formal/lean\|"formal", "lean"\|get_default_lean_project_path' tests/`

- [ ] **Step 2: For each hardcoded reference**, replace the literal with `get_default_lean_project_path()` and add a guard at the top of the test (or use the marker) so it skips cleanly when the project is missing:

```python
import pytest
from erdos.core.config import get_default_lean_project_path

_LEAN_PROJECT = get_default_lean_project_path()
pytestmark = pytest.mark.skipif(
    not (_LEAN_PROJECT / "lakefile.lean").exists(),
    reason="Lean project not present (relocated to ~/.erdos/formal/lean)",
)
```

(Apply `pytestmark` only in modules that actually compile/inspect the project; keep existing `requires_lean` markers.)

- [ ] **Step 3: Run the fast suite to confirm no regressions**

Run: `uv run pytest -m "not requires_lean and not requires_network and not slow" -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test(lean): resolve Lean project via get_default_lean_project_path + skip if absent

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.5: Phase-1 CI checkpoint

- [ ] **Step 1: Full fast CI**

Run: `make ci`
Expected: PASS (lint, typecheck, fast tests, audit, lock-check).

- [ ] **Step 2: Fix any failures inline, then re-run `make ci` until green.** (No commit if nothing changed.)

---

## Phase 2 — Lean relocation (ops/git)

### Task 2.1: Subtree-split `formal/lean` and push to `research-developer/erdos-lean`

**Files:** none (git ops on the fork branch).

- [ ] **Step 1: Split `formal/lean` history into a branch**

```bash
git subtree split --prefix=formal/lean -b lean-split
```
Expected: prints a commit SHA; branch `lean-split` created with `formal/lean` at its root.

- [ ] **Step 2: Create the (private) standalone repo**

Run: `gh repo create research-developer/erdos-lean --private`
Expected: `✓ Created repository research-developer/erdos-lean on GitHub`.

- [ ] **Step 3: Push the split history as `main`**

```bash
git push https://github.com/research-developer/erdos-lean.git lean-split:main
```
Expected: push succeeds; `lean-split` history now on `erdos-lean` `main`.

- [ ] **Step 4: Verify remotely**

Run: `gh api repos/research-developer/erdos-lean/contents/lakefile.lean --jq .name`
Expected: `lakefile.lean`.

### Task 2.2: Clone into `~/.erdos/formal/lean`, wire remotes, fetch mathlib cache

**Files:** none (creates `~/.erdos/formal/lean`).

- [ ] **Step 1: Clone into the data home**

```bash
mkdir -p ~/.erdos/formal
git clone https://github.com/research-developer/erdos-lean.git ~/.erdos/formal/lean
git -C ~/.erdos/formal/lean remote add upstream https://github.com/research-developer/erdos-banger.git
```
Expected: clone succeeds; `upstream` added (for future `git subtree pull --prefix=formal/lean upstream <branch>`).

- [ ] **Step 2: Fetch mathlib cache (long-running; needs elan on PATH)**

```bash
source ~/.elan/env
cd ~/.erdos/formal/lean && lake exe cache get
```
Expected: mathlib cache downloaded. (Heavy/slow — one-time.)

- [ ] **Step 3: Verify the relocated project resolves + builds via the CLI**

```bash
cd /tmp && ERDOS_LEAN_PROJECT="$HOME/.erdos/formal/lean" uv run --project /Users/psentro/git/erdos-banger erdos lean check "$HOME/.erdos/formal/lean/Erdos/Problem848.lean"
```
Expected: compiles (or reports real Lean diagnostics) — proving the project is reachable from an arbitrary cwd via `ERDOS_LEAN_PROJECT`.

### Task 2.3: Remove `formal/lean` from the fork; add pointer

**Files:**
- Delete: `formal/lean/**`
- Create: `formal/README.md`
- Modify: `CLAUDE.md` (Lean Notes paths), `data/README.md` if it references `formal/lean`.

- [ ] **Step 1: Remove the tree (history preserved in `erdos-lean` + `lean-split`)**

```bash
git rm -r formal/lean
```

- [ ] **Step 2: Add `formal/README.md`**

```markdown
# Lean formalization (relocated)

The Lean 4 project moved to its own repo: **research-developer/erdos-lean**,
cloned to `~/.erdos/formal/lean` (the data home).

- Resolve it from anywhere via `ERDOS_LEAN_PROJECT` (defaults to `<data-home>/formal/lean`).
- Pull upstream `formal/lean` changes: `git -C ~/.erdos/formal/lean subtree pull --prefix=. upstream <branch>` (or fetch via the erdos-banger fork).
- Run checks: `erdos lean check ~/.erdos/formal/lean/Erdos/ProblemXXX.lean`.
```

- [ ] **Step 3: Update doc references**

In `CLAUDE.md` "Lean Notes", change examples from `formal/lean/Erdos/Problem848.lean` to `~/.erdos/formal/lean/Erdos/Problem848.lean` and `lake -d formal/lean ...` to `lake -d ~/.erdos/formal/lean ...`. Grep first: `grep -rn "formal/lean" CLAUDE.md data/README.md`.

- [ ] **Step 4: Fast CI still green (Lean tests skip cleanly)**

Run: `make ci`
Expected: PASS; Lean-marked tests skip (project absent in-repo).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(lean): relocate formal/lean to research-developer/erdos-lean (~/.erdos)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3 — Plugin packaging

### Task 3.1: Plugin + marketplace manifests

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: `.claude-plugin/plugin.json`**

```json
{
  "name": "erdos",
  "version": "0.1.0",
  "description": "Erdős problems research toolkit: literature search, RAG Q&A, and Lean 4 formalization, backed by a centralized ~/.erdos data home.",
  "author": { "name": "research-developer" },
  "homepage": "https://github.com/research-developer/erdos-banger",
  "keywords": ["erdos", "math", "lean4", "research", "formalization"]
}
```

- [ ] **Step 2: `.claude-plugin/marketplace.json`**

```json
{
  "name": "erdos-banger",
  "owner": { "name": "research-developer" },
  "plugins": [
    {
      "name": "erdos",
      "source": "./",
      "description": "Erdős problems research toolkit (CLI wrappers, skills, centralized data home)."
    }
  ]
}
```

- [ ] **Step 3: Verify JSON validity**

Run: `python -c "import json,pathlib; [json.loads(pathlib.Path(p).read_text()) for p in ('.claude-plugin/plugin.json','.claude-plugin/marketplace.json')]; print('ok')"`
Expected: `ok`.

### Task 3.2: Relocate skills to plugin `skills/`

**Files:**
- Move: `.claude/skills/erdos/SKILL.md` → `skills/erdos/SKILL.md`; `.claude/skills/erdos-prove/SKILL.md` → `skills/erdos-prove/SKILL.md`
- Modify: `CLAUDE.md` (skills table path note)

- [ ] **Step 1: Move with history**

```bash
mkdir -p skills
git mv .claude/skills/erdos skills/erdos
git mv .claude/skills/erdos-prove skills/erdos-prove
rmdir .claude/skills .claude 2>/dev/null || true
```
Expected: files staged as renames.

- [ ] **Step 2: Update `CLAUDE.md`** — in the Skills table, change `.claude/skills/` to `skills/` (plugin root) and add a line: "Skills ship via the `erdos` plugin (`skills/`); `.codex/skills/` remains for Codex." Grep: `grep -rn ".claude/skills" CLAUDE.md`.

- [ ] **Step 3: Verify discovery paths exist**

Run: `ls skills/erdos/SKILL.md skills/erdos-prove/SKILL.md`
Expected: both listed.

### Task 3.3: Author command wrappers

**Files:**
- Create: `commands/erdos-setup.md`, `commands/erdos-sync.md`, `commands/erdos-list.md`, `commands/erdos-show.md`, `commands/erdos-search.md`, `commands/erdos-refs.md`, `commands/erdos-ingest.md`, `commands/erdos-ask.md`, `commands/erdos-formalize.md`, `commands/erdos-check.md`

- [ ] **Step 1: Create the CLI-wrapper commands.** Each is the same shape; use this exact template, substituting per the table:

Template (`commands/erdos-<name>.md`):

```markdown
---
description: <DESCRIPTION>
argument-hint: "<HINT>"
allowed-tools: Bash(erdos:*)
---

Run the Erdős CLI and summarize the result for the user.

If `erdos` is not on PATH, tell the user to run `/erdos-setup` first, then stop.

```bash
erdos <SUBCMD> $ARGUMENTS
```
```

| File | `<DESCRIPTION>` | `<HINT>` | `<SUBCMD>` |
|------|-----------------|----------|------------|
| erdos-list.md | List Erdős problems | `[--status open] [--limit N] [--tag T]` | `list` |
| erdos-show.md | Show one Erdős problem | `<id>` | `show` |
| erdos-search.md | Search problems/literature (FTS) | `<query> [--build-index]` | `search` |
| erdos-refs.md | Show references for a problem | `<id>` | `refs` |
| erdos-ingest.md | Ingest references for a problem | `<id> [--source arxiv]` | `ingest` |
| erdos-ask.md | RAG Q&A over a problem | `<id> "<question>"` | `ask` |
| erdos-formalize.md | Generate a Lean skeleton | `<id>` | `lean formalize` |
| erdos-check.md | Compile-check a Lean file | `<path>` | `lean check` |
| erdos-sync.md | Sync problem data into ~/.erdos | `[all\|website <id>]` | `sync` |

- [ ] **Step 2: Create `commands/erdos-setup.md`** (delegates to the script from Task 4.2):

```markdown
---
description: One-time setup — create ~/.erdos, install the erdos CLI, clone the Lean project, write ~/.erdos/.env
argument-hint: ""
allowed-tools: Bash(bash:*), Bash(erdos:*)
---

Bootstrap the Erdős data home and CLI. Run the setup script (idempotent — safe to re-run), then report what it did and any next steps it prints (e.g. shell-profile lines to add).

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/erdos_home_setup.sh"
```

After it completes, verify with `erdos --version` and `erdos list --limit 1`.
```

- [ ] **Step 3: Verify all command files parse** (frontmatter present)

Run: `for f in commands/erdos-*.md; do head -1 "$f" | grep -q '^---$' && echo "ok $f" || echo "BAD $f"; done`
Expected: `ok` for all 10.

### Task 3.4: Validate plugin structure + commit Phase 3

- [ ] **Step 1: Dispatch the `plugin-dev:plugin-validator` agent** against the repo root to validate `.claude-plugin/plugin.json`, `marketplace.json`, `commands/`, and `skills/`. Address any errors it reports.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(plugin): add .claude-plugin manifests, command wrappers, relocate skills

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — Bootstrap, migration & sync (ops)

### Task 4.1: Setup script

**Files:**
- Create: `scripts/erdos_home_setup.sh`

- [ ] **Step 1: Write `scripts/erdos_home_setup.sh`**

```bash
#!/usr/bin/env bash
# Idempotent bootstrap for the Erdős data home + CLI. Safe to re-run.
set -euo pipefail

ERDOS_HOME="${ERDOS_HOME:-$HOME/.erdos}"
# Repo root = two levels up from this script (scripts/ -> repo root)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAN_REPO="https://github.com/research-developer/erdos-lean.git"
ERDOS_FORK="https://github.com/research-developer/erdos-banger.git"
SUBMODULE_REPO="https://github.com/teorth/erdosproblems.git"

echo "==> data home: $ERDOS_HOME"
mkdir -p "$ERDOS_HOME"/{data,literature/manifests,index,logs,formal}

# Lean toolchain on PATH (best-effort)
[ -f "$HOME/.elan/env" ] && . "$HOME/.elan/env"

echo "==> installing erdos CLI (uv tool install --editable)"
uv tool install --editable "$REPO_ROOT" --force

# Lean project
if [ ! -d "$ERDOS_HOME/formal/lean/.git" ]; then
  echo "==> cloning Lean project"
  git clone "$LEAN_REPO" "$ERDOS_HOME/formal/lean"
  git -C "$ERDOS_HOME/formal/lean" remote add upstream "$ERDOS_FORK" 2>/dev/null || true
fi

# Upstream metadata (plain clone, not a submodule, since we're outside a checkout)
if [ ! -d "$ERDOS_HOME/data/erdosproblems/.git" ]; then
  echo "==> cloning upstream erdosproblems metadata"
  git clone --depth 1 "$SUBMODULE_REPO" "$ERDOS_HOME/data/erdosproblems"
fi

# Migrate any in-repo literature manifests (copy, never overwrite)
if [ -d "$REPO_ROOT/literature/manifests" ]; then
  echo "==> migrating literature manifests"
  cp -an "$REPO_ROOT/literature/manifests/." "$ERDOS_HOME/literature/manifests/" 2>/dev/null || true
fi

# .env (keys/mailto/lean project) — created once, never clobbered
ENV_FILE="$ERDOS_HOME/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "==> writing $ENV_FILE"
  cat > "$ENV_FILE" <<EOF
ERDOS_LEAN_PROJECT=$ERDOS_HOME/formal/lean
ERDOS_SUBMODULE_PATH=$ERDOS_HOME/data/erdosproblems
ERDOS_MAILTO=${ERDOS_MAILTO:-erdos-banger@example.com}
EOF
fi

cat <<EOF

✔ erdos home ready at $ERDOS_HOME
  Next (add to your shell profile, ~/.zshrc):
    export ERDOS_HOME="$ERDOS_HOME"
    [ -f "\$HOME/.elan/env" ] && . "\$HOME/.elan/env"
  Then: erdos list --limit 1
EOF
```

- [ ] **Step 2: Lint the script + make executable**

```bash
chmod +x scripts/erdos_home_setup.sh
command -v shellcheck >/dev/null && shellcheck scripts/erdos_home_setup.sh || echo "(shellcheck not installed; skipping)"
```
Expected: no shellcheck errors (warnings acceptable), or skip note.

- [ ] **Step 3: Commit**

```bash
git add scripts/erdos_home_setup.sh
git commit -m "feat(setup): idempotent ~/.erdos bootstrap script

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 4.2: Run the bootstrap

**Files:** none (populates `~/.erdos`, installs CLI).

- [ ] **Step 1: Run setup**

Run: `bash scripts/erdos_home_setup.sh`
Expected: data home created; `uv tool install` succeeds; Lean + erdosproblems cloned; `~/.erdos/.env` written; next-steps printed.

- [ ] **Step 2: Confirm CLI is global**

```bash
source ~/.elan/env 2>/dev/null || true
which erdos && erdos --version
```
Expected: `erdos` resolves (uv tool bin dir) and prints a version.

- [ ] **Step 3: Confirm data home (run from an unrelated cwd)**

```bash
cd /tmp && ERDOS_HOME="$HOME/.erdos" erdos list --limit 1 --json | head -c 200
```
Expected: JSON output (uses built-in sample dataset until sync runs) — proves from-anywhere resolution.

### Task 4.3: Sync data into `~/.erdos` + build the FTS index

**Files:** none (network; writes under `~/.erdos`).

- [ ] **Step 1: Sync (network).** Prefer `sync all`; tolerate submodule-step quirks.

```bash
cd /tmp
ERDOS_HOME="$HOME/.erdos" erdos sync all || ERDOS_HOME="$HOME/.erdos" erdos sync website
```
Expected: website data fetched into `~/.erdos/data/problems_enriched.yaml`; submodule step reports up-to-date/updated (clone present). Report exactly what ran.

- [ ] **Step 2: Build the FTS index**

```bash
cd /tmp && ERDOS_HOME="$HOME/.erdos" erdos search "squarefree" --build-index --limit 3
```
Expected: index built at `~/.erdos/index/erdos.sqlite`; search returns hits.

- [ ] **Step 3: Verify centralized layout**

Run: `ls -R ~/.erdos | head -40 && test -f ~/.erdos/index/erdos.sqlite && echo INDEX_OK`
Expected: `data/`, `literature/`, `index/erdos.sqlite` (`INDEX_OK`), `logs/`, `formal/lean/` present.

### Task 4.4: End-to-end verification, final CI, PR

- [ ] **Step 1: From-anywhere smoke (no ERDOS_HOME — relies on `~/.erdos` default)**

```bash
cd /tmp
unset ERDOS_HOME
erdos show 848 | head -20
erdos lean check "$HOME/.erdos/formal/lean/Erdos/Problem848.lean" | tail -5
```
Expected: `show 848` works from the default home; `lean check` compiles/reports diagnostics from arbitrary cwd.

- [ ] **Step 2: Plugin install dry-run.** In Claude Code: `/plugin marketplace add /Users/psentro/git/erdos-banger` then `/plugin install erdos@erdos-banger`; confirm `/erdos-list`, `/erdos-setup` and the `erdos` skill appear. (If running headless, instead validate with the `plugin-validator` agent and note the manual install step for the user.)

- [ ] **Step 3: Final CI**

Run: `make ci`
Expected: PASS.

- [ ] **Step 4: Push branch + open PR on the fork**

```bash
git push -u origin feat/erdos-plugin-and-central-data
gh pr create --repo research-developer/erdos-banger --base main --head feat/erdos-plugin-and-central-data \
  --title "Erdős plugin + centralized ~/.erdos data home" \
  --body "$(cat <<'EOF'
## Summary
- Centralize all data resolution on a `data_home()` (`$ERDOS_HOME` → repo → `~/.erdos`).
- Relocate the Lean project to research-developer/erdos-lean (history-preserving subtree split), cloned to `~/.erdos/formal/lean`; resolve via `ERDOS_LEAN_PROJECT`.
- Package the repo as a Claude Code plugin (`.claude-plugin/`, `commands/`, `skills/`).
- Global CLI via `uv tool install`; idempotent `/erdos-setup` bootstrap; sync into `~/.erdos`.

## Test plan
- `make ci` green; new path-centralization + lean-resolution unit tests.
- `erdos list/show/search` and `erdos lean check` verified from an unrelated cwd.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: PR opened against `research-developer/erdos-banger`.

---

## Self-Review (completed by plan author)

- **Spec coverage:** D1 data home → Task 1.1; relative-path stragglers → 1.2; D5 Lean relocate/subtree/erdos-lean → 2.1–2.3 + lean resolution 1.3; D2 plugin → 3.1–3.4; D3 global CLI → 4.1–4.2; D4 run sync → 4.3; D6 toolchain global+math → 4.1/4.2/4.4; D7 fork-first/branch → 0.1. Subprocess env propagation (spec §5) → 1.3. Migration of literature manifests (spec §1) → 4.1 script.
- **Placeholder scan:** none — every code step shows code; ops steps show commands + expected output. The one explicit judgment call (SearchIndex path attribute name) is flagged with the exact requirement and how to confirm it.
- **Type/name consistency:** `data_home`, `repo_path`, `resolve_repo_root`, `get_default_lean_project_path`, `initialize_environment` used consistently across Tasks 1.1–1.4 and 4.x.
