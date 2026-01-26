# DEBT-109: `erdos ask` prompt lacks budget guardrails

**Priority:** P2 (Material quality gap; should be scheduled soon)
**Status:** Open
**Found:** 2026-01-26

## Summary

`erdos ask` constructs a deterministic prompt that includes the full text of every retrieved chunk (and sometimes `research/problems/{id}/SYNTHESIS.md`). This has **no hard size limit** today.

For “real” corpora (PDF extractions, long notes/synthesis), the prompt can grow large enough to:

- exceed downstream LLM context limits (or wrapper tool limits)
- increase latency / timeouts (`LLM_COMMAND_TIMEOUT`)
- make answers worse due to dilution/noise

This is a classic “works in tests, fails at scale” failure mode.

## Evidence (SSOT)

- Prompt assembly: `src/erdos/core/ask/prompt.py` (`build_prompt`)
- Retrieval can return long blobs (e.g., research synthesis, PDF extraction chunks): `src/erdos/core/ask/retrieval.py`
- Unlike `erdos loop`, `erdos ask` has no prompt budgeting step:
  - Loop budgeting exists: `src/erdos/core/loop/prompt.py` (`budget_context`)

## Why This Matters (First Principles)

External LLMs have bounded input:

- some vendors hard-fail on oversized prompts
- others accept and silently truncate, producing misleading behavior

If the tool’s success depends on prompt size, we should make truncation **explicit, deterministic, and testable**.

## Proposed Fix (Design)

Add an “ask prompt budgeting” step analogous to the loop:

1. Define a maximum prompt budget in bytes (UTF‑8) for the LLM path (not necessarily for JSON output).
2. Always preserve (in order):
   - problem metadata + statement
   - the user question
   - source headers / ids
3. Truncate sources deterministically:
   - keep the first `N` bytes of each source
   - append a clear marker like `(...truncated...)`
   - optionally bias towards shorter/higher-ranked sources
4. Make this behavior testable and configurable:
   - constant default (e.g., `ASK_PROMPT_MAX_BYTES`)
   - optional CLI override if needed later

## Acceptance Criteria

1. [ ] Add deterministic budgeting for the LLM prompt path in `erdos ask`.
2. [ ] Ensure budgeting preserves statement + question and retains citations scaffold.
3. [ ] Add unit tests asserting prompt length stays under the budget and that required sections remain present.
4. [ ] Keep JSON output unchanged (or explicitly document any change).
5. [ ] `make ci` passes.
