"""Tests for Lean runner integration.

These tests require Lean to be installed and are skipped otherwise.
"""

import shutil

import pytest


pytestmark = pytest.mark.requires_lean


def lean_available() -> bool:
    """Check if Lean toolchain is available."""
    return shutil.which("lake") is not None


@pytest.mark.skipif(not lean_available(), reason="Lean toolchain not installed")
def test_lean_toolchain_available():
    """Verify Lean toolchain is accessible when marker is used."""
    assert lean_available(), "Lean toolchain should be available"
