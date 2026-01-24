"""Loop iteration state machine.

This module executes a single iteration (Lean check -> prompt -> LLM -> patch
validation -> apply/record). It is intentionally separate from `runner.py` to
keep orchestration and iteration mechanics decoupled.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from erdos.core.loop.iteration_steps import (
    apply_patch_and_record_iteration,
    build_prompt_and_log,
    execute_llm_and_log,
    handle_llm_exit_code,
    read_file_state,
    record_no_apply_iteration,
    run_lean_check_and_log,
    validate_patch_and_maybe_record,
)
from erdos.core.loop.result import IterationRecord, LoopStatus


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.lean import LeanRunner
    from erdos.core.loop.config import LoopConfig
    from erdos.core.loop.logging import LoopLogger
    from erdos.core.models import LeanCheckResult, ProblemRecord
    from erdos.core.ports import LLMExecute


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ValidatedPatch:
    search_text: str
    replace_text: str


class _IterationRunner:
    def __init__(
        self,
        *,
        file_path: Path,
        problem: ProblemRecord,
        config: LoopConfig,
        lean_runner: LeanRunner,
        llm_command: str,
        no_apply: bool,
        rag_chunks: list[Any],
        loop_logger: LoopLogger,
        iterations: list[IterationRecord],
        llm_execute: LLMExecute,
    ) -> None:
        self._file_path = file_path
        self._problem = problem
        self._config = config
        self._lean_runner = lean_runner
        self._llm_command = llm_command
        self._no_apply = no_apply
        self._rag_chunks = rag_chunks
        self._loop_logger = loop_logger
        self._iterations = iterations
        self._llm_execute = llm_execute

    def _call_llm_and_get_patch(
        self,
        *,
        iteration: int,
        file_content: str,
        sorries_before: int,
        admits_before: int,
        last_check: LeanCheckResult,
        stall_count: int,
    ) -> tuple[LoopStatus | None, int, _ValidatedPatch | None]:
        prompt = build_prompt_and_log(
            iteration=iteration,
            file_path=self._file_path,
            file_content=file_content,
            problem=self._problem,
            check_result=last_check,
            rag_chunks=self._rag_chunks,
            config=self._config,
            loop_logger=self._loop_logger,
        )

        try:
            response, exit_code = execute_llm_and_log(
                iteration=iteration,
                llm_command=self._llm_command,
                prompt=prompt,
                llm_execute=self._llm_execute,
                loop_logger=self._loop_logger,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            logger.exception("LLM execution failed: %s", e)
            return LoopStatus.ERROR, stall_count, None

        if exit_code != 0:
            terminal_status, new_stall = handle_llm_exit_code(
                iteration=iteration,
                exit_code=exit_code,
                sorries_before=sorries_before,
                admits_before=admits_before,
                last_check=last_check,
                stall_count=stall_count,
                config=self._config,
                iterations=self._iterations,
            )
            return terminal_status, new_stall, None

        terminal_status, new_stall, search_text, replace_text = (
            validate_patch_and_maybe_record(
                iteration=iteration,
                response=response,
                file_path=self._file_path,
                config=self._config,
                loop_logger=self._loop_logger,
                sorries_before=sorries_before,
                admits_before=admits_before,
                last_check=last_check,
                stall_count=stall_count,
                iterations=self._iterations,
            )
        )
        if search_text is None or replace_text is None:
            return terminal_status, new_stall, None

        return terminal_status, new_stall, _ValidatedPatch(search_text, replace_text)

    def run(
        self, *, iteration: int, stall_count: int
    ) -> tuple[LoopStatus | None, LeanCheckResult, int, bool]:
        logger.info("Loop iteration %d/%d", iteration, self._config.max_iterations)

        file_content, sorries_before, admits_before, size_before = read_file_state(
            self._file_path
        )
        last_check = run_lean_check_and_log(
            iteration=iteration,
            file_path=self._file_path,
            lean_runner=self._lean_runner,
            config=self._config,
            loop_logger=self._loop_logger,
        )

        if last_check.success and sorries_before == 0 and admits_before == 0:
            return LoopStatus.SUCCESS, last_check, stall_count, False

        terminal_status, new_stall, patch = self._call_llm_and_get_patch(
            iteration=iteration,
            file_content=file_content,
            sorries_before=sorries_before,
            admits_before=admits_before,
            last_check=last_check,
            stall_count=stall_count,
        )
        if patch is None:
            return terminal_status, last_check, new_stall, True

        if self._no_apply:
            record_no_apply_iteration(
                iteration=iteration,
                loop_logger=self._loop_logger,
                sorries_before=sorries_before,
                admits_before=admits_before,
                last_check=last_check,
                iterations=self._iterations,
            )
            return LoopStatus.NO_PROGRESS, last_check, new_stall, True

        terminal_status, last_check, new_stall = apply_patch_and_record_iteration(
            iteration=iteration,
            file_path=self._file_path,
            search_text=patch.search_text,
            replace_text=patch.replace_text,
            sorries_before=sorries_before,
            admits_before=admits_before,
            size_before=size_before,
            config=self._config,
            loop_logger=self._loop_logger,
            iterations=self._iterations,
            stall_count=new_stall,
            last_check=last_check,
            lean_runner=self._lean_runner,
        )
        return terminal_status, last_check, new_stall, True
