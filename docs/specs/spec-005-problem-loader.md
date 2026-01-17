# Spec 005: Problem Loader & YAML Parsing

> Defines how erdos-banger loads problem data from the teorth/erdosproblems dataset.

---

## Overview

The Problem Loader is the foundation of the data pipeline. For v1, it reads an **enriched** problems YAML (default `data/problems_enriched.yaml`) and transforms it into validated `ProblemRecord` objects. The upstream `teorth/erdosproblems` `data/problems.yaml` is metadata-only and is used as SSOT for metadata and as an input to enrichment.

### Guiding Principles

1. **Upstream SSOT (metadata)** - Upstream YAML is SSOT for metadata; titles/statements come from enrichment
2. **Validation at the boundary** - Parse once, validate once, use everywhere
3. **Lazy loading** - Don't load all 1135 problems unless needed
4. **Cacheable** - Parsed data can be cached to avoid re-parsing

---

## 1) Data Source: teorth/erdosproblems

The canonical data lives in Terence Tao's repository:
- **Repository:** `https://github.com/teorth/erdosproblems`
- **License:** Apache-2.0
- **Main file:** `data/problems.yaml`

### Integration Strategy

We use a git submodule to track a specific commit:

```bash
# Add submodule (one-time setup)
git submodule add https://github.com/teorth/erdosproblems.git data/erdosproblems

# Update to latest
git submodule update --remote data/erdosproblems
```

**Directory structure:**
```
erdos-banger/
├── data/
│   └── erdosproblems/          # Git submodule
│       ├── data/
│       │   └── problems.yaml   # The source of truth
│       ├── CONTRIBUTING.md
│       └── LICENSE
```

---

## 2) YAML Schema

### Upstream Format (teorth/erdosproblems)

**Important:** The upstream repository contains **metadata only**, not full problem statements. The actual format is:

```yaml
- number: "6"
  prize: "$100"
  status:
    state: "proved"
    last_update: "2025-08-31"
  oeis: ["A335277"]
  formalized:
    state: "yes"
    last_update: "2025-09-18"
  tags:
    - number theory
    - primes
```

### Upstream Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `number` | str | Yes | Problem identifier (string, not int) |
| `prize` | str | No | Prize amount as string ("$500", "£25", "no") |
| `status.state` | str | No | Free-form status label; common values include open, proved, disproved, solved, verifiable, falsifiable, decidable, independent, not provable, and variants like "proved (Lean)" |
| `status.last_update` | str | No | ISO date of last status update |
| `oeis` | list[str] | No | OEIS sequence IDs or ["N/A"] |
| `formalized.state` | str | No | "yes" or "no" |
| `formalized.last_update` | str | No | ISO date |
| `tags` | list[str] | No | Topic tags |
| `comments` | str | No | Brief notes |

### Enriched Format (erdos-banger)

Since the upstream YAML lacks titles and statements, erdos-banger uses an **enriched format** for local development and testing. Problem statements must be sourced separately (see Section 3).

```yaml
- id: 6
  title: "Small primes in arithmetic progressions"
  statement: |
    Let $p_1 < p_2 < \ldots$ be the sequence of primes.
    Prove that for every $k$, there exist infinitely many
    arithmetic progressions of length $k$ consisting of primes.
  status: proved
  prize: 100
  tags:
    - number theory
    - primes
  references:
    - key: GreenTao2008
      citation: "B. Green, T. Tao, The primes contain arbitrarily long arithmetic progressions"
      doi: "10.4007/annals.2008.167.481"
      arxiv_id: "math/0404188"
  notes: "Solved by Green and Tao in 2008."
  oeis_ids:
    - A000040
  formalized: true
```

### Enriched Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | int | Yes | Unique problem ID (converted from upstream `number`) |
| `title` | str | Yes | Short descriptive title (sourced separately) |
| `statement` | str | Yes | Full problem statement with LaTeX (sourced separately) |
| `status` | str | Yes | One of: open, proved, disproved, partially_solved |
| `prize` | int | No | Prize amount in USD (parsed from upstream string) |
| `tags` | list[str] | No | Topic tags (default: []) |
| `references` | list[dict] | No | Bibliography entries (default: []) |
| `notes` | str | No | Additional notes (from upstream `comments`) |
| `oeis_ids` | list[str] | No | Related OEIS sequence IDs |
| `formalized` | bool | No | Has Lean formalization (parsed from upstream) |

### Data Sourcing Strategy

The upstream teorth/erdosproblems repo provides metadata only. For full problem data, erdos-banger supports multiple strategies:

1. **Enriched Local YAML** (default for v1): Maintain a local `data/problems_enriched.yaml` with manually curated titles and statements. This is the simplest approach for initial development.

2. **Upstream Metadata + Scraping** (future): Parse metadata from upstream, then fetch statements from erdosproblems.com.

3. **Hybrid Merging** (future): Merge upstream metadata with local enrichments, keeping them in sync.

For v1, the ProblemLoader expects the **enriched format** with `id`, `title`, and `statement` fields. Test fixtures (Spec 008) use this enriched format.

---

## 3) Problem Loader Implementation

```python
# src/erdos/core/problem_loader.py
"""Load and parse problems from the erdosproblems dataset."""

from pathlib import Path
from typing import Iterator

import yaml
from pydantic import ValidationError

from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry


class ProblemLoaderError(Exception):
    """Raised when problem loading fails."""

    pass


class ProblemLoader:
    """
    Loads problems from the erdosproblems YAML file.

    Usage:
        loader = ProblemLoader.from_default()
        problems = loader.load_all()
        problem = loader.get_by_id(6)
    """

    def __init__(self, yaml_path: Path) -> None:
        """
        Initialize loader with path to problems.yaml.

        Args:
            yaml_path: Path to the problems.yaml file

        Raises:
            ProblemLoaderError: If file doesn't exist
        """
        if not yaml_path.exists():
            raise ProblemLoaderError(f"Problems file not found: {yaml_path}")
        if not yaml_path.is_file():
            raise ProblemLoaderError(f"Not a file: {yaml_path}")

        self._yaml_path = yaml_path
        self._cache: dict[int, ProblemRecord] | None = None

    @classmethod
    def from_default(cls) -> "ProblemLoader":
        """
        Create loader using default data path.

        Looks for a problems YAML in these locations (in order):
        1. ERDOS_DATA_PATH environment variable
        2. ./data/problems_enriched.yaml (relative to cwd; v1 default)
        3. ./data/erdosproblems/data/problems.yaml (upstream metadata-only)
        4. Package data directory

        Returns:
            ProblemLoader instance

        Raises:
            ProblemLoaderError: If no valid path found
        """
        import os

        # Check environment variable first
        env_path = os.environ.get("ERDOS_DATA_PATH")
        if env_path:
            env_dir = Path(env_path)
            for filename in ("problems_enriched.yaml", "problems.yaml"):
                yaml_path = env_dir / filename
                if yaml_path.exists():
                    return cls(yaml_path)

        # v1 default: local enriched dataset
        enriched_path = Path("data/problems_enriched.yaml")
        if enriched_path.exists():
            return cls(enriched_path)

        # Check relative path (for development)
        relative_path = Path("data/erdosproblems/data/problems.yaml")
        if relative_path.exists():
            return cls(relative_path)

        # Check package data (for installed package)
        try:
            from importlib.resources import as_file, files

            pkg_files = files("erdos")
            pkg_data = pkg_files.joinpath("data", "problems_enriched.yaml")
            # as_file() extracts resource to a real filesystem path
            with as_file(pkg_data) as real_path:
                if real_path.exists():
                    return cls(real_path)
        except (ImportError, TypeError, AttributeError, FileNotFoundError):
            pass

        raise ProblemLoaderError(
            "Could not find problems YAML. Set ERDOS_DATA_PATH or create data/problems_enriched.yaml."
        )

    @property
    def yaml_path(self) -> Path:
        """Path to the problems.yaml file."""
        return self._yaml_path

    def _load_raw(self) -> list[dict]:
        """Load raw YAML data."""
        with open(self._yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise ProblemLoaderError(
                f"Expected list of problems, got {type(data).__name__}"
            )

        return data

    def _parse_problem(self, raw: dict) -> ProblemRecord:
        """
        Parse a single problem from raw YAML dict.

        Handles field name normalization and validation.
        """
        if "id" not in raw:
            if "number" in raw:
                raise ProblemLoaderError(
                    "Unsupported upstream teorth/erdosproblems format (metadata-only). "
                    "v1 requires enriched problems with id/title/statement. "
                    "Create data/problems_enriched.yaml (Spec 005) or point ERDOS_DATA_PATH at an enriched problems_enriched.yaml (or problems.yaml)."
                )
            raise ProblemLoaderError("Missing required field 'id' in problem entry")
        if "title" not in raw or "statement" not in raw:
            raise ProblemLoaderError(
                "Missing required enriched fields 'title'/'statement'. "
                "Create data/problems_enriched.yaml (Spec 005) or point ERDOS_DATA_PATH at an enriched problems_enriched.yaml (or problems.yaml)."
            )

        # Normalize status string (handles legacy/variant values)
        status = ProblemStatus.from_string(raw.get("status", "open"))

        # Parse references
        raw_refs = raw.get("references", [])
        references = []
        for ref in raw_refs:
            references.append(
                ReferenceEntry(
                    key=ref.get("key", "unknown"),
                    citation=ref.get("citation"),
                    doi=ref.get("doi"),
                    arxiv_id=ref.get("arxiv_id"),
                    url=ref.get("url"),
                )
            )

        return ProblemRecord(
            id=raw["id"],
            title=raw["title"],
            statement=raw["statement"],
            status=status,
            prize=raw.get("prize", 0),
            tags=raw.get("tags", []),
            references=references,
            oeis_ids=raw.get("oeis_ids", []),
            notes=raw.get("notes"),
            formalized=raw.get("formalized", False),
        )

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]:
        """
        Load all problems from the YAML file.

        Args:
            use_cache: If True, return cached results on subsequent calls

        Returns:
            List of all ProblemRecord objects

        Raises:
            ProblemLoaderError: If parsing fails
        """
        if use_cache and self._cache is not None:
            return list(self._cache.values())

        raw_problems = self._load_raw()
        problems: dict[int, ProblemRecord] = {}
        errors: list[str] = []

        for i, raw in enumerate(raw_problems):
            try:
                problem = self._parse_problem(raw)
                problems[problem.id] = problem
            except (KeyError, ValidationError) as e:
                errors.append(f"Problem at index {i}: {e}")

        if errors:
            raise ProblemLoaderError(
                f"Failed to parse {len(errors)} problems:\n" + "\n".join(errors[:5])
            )

        self._cache = problems
        return list(problems.values())

    def iter_problems(self) -> Iterator[ProblemRecord]:
        """
        Iterate over problems lazily.

        Yields:
            ProblemRecord objects one at a time
        """
        raw_problems = self._load_raw()
        for raw in raw_problems:
            yield self._parse_problem(raw)

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        """
        Get a specific problem by ID.

        Args:
            problem_id: The problem ID to look up

        Returns:
            ProblemRecord if found, None otherwise
        """
        if self._cache is None:
            self.load_all()

        return self._cache.get(problem_id)

    def filter(
        self,
        *,
        status: ProblemStatus | None = None,
        prize_min: int | None = None,
        prize_max: int | None = None,
        tags: list[str] | None = None,
        formalized: bool | None = None,
    ) -> list[ProblemRecord]:
        """
        Filter problems by criteria.

        Args:
            status: Filter by problem status
            prize_min: Minimum prize amount
            prize_max: Maximum prize amount
            tags: Filter by tags (matches if problem has ANY of these tags)
            formalized: Filter by formalization status

        Returns:
            List of matching ProblemRecord objects
        """
        problems = self.load_all()
        results = []

        for problem in problems:
            # Status filter
            if status is not None and problem.status != status:
                continue

            # Prize filters
            if prize_min is not None and problem.prize < prize_min:
                continue
            if prize_max is not None and problem.prize > prize_max:
                continue

            # Tags filter (match any)
            if tags is not None:
                tag_set = set(t.lower() for t in tags)
                problem_tags = set(t.lower() for t in problem.tags)
                if not tag_set.intersection(problem_tags):
                    continue

            # Formalized filter
            if formalized is not None and problem.formalized != formalized:
                continue

            results.append(problem)

        return results

    def count(self) -> int:
        """Return total number of problems."""
        return len(self.load_all())

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache = None
```

---

## 4) Configuration

The loader respects these configuration options:

```yaml
# erdos.yaml (config file)
data:
  problems_path: "data/erdosproblems/data/problems.yaml"
  cache_parsed: true
```

**Environment variable:** `ERDOS_DATA_PATH` overrides the config.

---

## 5) Error Handling

```python
class ProblemLoaderError(Exception):
    """Base exception for loader errors."""

    pass


# Specific error cases:
# - File not found → ProblemLoaderError("Problems file not found: ...")
# - Invalid YAML → ProblemLoaderError("Failed to parse YAML: ...")
# - Validation error → ProblemLoaderError("Failed to parse N problems: ...")
# - Missing required field → Includes field name and problem index
```

---

## 6) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_problem_loader.py
"""Unit tests for ProblemLoader."""

from pathlib import Path

import pytest

from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


class TestProblemLoaderInit:
    def test_raises_if_file_not_found(self, tmp_path: Path) -> None:
        """Loader raises if YAML file doesn't exist."""
        with pytest.raises(ProblemLoaderError, match="not found"):
            ProblemLoader(tmp_path / "nonexistent.yaml")

    def test_raises_if_path_is_directory(self, tmp_path: Path) -> None:
        """Loader raises if path is a directory."""
        with pytest.raises(ProblemLoaderError, match="Not a file"):
            ProblemLoader(tmp_path)


class TestProblemLoaderLoadAll:
    def test_loads_valid_yaml(self, sample_problems_yaml: Path) -> None:
        """Loader successfully parses valid YAML."""
        loader = ProblemLoader(sample_problems_yaml)
        problems = loader.load_all()

        assert len(problems) > 0
        assert all(isinstance(p, ProblemRecord) for p in problems)

    def test_caches_results(self, sample_problems_yaml: Path) -> None:
        """Subsequent calls return cached results."""
        loader = ProblemLoader(sample_problems_yaml)
        first = loader.load_all()
        second = loader.load_all()

        assert first == second  # Same objects due to caching

    def test_cache_can_be_cleared(self, sample_problems_yaml: Path) -> None:
        """clear_cache() forces reload."""
        loader = ProblemLoader(sample_problems_yaml)
        loader.load_all()
        loader.clear_cache()

        # After clearing, cache should be None
        assert loader._cache is None


class TestProblemLoaderGetById:
    def test_returns_problem_when_found(self, sample_problems_yaml: Path) -> None:
        """get_by_id returns correct problem."""
        loader = ProblemLoader(sample_problems_yaml)
        problem = loader.get_by_id(6)

        assert problem is not None
        assert problem.id == 6

    def test_returns_none_when_not_found(self, sample_problems_yaml: Path) -> None:
        """get_by_id returns None for nonexistent ID."""
        loader = ProblemLoader(sample_problems_yaml)
        problem = loader.get_by_id(99999)

        assert problem is None


class TestProblemLoaderFilter:
    def test_filter_by_status(self, sample_problems_yaml: Path) -> None:
        """Filter by status works."""
        loader = ProblemLoader(sample_problems_yaml)
        open_problems = loader.filter(status=ProblemStatus.OPEN)

        assert all(p.status == ProblemStatus.OPEN for p in open_problems)

    def test_filter_by_prize_min(self, sample_problems_yaml: Path) -> None:
        """Filter by minimum prize works."""
        loader = ProblemLoader(sample_problems_yaml)
        big_prize = loader.filter(prize_min=1000)

        assert all(p.prize >= 1000 for p in big_prize)

    def test_filter_by_tags(self, sample_problems_yaml: Path) -> None:
        """Filter by tags matches any tag."""
        loader = ProblemLoader(sample_problems_yaml)
        number_theory = loader.filter(tags=["number theory"])

        for p in number_theory:
            assert any("number theory" in t.lower() for t in p.tags)

    def test_filter_combined(self, sample_problems_yaml: Path) -> None:
        """Multiple filters combine with AND."""
        loader = ProblemLoader(sample_problems_yaml)
        results = loader.filter(
            status=ProblemStatus.OPEN,
            prize_min=100,
        )

        for p in results:
            assert p.status == ProblemStatus.OPEN
            assert p.prize >= 100


class TestProblemLoaderFromDefault:
    def test_uses_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """from_default() respects ERDOS_DATA_PATH env var."""
        # Create a minimal problems.yaml
        problems_dir = tmp_path / "data"
        problems_dir.mkdir()
        yaml_file = problems_dir / "problems.yaml"
        yaml_file.write_text(
            """
- id: 1
  title: Test Problem
  statement: Prove X
  status: open
"""
        )

        monkeypatch.setenv("ERDOS_DATA_PATH", str(problems_dir))
        loader = ProblemLoader.from_default()

        assert loader.yaml_path == yaml_file


class TestProblemLoaderIterProblems:
    def test_yields_problems_lazily(self, sample_problems_yaml: Path) -> None:
        """iter_problems yields without loading all into memory."""
        loader = ProblemLoader(sample_problems_yaml)

        # Get first problem without loading all
        first = next(loader.iter_problems())

        assert isinstance(first, ProblemRecord)
        # Cache should still be None (didn't call load_all)
        assert loader._cache is None
```

### Integration Tests

```python
# tests/integration/test_problem_loader.py
"""Integration tests for ProblemLoader with real data."""

from pathlib import Path

import pytest

from erdos.core.problem_loader import ProblemLoader


@pytest.fixture
def real_data_loader() -> ProblemLoader | None:
    """Load from actual submodule if available."""
    real_path = Path("data/erdosproblems/data/problems.yaml")
    if real_path.exists():
        return ProblemLoader(real_path)
    pytest.skip("erdosproblems submodule not initialized")


def test_loads_all_real_problems(real_data_loader: ProblemLoader) -> None:
    """Verify we can load the full upstream dataset."""
    problems = real_data_loader.load_all()

    # Should have hundreds of problems
    assert len(problems) > 100

    # All should have valid IDs
    ids = [p.id for p in problems]
    assert len(ids) == len(set(ids))  # No duplicates


def test_specific_known_problem(real_data_loader: ProblemLoader) -> None:
    """Verify a known problem loads correctly."""
    # Problem 6 is well-documented
    problem = real_data_loader.get_by_id(6)

    assert problem is not None
    assert "prime" in problem.title.lower() or "prime" in problem.statement.lower()
```

### Acceptance Criteria

```bash
# 1. Loader can be created
python -c "from erdos.core.problem_loader import ProblemLoader; print('OK')"

# 2. from_default() works in repo root
cd erdos-banger
uv run python -c "
from erdos.core.problem_loader import ProblemLoader
loader = ProblemLoader.from_default()
print(f'Loaded from: {loader.yaml_path}')
print(f'Total problems: {loader.count()}')
"

# 3. Filtering works
uv run python -c "
from erdos.core.problem_loader import ProblemLoader
from erdos.core.models import ProblemStatus
loader = ProblemLoader.from_default()
open_problems = loader.filter(status=ProblemStatus.OPEN)
print(f'Open problems: {len(open_problems)}')
"

# 4. Tests pass
uv run pytest tests/unit/test_problem_loader.py -v
uv run pytest tests/integration/test_problem_loader.py -v
```

---

## 7) References

- [teorth/erdosproblems](https://github.com/teorth/erdosproblems)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [Git Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
