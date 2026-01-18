"""Integration test: validate upstream erdosproblems metadata schema."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.slow
def test_upstream_metadata_yaml_schema_smoke() -> None:
    """
    Smoke-test the upstream `teorth/erdosproblems` metadata-only YAML.

    This does NOT assert compatibility with the enriched v1 schema (ProblemRecord).
    It exists to catch upstream structural changes early.
    """
    upstream = Path("data/erdosproblems/data/problems.yaml")
    if not upstream.exists():
        pytest.skip("Upstream submodule not present (data/erdosproblems)")

    data = yaml.safe_load(upstream.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 100

    first = data[0]
    assert isinstance(first, dict)
    assert "number" in first
    assert "status" in first
    assert isinstance(first["status"], dict)
    assert "state" in first["status"]
