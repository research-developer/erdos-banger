"""Unit tests for lean_copilot.server module (SPEC-033).

Tests:
- Tactic parsing from LLM responses
- Request/response models
- LLM execution and error handling
- generate_tactics function

These tests are offline (no network, no actual LLM calls).
"""

from __future__ import annotations

import subprocess
from unittest import mock

import pytest

from erdos.core.llm.router import LLMRouterError
from erdos.lean_copilot.server import (
    GenerateRequest,
    GenerateResponse,
    generate_tactics,
    parse_tactics,
)


class TestParseTactics:
    """Tests for parse_tactics() function."""

    def test_simple_list(self):
        """Parses simple tactic list."""
        response = """rfl
simp
exact h
apply le_of_lt"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h", "apply le_of_lt"]

    def test_strips_whitespace(self):
        """Strips leading/trailing whitespace from each tactic."""
        response = """  rfl
  simp
  exact h  """
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_removes_bullet_points(self):
        """Removes common bullet point prefixes."""
        response = """- rfl
• simp
· exact h
* apply le_of_lt"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h", "apply le_of_lt"]

    def test_skips_empty_lines(self):
        """Skips empty lines."""
        response = """rfl

simp

exact h"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_skips_lean_comments(self):
        """Skips lines starting with Lean comment marker '--'."""
        response = """rfl
-- this is a comment
simp
-- another comment
exact h"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_skips_python_comments(self):
        """Skips lines starting with '#'."""
        response = """rfl
# this is a comment
simp"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp"]

    def test_removes_trailing_punctuation(self):
        """Removes trailing punctuation from tactics."""
        response = """rfl.
simp,
exact h;
apply le_of_lt:"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h", "apply le_of_lt"]

    def test_removes_markdown_backticks(self):
        """Removes markdown code backticks from tactics."""
        response = """`rfl`
`simp`
exact h"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_deduplicates_tactics(self):
        """Removes duplicate tactics, preserving order."""
        response = """rfl
simp
rfl
exact h
simp"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_skips_explanation_lines(self):
        """Skips lines that look like explanations."""
        response = """rfl
This tactic simplifies the goal
simp
We can use this to apply the hypothesis
exact h"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_skips_note_lines(self):
        """Skips lines starting with 'Note:' or 'Explanation:'."""
        response = """rfl
Note: This is a simple tactic
simp
Explanation: This tactic works because...
exact h"""
        result = parse_tactics(response)
        assert result == ["rfl", "simp", "exact h"]

    def test_empty_response(self):
        """Returns empty list for empty response."""
        result = parse_tactics("")
        assert result == []

    def test_whitespace_only_response(self):
        """Returns empty list for whitespace-only response."""
        result = parse_tactics("   \n\n   ")
        assert result == []

    def test_preserves_complex_tactics(self):
        """Preserves complex tactic applications."""
        response = """induction n with
| zero => rfl
| succ n ih => simp [ih]"""
        result = parse_tactics(response)
        assert result == [
            "induction n with",
            "| zero => rfl",
            "| succ n ih => simp [ih]",
        ]

    def test_handles_tactics_with_arguments(self):
        """Handles tactics with arguments correctly."""
        response = """apply Nat.le_of_lt
exact Finset.card_mono h
simp only [add_comm, mul_comm]"""
        result = parse_tactics(response)
        assert result == [
            "apply Nat.le_of_lt",
            "exact Finset.card_mono h",
            "simp only [add_comm, mul_comm]",
        ]


class TestGenerateRequest:
    """Tests for GenerateRequest model."""

    def test_required_prompt(self):
        """Prompt is required."""
        request = GenerateRequest(prompt="goal: 1 + 1 = 2")
        assert request.prompt == "goal: 1 + 1 = 2"

    def test_default_num_samples(self):
        """Default num_samples is 5."""
        request = GenerateRequest(prompt="test")
        assert request.num_samples == 5

    def test_default_temperature(self):
        """Default temperature is 0.2."""
        request = GenerateRequest(prompt="test")
        assert request.temperature == 0.2

    def test_custom_values(self):
        """Can set custom values."""
        request = GenerateRequest(prompt="test", num_samples=10, temperature=0.5)
        assert request.num_samples == 10
        assert request.temperature == 0.5

    def test_num_samples_bounds(self):
        """num_samples must be between 1 and 20."""
        with pytest.raises(ValueError):
            GenerateRequest(prompt="test", num_samples=0)
        with pytest.raises(ValueError):
            GenerateRequest(prompt="test", num_samples=21)

    def test_temperature_bounds(self):
        """temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValueError):
            GenerateRequest(prompt="test", temperature=-0.1)
        with pytest.raises(ValueError):
            GenerateRequest(prompt="test", temperature=2.1)


class TestGenerateResponse:
    """Tests for GenerateResponse model."""

    def test_default_empty_tactics(self):
        """Default tactics is empty list."""
        response = GenerateResponse()
        assert response.tactics == []

    def test_with_tactics(self):
        """Can set tactics list."""
        response = GenerateResponse(tactics=["rfl", "simp", "exact h"])
        assert response.tactics == ["rfl", "simp", "exact h"]


class TestGenerateTactics:
    """Tests for generate_tactics() function."""

    def test_uses_router_for_command(self, monkeypatch: pytest.MonkeyPatch):
        """Uses SPEC-032 router to resolve command."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "echo 'rfl'")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.return_value = ("rfl\nsimp", 0)
            result = generate_tactics("goal: 1 + 1 = 2")

        assert result == ["rfl", "simp"]
        mock_exec.assert_called_once()
        # Check that the command was resolved correctly
        call_args = mock_exec.call_args
        assert call_args[0][0] == "echo 'rfl'"

    def test_uses_override_when_provided(self, monkeypatch: pytest.MonkeyPatch):
        """Uses override command when provided."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "echo 'from-env'")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.return_value = ("rfl\nsimp", 0)
            result = generate_tactics("goal: 1 + 1 = 2", llm_command="echo 'override'")

        assert result == ["rfl", "simp"]
        call_args = mock_exec.call_args
        assert call_args[0][0] == "echo 'override'"

    def test_limits_to_num_samples(self, monkeypatch: pytest.MonkeyPatch):
        """Returns at most num_samples tactics."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "echo 'test'")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.return_value = ("rfl\nsimp\nexact h\napply le_of_lt\nnorm_num", 0)
            result = generate_tactics("test", num_samples=3)

        assert result == ["rfl", "simp", "exact h"]

    def test_returns_empty_on_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch):
        """Returns empty list when LLM exits with non-zero code."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "echo 'test'")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.return_value = ("rfl\nsimp", 1)
            result = generate_tactics("test")

        assert result == []

    def test_raises_when_no_command_configured(self, monkeypatch: pytest.MonkeyPatch):
        """Raises LLMRouterError when no command is configured."""
        monkeypatch.delenv("ERDOS_LLM_COMMAND", raising=False)
        monkeypatch.delenv("ERDOS_LLM_COMMAND_COPILOT", raising=False)
        monkeypatch.delenv("ERDOS_LLM_COMMAND_MATH", raising=False)

        with pytest.raises(LLMRouterError):
            generate_tactics("test")

    def test_propagates_file_not_found(self, monkeypatch: pytest.MonkeyPatch):
        """Propagates FileNotFoundError from LLM execution."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "/nonexistent/command")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("Command not found")
            with pytest.raises(FileNotFoundError):
                generate_tactics("test")

    def test_propagates_timeout(self, monkeypatch: pytest.MonkeyPatch):
        """Propagates TimeoutExpired from LLM execution."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "sleep 999")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.side_effect = subprocess.TimeoutExpired("sleep", 10)
            with pytest.raises(subprocess.TimeoutExpired):
                generate_tactics("test")

    def test_prompt_template_includes_proof_state(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Prompt template includes the proof state."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "echo 'rfl'")

        with mock.patch("erdos.lean_copilot.server.execute_llm_sync") as mock_exec:
            mock_exec.return_value = ("rfl", 0)
            generate_tactics("goal: 1 + 1 = 2")

        call_args = mock_exec.call_args
        prompt = call_args[0][1]
        assert "goal: 1 + 1 = 2" in prompt
        assert "Lean 4" in prompt  # From prompt template
