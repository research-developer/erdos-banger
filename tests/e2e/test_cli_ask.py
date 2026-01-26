"""End-to-end tests for erdos ask command."""

from __future__ import annotations

import json

import pytest


@pytest.mark.e2e
class TestErdosAsk:
    """E2E tests for erdos ask --no-llm (no paid API required)."""

    def test_ask_no_llm_json_output(self, cli_runner) -> None:
        """erdos --json ask --no-llm returns valid JSON."""
        result = cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos ask"

    def test_ask_no_llm_answer_is_null(self, cli_runner) -> None:
        """erdos ask --no-llm returns null answer (no LLM invocation)."""
        result = cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        data = json.loads(result.stdout)
        assert data["data"]["answer"] is None
        assert data["data"]["llm"]["enabled"] is False

    def test_ask_no_llm_has_sources(self, cli_runner) -> None:
        """erdos ask --no-llm still retrieves sources."""
        result = cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        data = json.loads(result.stdout)
        sources = data["data"]["sources"]
        assert isinstance(sources, list)
        # Problem statement is always available as a source
        assert len(sources) >= 1

    def test_ask_no_llm_sources_have_schema_keys(self, cli_runner) -> None:
        """erdos ask sources have expected schema keys."""
        result = cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        data = json.loads(result.stdout)
        for source in data["data"]["sources"]:
            assert "chunk_id" in source
            assert "source_type" in source
            assert "text" in source

    def test_ask_not_found(self, cli_runner) -> None:
        """erdos ask returns error for missing problem."""
        result = cli_runner(
            "--json", "ask", "99999", "question", "--no-llm", check=False
        )

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "NotFoundError"
        assert data["error"]["code"] == 3

    def test_ask_exit_code_zero(self, cli_runner) -> None:
        """erdos ask --no-llm returns exit code 0 on success."""
        result = cli_runner("ask", "6", "What is known?", "--no-llm")
        assert result.returncode == 0
