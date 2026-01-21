# Spec 021: Harmonic Aristotle Integration (Deferred to v1.2+)

> Integrate Harmonic’s Aristotle as an optional Lean theorem-proving backend for `erdos-banger`.

**Status:** Ready (Deferred)
**Target:** v1.2+
**Prerequisites (SSOT):**
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Loop design decisions: `docs/specs/spec-012-design.md`
- Loop command: `docs/specs/spec-012-loop-command.md`
- Vendor notes: `docs/_vendor-docs/harmonic-aristotle/README.md`

---

## 0) Executive Summary

Harmonic’s Aristotle can propose Lean proof code using a dedicated theorem-proving service. This spec defines:

1. A **safe, opt-in CLI integration** (`erdos lean prove`) that runs Aristotle against a Lean file and writes an output file.
2. A **future integration point** for `erdos loop` (SPEC-012) to use Aristotle as a solver backend.

This is **not** a replacement for the existing subprocess-based LLM architecture. Aristotle is an additional backend with clear safety and testability constraints.

---

## 1) Scope

### In scope

- Add an **optional** “Aristotle prove” command that:
  - requires explicit configuration (`ARISTOTLE_API_KEY` present)
  - runs an external command (`aristotle` CLI from `aristotlelib`)
  - never overwrites the input Lean file by default
  - returns structured `CLIOutput` JSON on `--json`

### Out of scope

- Direct HTTP integration (we use the vendor CLI as a subprocess boundary).
- Automatic Lean toolchain upgrades for compatibility (this needs a dedicated Lean upgrade spec).
- Any claim of “solving Erdős problems” automatically.

---

## 2) Configuration

### Required environment variable (vendor)

- `ARISTOTLE_API_KEY` — required by the vendor CLI. Must be set in local `.env` (gitignored).

### Optional configuration (erdos-banger)

- `ERDOS_ARISTOTLE_COMMAND` — the command to execute (default: `aristotle` on PATH).

`.env.example` must include placeholders for these variables (no real keys).

---

## 3) CLI: `erdos lean prove`

### Signature

```text
erdos lean prove [OPTIONS] INPUT_FILE
```

### Arguments

- `INPUT_FILE` (path, required): Lean file to prove.

### Options

- `--output FILE`: output Lean file path (required; must not equal INPUT_FILE)
- `--timeout SECONDS`: subprocess timeout (default: 600)
- `--informal`: pass `--informal` to Aristotle (vendor behavior)
- `--formal-input-context`: pass `--formal-input-context` to Aristotle (vendor behavior)
- `--json`: machine output (CLIOutput envelope)

### Behavior

1. Validate:
   - `ARISTOTLE_API_KEY` is set (else `ExitCode.CONFIG_ERROR`).
   - `ERDOS_ARISTOTLE_COMMAND` exists on PATH (else `ExitCode.CONFIG_ERROR`).
   - `INPUT_FILE` exists (else `ExitCode.NOT_FOUND`).
   - `--output` is provided and is not the same path as `INPUT_FILE` (else `ExitCode.USAGE_ERROR`).
2. Execute the vendor CLI via subprocess:
   - `"$ERDOS_ARISTOTLE_COMMAND" prove-from-file "$INPUT_FILE" --output-file "$OUTPUT_FILE" ...`
3. On success:
   - Return `CLIOutput.ok(command="erdos lean prove", data={...})`.
4. On failure:
   - Return `CLIOutput.err(...)` with an error type indicating:
     - configuration error
     - timeout
     - nonzero exit code with captured stderr

### JSON output schema (data)

```json
{
  "input_file": "formal/lean/Erdos/Problem006.lean",
  "output_file": "formal/lean/Erdos/Problem006.aristotle.lean",
  "aristotle": {
    "command": "aristotle",
    "informal": false,
    "formal_input_context": false,
    "timeout_s": 600,
    "exit_code": 0
  }
}
```

### Exit codes

Use `src/erdos/core/exit_codes.py`:

- `ExitCode.SUCCESS` on success
- `ExitCode.USAGE_ERROR` for invalid args (e.g. output == input)
- `ExitCode.NOT_FOUND` when input file missing
- `ExitCode.CONFIG_ERROR` when required env/command missing
- `ExitCode.ERROR` for nonzero Aristotle exit code or unexpected failures

---

## 4) Integration Point: `erdos loop` backend (deferred)

When SPEC-012 is implemented, it may optionally support:

- `--solver=llm` (default) — existing SEARCH/REPLACE patch workflow
- `--solver=aristotle` — invoke `erdos lean prove` and treat the resulting file as the proposed patch

Safety rules remain the same:
- Never overwrite files without confirmation (unless `--yes`).
- Count `sorry`/`admit` deltas and reject regressions per SPEC-012 design.

This integration is *explicitly deferred* to the SPEC-012 implementation PR.

---

## 5) Implementation Plan (v1.2+)

### Modules to create

- `src/erdos/core/aristotle.py`
  - `AristotleError`
  - `run_aristotle_prove_from_file(...)` (subprocess wrapper)
- `src/erdos/commands/lean.py`
  - Add `prove` subcommand using the shared presenter pattern

### Tests (no network required)

- Unit tests for command construction and validation:
  - missing `ARISTOTLE_API_KEY` returns `ExitCode.CONFIG_ERROR`
  - missing command returns `ExitCode.CONFIG_ERROR`
  - input missing returns `ExitCode.NOT_FOUND`
  - output == input returns `ExitCode.USAGE_ERROR`
  - timeout maps to `ExitCode.ERROR` with `error.type="Timeout"`
  - nonzero exit code maps to `ExitCode.ERROR` and includes stderr in JSON error message
- Integration test (mock subprocess):
  - verifies JSON output shape is stable and stdout is clean in `--json` mode

---

## 6) Vendor Documentation Handling

All vendor references must live under:

- `docs/_vendor-docs/harmonic-aristotle/`

Do not copy large vendor docs verbatim unless licensing explicitly permits it; prefer source links + summary notes.
