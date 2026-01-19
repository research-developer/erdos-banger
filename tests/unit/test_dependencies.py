"""Tests for project dependency configuration."""

import re
import tomllib
from pathlib import Path

import requests


def test_requests_is_installed() -> None:
    """Verify requests library is installed and importable.

    This test ensures BUG-007 is fixed: requests must be in pyproject.toml
    dependencies, not just types-requests in dev dependencies.

    Relates to:
    - src/erdos/core/ingest.py (imports requests)
    - src/erdos/core/arxiv_client.py (imports requests)
    - src/erdos/core/crossref_client.py (imports requests)
    """
    # If we got here, requests imported successfully at module level
    assert requests is not None


def test_requests_version_meets_spec() -> None:
    """Verify requests version meets SPEC-010 requirement (>=2.32.5).

    SPEC-010 Section 5.0 requires requests>=2.32.5 for security fixes.
    """
    # Parse version, handling pre-release/post-release suffixes
    # e.g., "2.32.5" or "2.32.5.post1" or "2.32.5rc1" -> (2, 32, 5)
    version_str = requests.__version__
    # Extract numeric parts using regex (handles suffixes like .post1, rc1, etc.)
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
    assert match, f"Could not parse version string: {version_str}"
    version_parts = tuple(int(x) for x in match.groups())
    required = (2, 32, 5)

    assert version_parts >= required, (
        f"requests version {version_str} is below required "
        f"{'.'.join(map(str, required))}"
    )


def test_pyproject_toml_has_requests_dependency() -> None:
    """Verify pyproject.toml explicitly lists requests in dependencies.

    This prevents regression of BUG-007 where requests was imported but
    not declared as a dependency.
    """
    # Read pyproject.toml from project root
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    assert isinstance(dependencies, list)
    found_requests = any(
        isinstance(dep, str) and dep.lstrip().startswith("requests")
        for dep in dependencies
    )

    assert found_requests, (
        "requests>=2.32.5 must be in [project] dependencies section "
        "of pyproject.toml (not just in dev dependencies)"
    )
