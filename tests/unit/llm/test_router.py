"""Unit tests for LLM command router."""

import pytest

from erdos.core.llm.router import (
    LLMRouterError,
    resolve_llm_command,
)
from erdos.core.llm.tasks import TaskType


class TestResolveLLMCommand:
    """Tests for resolve_llm_command()."""

    def test_global_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to ERDOS_LLM_COMMAND when task-specific not set."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/llm.sh")
        monkeypatch.delenv("ERDOS_LLM_COMMAND_MATH", raising=False)

        result = resolve_llm_command(TaskType.ask_question)
        assert result == "./scripts/llm.sh"

    def test_task_specific_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task-specific env var takes precedence over global."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "./scripts/math.sh")

        result = resolve_llm_command(TaskType.ask_question)
        assert result == "./scripts/math.sh"

    def test_loop_patch_uses_code_command(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """loop_patch uses ERDOS_LLM_COMMAND_CODE."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_CODE", "./scripts/code.sh")

        result = resolve_llm_command(TaskType.loop_patch)
        assert result == "./scripts/code.sh"

    def test_tactic_generation_chain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """tactic_generation checks COPILOT -> MATH -> global."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "./scripts/math.sh")
        # COPILOT not set

        result = resolve_llm_command(TaskType.tactic_generation)
        assert result == "./scripts/math.sh"

    def test_tactic_generation_copilot_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COPILOT takes precedence for tactic_generation."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "./scripts/math.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_COPILOT", "./scripts/copilot.sh")

        result = resolve_llm_command(TaskType.tactic_generation)
        assert result == "./scripts/copilot.sh"

    def test_empty_env_var_is_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string env vars are treated as unset."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "")

        result = resolve_llm_command(TaskType.ask_question)
        assert result == "./scripts/fallback.sh"

    def test_whitespace_only_env_var_is_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Whitespace-only env vars are treated as unset."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "   ")

        result = resolve_llm_command(TaskType.ask_question)
        assert result == "./scripts/fallback.sh"

    def test_raises_when_no_command_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises LLMRouterError when no command is configured."""
        monkeypatch.delenv("ERDOS_LLM_COMMAND", raising=False)
        monkeypatch.delenv("ERDOS_LLM_COMMAND_MATH", raising=False)

        with pytest.raises(LLMRouterError) as exc_info:
            resolve_llm_command(TaskType.ask_question)

        assert "No LLM command configured" in str(exc_info.value)
        assert "ask_question" in str(exc_info.value)

    def test_error_lists_checked_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error message lists which env vars were checked."""
        monkeypatch.delenv("ERDOS_LLM_COMMAND", raising=False)
        monkeypatch.delenv("ERDOS_LLM_COMMAND_MATH", raising=False)

        with pytest.raises(LLMRouterError) as exc_info:
            resolve_llm_command(TaskType.ask_question)

        error_msg = str(exc_info.value)
        assert "ERDOS_LLM_COMMAND_MATH" in error_msg
        assert "ERDOS_LLM_COMMAND" in error_msg


class TestResolveLLMCommandWithOverride:
    """Tests for resolve_llm_command() with explicit override."""

    def test_override_bypasses_routing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit override bypasses all env var lookups."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")
        monkeypatch.setenv("ERDOS_LLM_COMMAND_MATH", "./scripts/math.sh")

        result = resolve_llm_command(
            TaskType.ask_question, override="./scripts/custom.sh"
        )
        assert result == "./scripts/custom.sh"

    def test_override_works_without_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Override works even when no env vars are set."""
        monkeypatch.delenv("ERDOS_LLM_COMMAND", raising=False)
        monkeypatch.delenv("ERDOS_LLM_COMMAND_MATH", raising=False)

        result = resolve_llm_command(
            TaskType.ask_question, override="./scripts/custom.sh"
        )
        assert result == "./scripts/custom.sh"

    def test_empty_override_falls_back_to_routing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty override string falls back to normal routing."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")

        result = resolve_llm_command(TaskType.ask_question, override="")
        assert result == "./scripts/fallback.sh"

    def test_none_override_falls_back_to_routing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """None override falls back to normal routing."""
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/fallback.sh")

        result = resolve_llm_command(TaskType.ask_question, override=None)
        assert result == "./scripts/fallback.sh"


class TestResolveLLMCommandFromEnvDict:
    """Tests for resolve_llm_command() with explicit env dict."""

    def test_uses_provided_env_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Uses provided env dict instead of os.environ."""
        # Set os.environ to something different
        monkeypatch.setenv("ERDOS_LLM_COMMAND", "./scripts/from-os.sh")

        # Provide explicit env dict
        env = {"ERDOS_LLM_COMMAND": "./scripts/from-dict.sh"}

        result = resolve_llm_command(TaskType.ask_question, env=env)
        assert result == "./scripts/from-dict.sh"

    def test_env_dict_empty_raises_error(self) -> None:
        """Empty env dict raises error."""
        env: dict[str, str] = {}

        with pytest.raises(LLMRouterError):
            resolve_llm_command(TaskType.ask_question, env=env)

    def test_env_dict_with_task_specific(self) -> None:
        """Task-specific in env dict takes precedence."""
        env = {
            "ERDOS_LLM_COMMAND": "./scripts/global.sh",
            "ERDOS_LLM_COMMAND_MATH": "./scripts/math.sh",
        }

        result = resolve_llm_command(TaskType.ask_question, env=env)
        assert result == "./scripts/math.sh"
