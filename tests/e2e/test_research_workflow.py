"""End-to-end tests for research workspace persistence."""

from __future__ import annotations

import json

import pytest


@pytest.mark.e2e
class TestResearchWorkflow:
    """E2E tests for research workspace commands across invocations."""

    def test_research_init_creates_workspace(self, cli_runner) -> None:
        """erdos research init creates workspace directory."""
        result = cli_runner("--json", "research", "init", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos research init"
        assert data["data"]["problem_id"] == 6
        assert data["data"]["created"] is True
        assert len(data["data"]["created_paths"]) > 0

    def test_research_init_idempotent(self, cli_runner) -> None:
        """erdos research init is idempotent (can run twice)."""
        # First init
        cli_runner("--json", "research", "init", "6")

        # Second init should succeed (idempotent)
        result = cli_runner("--json", "research", "init", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        # Second run should create=False since already exists
        assert data["data"]["created"] is False

    def test_research_status_shows_workspace(self, cli_runner) -> None:
        """erdos research status shows workspace state."""
        # Init first
        cli_runner("--json", "research", "init", "6")

        # Check status
        result = cli_runner("--json", "research", "status", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos research status"
        assert data["data"]["problem_id"] == 6
        assert "counts" in data["data"]

    def test_research_note_appends_to_scratchpad(self, cli_runner) -> None:
        """erdos research note appends to SCRATCHPAD.md."""
        # Init first
        cli_runner("--json", "research", "init", "6")

        # Add a note
        result = cli_runner("--json", "research", "note", "6", "This is a test note.")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos research note"

    def test_research_synthesize_runs(self, cli_runner) -> None:
        """erdos research synthesize generates SYNTHESIS.md."""
        # Init first
        cli_runner("--json", "research", "init", "6")

        # Run synthesize
        result = cli_runner("--json", "research", "synthesize", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos research synthesize"

    def test_research_workflow_persists_across_invocations(self, cli_runner) -> None:
        """Research workspace state persists across process invocations."""
        # Init workspace
        cli_runner("--json", "research", "init", "6")

        # Add notes in separate invocations
        cli_runner("--json", "research", "note", "6", "First note")
        cli_runner("--json", "research", "note", "6", "Second note")

        # Status should still work (workspace persisted)
        result = cli_runner("--json", "research", "status", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["files"]["scratchpad"] is True

    def test_research_status_not_found(self, cli_runner) -> None:
        """erdos research status returns error for uninitialized problem."""
        # Don't init - try status directly on a different problem
        result = cli_runner("--json", "research", "status", "99999", check=False)

        # Should fail gracefully
        data = json.loads(result.stdout)
        assert data["success"] is False
