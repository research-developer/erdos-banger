"""Fixtures for unit tests - no I/O, no subprocesses."""

import pytest


@pytest.fixture
def lean_error_output() -> str:
    """Captured Lean error output for parsing tests."""
    return """
Erdos/Problem006.lean:12:5: error: unknown identifier 'Nat.prime'
Erdos/Problem006.lean:15:10: error: type mismatch
  has type
    Nat
  but is expected to have type
    Prop
"""
