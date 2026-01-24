# SPEC-032: Multi-Model Routing (External Command)

> **Status:** Complete
>
> **Target:** v3.5
>
> **Resolves:** Single-command limitation; task-appropriate LLM backends
>
> **Prerequisites:** SPEC-028 (v3 verification)

---

## Summary

Add **task-level routing** for LLM calls while preserving the repo’s existing, vendor-neutral integration pattern: **LLMs are invoked via external commands** (e.g. `ERDOS_LLM_COMMAND=./scripts/llm.sh`).

This spec does **not** require direct OpenAI/Anthropic SDK integration in Python. “Model selection” is implemented by choosing the appropriate **command/script** per task.

---

## Goals / Non-Goals

### Goals

1. Route LLM work to different backends per task (ask vs loop vs copilot).
2. Keep the core vendor-neutral (commands/scripts decide provider/model).
3. Preserve the existing UX (`ERDOS_LLM_COMMAND`, `--llm-cmd`, `--no-llm`).
4. Make routing behavior fully testable offline (no network, no API keys).

### Non-Goals

- Replacing `ERDOS_LLM_COMMAND` with provider-specific SDK calls.
- Benchmark-based “best model” claims inside the spec.
- Dynamic routing based on prompt content.
- Streaming responses.

---

## Scope

### In Scope

1. **Task enum** describing LLM call sites.
2. **Command router** that resolves a task → command string (with fallback).
3. **Execution helper** that runs the command shell-free (reusing existing patterns).
4. **CLI wiring**:
   - `erdos ask`: use router unless `--llm-cmd` override is provided
   - `erdos loop run`: use router unless `--llm-cmd` override is provided
   - (future) `erdos lean copilot serve` (SPEC-033): use router for tactic generation

### Out of Scope

- Exa Research integration (covered by SPEC-029; not an LLM command).
- Changing deterministic/template-based commands (e.g. `erdos lean formalize`).

---

## Configuration

### Environment Variables (Primary)

These variables select **commands**, not “models”:

```bash
# Existing global fallback (still supported)
ERDOS_LLM_COMMAND=./scripts/llm.sh

# Optional task-specific commands
ERDOS_LLM_COMMAND_MATH=./scripts/llm-openai.sh
ERDOS_LLM_COMMAND_CODE=./scripts/llm-anthropic.sh
ERDOS_LLM_COMMAND_COPILOT=./scripts/llm-openai.sh
```

### Task → Command Mapping

| Task | Default Command Resolution |
|------|----------------------------|
| `ask_question` | `ERDOS_LLM_COMMAND_MATH` → `ERDOS_LLM_COMMAND` |
| `loop_patch` | `ERDOS_LLM_COMMAND_CODE` → `ERDOS_LLM_COMMAND` |
| `tactic_generation` | `ERDOS_LLM_COMMAND_COPILOT` → `ERDOS_LLM_COMMAND_MATH` → `ERDOS_LLM_COMMAND` |

---

## Architecture

### Module Structure

```text
src/erdos/core/llm/
  __init__.py
  tasks.py            # TaskType enum + mapping rules
  router.py           # Resolve task -> command string
```

Execution is intentionally reused from existing call sites (ask/loop/copilot) so the router remains a small, testable unit:

- `src/erdos/commands/ask.py` resolves `TaskType.ask_question`
- `src/erdos/commands/loop.py` resolves `TaskType.loop_patch`
- `src/erdos/lean_copilot/server.py` resolves `TaskType.tactic_generation`

### Router Semantics (Precise)

- A task resolves to a command string by checking the environment-variable chain defined in `TaskType`.
- If `--llm-cmd` (override) is provided and non-empty, routing is bypassed entirely.
- If no command is configured, the CLI returns a clear configuration error (lists the env vars that were checked).

---

## CLI Integration

### `erdos ask`

- Existing behavior stays the same:
  - `--no-llm` disables execution
  - `--llm-cmd` overrides routing entirely
- New default behavior when LLM is enabled and `--llm-cmd` is not provided:
  - use `TaskType.ask_question` routing

### `erdos loop run`

- Existing behavior stays the same:
  - `--llm-cmd` overrides routing entirely
- New default behavior when `--llm-cmd` is not provided:
  - use `TaskType.loop_patch` routing

### Examples

```bash
# Ask uses the "math" LLM command (falls back to ERDOS_LLM_COMMAND).
ERDOS_LLM_COMMAND_MATH=./scripts/llm-openai.sh erdos ask 6 "Summarize the current approach"

# Loop uses the "code" LLM command (falls back to ERDOS_LLM_COMMAND).
ERDOS_LLM_COMMAND_CODE=./scripts/llm-anthropic.sh erdos loop run 6 --max-iter 10
```

---

## Testing

### Unit Tests (Offline)

- Task mapping resolution order.
- Behavior when env vars are missing/empty.
- Error message includes the checked env vars.

### Integration Tests (Offline)

Use `CliRunner` with temporary fixture scripts to confirm routing is honored:

- `tests/integration/test_cli_ask_router.py`
- `tests/integration/test_cli_loop_router.py`

---

## Acceptance Criteria

1. [ ] Router selects per-task command with documented precedence.
2. [ ] Existing `ERDOS_LLM_COMMAND` behavior remains valid.
3. [ ] `--llm-cmd` bypasses routing (ask + loop).
4. [ ] Clear errors when no command is configured.
5. [ ] Offline unit + integration tests cover routing and execution.

---

## References

- `src/erdos/core/ask/llm.py` (current external-command execution model)
- `src/erdos/commands/ask.py` and `src/erdos/commands/loop.py` (current CLI call sites)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
| 2026-01-23 | Rewritten to align with external-command LLM architecture and current CLI (`erdos loop run`) |
