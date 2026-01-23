from __future__ import annotations

from erdos.core.loop.result import LoopStatus
from erdos.core.research.loop_integration import _map_result
from erdos.core.research.models import AttemptResult


def test_map_result_success() -> None:
    assert _map_result(LoopStatus.SUCCESS) == AttemptResult.SUCCESS


def test_map_result_max_iterations_is_partial() -> None:
    assert _map_result(LoopStatus.MAX_ITERATIONS) == AttemptResult.PARTIAL


def test_map_result_error_is_failed() -> None:
    assert _map_result(LoopStatus.ERROR) == AttemptResult.FAILED
