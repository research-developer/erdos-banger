from __future__ import annotations

import pytest

from erdos.core.research.errors import ResearchRecordInvalidError
from erdos.core.research.models import LeadStatus
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.workspace import ensure_problem_workspace


def test_lead_update_rejects_path_traversal(tmp_path) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    store = FSResearchStore(repo_root=tmp_path)
    with pytest.raises(ResearchRecordInvalidError):
        store.lead_update(6, "../evil", status=LeadStatus.NEW)
