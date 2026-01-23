from __future__ import annotations

from pathlib import Path

import pytest

from erdos.core.research.errors import ResearchRecordInvalidError
from erdos.core.research.models import HypothesisStatus, LeadStatus, TaskStatus
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.workspace import ensure_problem_workspace


@pytest.mark.parametrize(
    "lead_id",
    [
        "../evil",
        "..\\evil",
        "foo/../bar",
        ".",
        "..",
        "/etc/passwd",
        "",
        "lead_20260123T000000Z_000000/../../../etc/passwd",
        "lead_20260123T000000Z_000000\\..\\evil",
    ],
)
def test_lead_update_rejects_malicious_ids(tmp_path: Path, lead_id: str) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    store = FSResearchStore(repo_root=tmp_path)
    with pytest.raises(ResearchRecordInvalidError):
        store.lead_update(6, lead_id, status=LeadStatus.NEW)


@pytest.mark.parametrize(
    "hyp_id",
    [
        "../evil",
        "..\\evil",
        "foo/../bar",
        ".",
        "..",
        "/etc/passwd",
        "",
        "hyp_20260123T000000Z_000000/../../../etc/passwd",
        "hyp_20260123T000000Z_000000\\..\\evil",
    ],
)
def test_hypothesis_update_rejects_malicious_ids(tmp_path: Path, hyp_id: str) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    store = FSResearchStore(repo_root=tmp_path)
    with pytest.raises(ResearchRecordInvalidError):
        store.hypothesis_update(6, hyp_id, status=HypothesisStatus.ACTIVE)


@pytest.mark.parametrize(
    "task_id",
    [
        "../evil",
        "..\\evil",
        "foo/../bar",
        ".",
        "..",
        "/etc/passwd",
        "",
        "task_20260123T000000Z_000000/../../../etc/passwd",
        "task_20260123T000000Z_000000\\..\\evil",
    ],
)
def test_task_update_rejects_malicious_ids(tmp_path: Path, task_id: str) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    store = FSResearchStore(repo_root=tmp_path)
    with pytest.raises(ResearchRecordInvalidError):
        store.task_update(6, task_id, status=TaskStatus.TODO)
