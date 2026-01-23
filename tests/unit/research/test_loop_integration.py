from __future__ import annotations

import pytest

from erdos.core.loop.result import LoopStatus
from erdos.core.research.loop_integration import _map_result
from erdos.core.research.models import AttemptResult


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (LoopStatus.SUCCESS, AttemptResult.SUCCESS),
        (LoopStatus.MAX_ITERATIONS, AttemptResult.PARTIAL),
        (LoopStatus.NO_PROGRESS, AttemptResult.FAILED),
        (LoopStatus.NO_FIX_POSSIBLE, AttemptResult.FAILED),
        (LoopStatus.REGRESSION, AttemptResult.FAILED),
        (LoopStatus.LLM_REQUIRED, AttemptResult.FAILED),
        (LoopStatus.ERROR, AttemptResult.FAILED),
    ],
)
def test_map_result_all_statuses(status: LoopStatus, expected: AttemptResult) -> None:
    assert _map_result(status) == expected
