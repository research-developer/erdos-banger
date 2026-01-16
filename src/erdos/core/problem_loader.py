"""Load and parse problems from the erdosproblems dataset."""

from __future__ import annotations

import os
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry


if TYPE_CHECKING:
    from collections.abc import Iterator


class ProblemLoaderError(Exception):
    """Raised when problem loading fails."""


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
    def from_default(cls) -> ProblemLoader:
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
        env_path = os.environ.get("ERDOS_DATA_PATH")
        if env_path:
            env_dir = Path(env_path)
            for filename in ("problems_enriched.yaml", "problems.yaml"):
                yaml_path = env_dir / filename
                if yaml_path.exists():
                    return cls(yaml_path)

        enriched_path = Path("data/problems_enriched.yaml")
        if enriched_path.exists():
            return cls(enriched_path)

        relative_path = Path("data/erdosproblems/data/problems.yaml")
        if relative_path.exists():
            return cls(relative_path)

        try:
            pkg_files = files("erdos")
            pkg_data = pkg_files.joinpath("data", "problems_enriched.yaml")
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

    def _load_raw(self) -> list[dict[str, Any]]:
        """Load raw YAML data."""
        try:
            with self._yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ProblemLoaderError(f"Failed to parse YAML: {e}") from e

        if not isinstance(data, list):
            raise ProblemLoaderError(
                f"Expected list of problems, got {type(data).__name__}"
            )

        raw: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                raise ProblemLoaderError(
                    f"Expected each problem to be a mapping, got {type(item).__name__}"
                )
            raw.append(item)
        return raw

    def _parse_problem(self, raw: dict[str, Any]) -> ProblemRecord:
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

        status = ProblemStatus.from_string(str(raw.get("status", "open")))

        raw_refs = raw.get("references", [])
        references: list[ReferenceEntry] = []
        if raw_refs is None:
            raw_refs = []
        if not isinstance(raw_refs, list):
            raise ProblemLoaderError("Field 'references' must be a list")
        for ref in raw_refs:
            if not isinstance(ref, dict):
                raise ProblemLoaderError("Each reference must be a mapping")
            references.append(
                ReferenceEntry(
                    key=str(ref.get("key", "unknown")),
                    citation=ref.get("citation"),
                    doi=ref.get("doi"),
                    arxiv_id=ref.get("arxiv_id"),
                    url=ref.get("url"),
                )
            )

        return ProblemRecord(
            id=int(raw["id"]),
            title=str(raw["title"]),
            statement=str(raw["statement"]),
            status=status,
            prize=int(raw.get("prize", 0) or 0),
            tags=list(raw.get("tags", []) or []),
            references=references,
            oeis_ids=list(raw.get("oeis_ids", []) or []),
            notes=raw.get("notes"),
            formalized=bool(raw.get("formalized", False)),
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
            except (ProblemLoaderError, KeyError, TypeError, ValidationError) as e:
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

        if self._cache is None:
            return None
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
        results: list[ProblemRecord] = []

        for problem in problems:
            if status is not None and problem.status != status:
                continue

            if prize_min is not None and problem.prize < prize_min:
                continue
            if prize_max is not None and problem.prize > prize_max:
                continue

            if tags is not None:
                tag_set = {t.lower() for t in tags}
                problem_tags = {t.lower() for t in problem.tags}
                if not tag_set.intersection(problem_tags):
                    continue

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
