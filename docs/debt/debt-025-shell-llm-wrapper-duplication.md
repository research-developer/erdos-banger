# Technical Debt 025: DRY Violation in Shell LLM Wrappers (`load_env_file`)

**Date:** 2026-01-20
**Status:** Fixed
**Fixed In:** (pending commit)
**Priority:** P4 (Nice-to-have)
**Impact:** Small maintenance risk; changes must be duplicated across scripts

## Summary

The bash LLM wrapper scripts duplicate the same `.env` parsing routine (`load_env_file`). This is acceptable for v1, but it’s easy to drift over time (e.g., bugfix applied to one script but not the others).

## Evidence

The function body is duplicated (nearly verbatim) in:

- `scripts/llm-openai.sh`
- `scripts/llm-anthropic.sh`
- `scripts/llm.sh`

## Proposed Fix (Optional)

- Extract a shared helper: `scripts/lib/load-env.sh` and source it:
  - `source "${SCRIPT_DIR}/lib/load-env.sh"`
- Or replace custom parsing with a minimal, documented contract:
  - `.env` must be simple `KEY=value` lines without escaping/`=` in values.

## Acceptance Criteria

- The `.env` loading logic is defined in exactly one place, or the limitations are documented explicitly.
