"""Minimal passing unit test placeholder."""

def test_unit_placeholder(sample_problem, lean_error_output: str) -> None:
    assert sample_problem.id == 6
    assert "error:" in lean_error_output
