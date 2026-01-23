from __future__ import annotations

import pytest

from erdos.core.research.errors import ResearchRecordInvalidError
from erdos.core.research.store_fs import (
    fmt_problem_workspace,
    validate_problem_workspace,
)
from erdos.core.research.workspace import ensure_problem_workspace


def test_validate_problem_workspace_catches_invalid_record(tmp_path) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    bad = tmp_path / "research" / "problems" / "0006" / "leads" / "lead_bad.yaml"
    bad.write_text("schema_version: 1\nproblem_id: 6\nid: lead_bad\n", encoding="utf-8")
    with pytest.raises(ResearchRecordInvalidError):
        validate_problem_workspace(6, repo_root=tmp_path)


def test_fmt_is_idempotent(tmp_path) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    lead_path = (
        tmp_path
        / "research"
        / "problems"
        / "0006"
        / "leads"
        / "lead_20260123T000501Z_a1b2c3.yaml"
    )
    lead_path.write_text(
        "\n".join(
            [
                "problem_id: 6",
                "schema_version: 1",
                "id: lead_20260123T000501Z_a1b2c3",
                "title: Test",
                "status: new",
                "priority: medium",
                "tags: []",
                "source: {doi: null, arxiv_id: null, url: null}",
                "notes: ''",
                "created_at: '2026-01-23T00:05:01Z'",
                "updated_at: '2026-01-23T00:05:01Z'",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rewritten = fmt_problem_workspace(6, repo_root=tmp_path)
    assert rewritten == 1
    rewritten_again = fmt_problem_workspace(6, repo_root=tmp_path)
    assert rewritten_again == 0
