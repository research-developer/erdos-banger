"""Unit tests for LLM task types and mapping rules."""

from erdos.core.llm.tasks import TaskType, get_env_var_chain


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self) -> None:
        """TaskType has expected values."""
        assert TaskType.ask_question.value == "ask_question"
        assert TaskType.loop_patch.value == "loop_patch"
        assert TaskType.tactic_generation.value == "tactic_generation"

    def test_task_type_members(self) -> None:
        """TaskType has exactly three members."""
        members = list(TaskType)
        assert len(members) == 3
        assert TaskType.ask_question in members
        assert TaskType.loop_patch in members
        assert TaskType.tactic_generation in members


class TestEnvVarChain:
    """Tests for get_env_var_chain() resolution order."""

    def test_ask_question_resolution_order(self) -> None:
        """ask_question resolves MATH -> global."""
        chain = get_env_var_chain(TaskType.ask_question)
        assert chain == ["ERDOS_LLM_COMMAND_MATH", "ERDOS_LLM_COMMAND"]

    def test_loop_patch_resolution_order(self) -> None:
        """loop_patch resolves CODE -> global."""
        chain = get_env_var_chain(TaskType.loop_patch)
        assert chain == ["ERDOS_LLM_COMMAND_CODE", "ERDOS_LLM_COMMAND"]

    def test_tactic_generation_resolution_order(self) -> None:
        """tactic_generation resolves COPILOT -> MATH -> global."""
        chain = get_env_var_chain(TaskType.tactic_generation)
        assert chain == [
            "ERDOS_LLM_COMMAND_COPILOT",
            "ERDOS_LLM_COMMAND_MATH",
            "ERDOS_LLM_COMMAND",
        ]

    def test_all_chains_end_with_global_fallback(self) -> None:
        """All task types fall back to ERDOS_LLM_COMMAND."""
        for task in TaskType:
            chain = get_env_var_chain(task)
            assert chain[-1] == "ERDOS_LLM_COMMAND", f"{task} missing global fallback"
