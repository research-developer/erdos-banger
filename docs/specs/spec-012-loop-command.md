# Spec 012: Loop Command (Deferred to v1.2+)

> Defines `erdos loop` for an iterative “propose → apply → check” cycle to assist Lean formalization.

**Status:** Deferred (v1.2+)  
**Prerequisites (SSOT):**
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Ask command (prompt + optional LLM): `docs/specs/spec-011-ask-command.md`

---

## 0) Why Deferred?

This command is intentionally deferred because it is high-risk and high-complexity:

1. It modifies files on disk (needs strong safety guardrails).
2. It can easily become a “reward hack” loop that passes compilation while stating nonsense.
3. It depends on stable building blocks:
   - deterministic Lean project init + check (Spec 007)
   - reliable retrieval/prompt tooling (Spec 011)
   - (optional) ingested fulltext improving retrieval (Spec 010)

---

## 1) CLI Interface

### Command signature

```text
erdos loop PROBLEM_ID [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (int, required)

**Options**

- `--max-iter, -n INT`: maximum iterations (default: `10`)
- `--yes, -y`: non-interactive; automatically apply changes
- `--no-apply`: propose changes only; never write to disk
- `--timeout SECONDS`: Lean check timeout (default: `120`)
- `--llm-cmd TEXT`: override LLM command (default: from `ERDOS_LLM_COMMAND`)
- `--from-iteration INT`: resume from a previous loop log (future; optional)

**Global flags**

- `--json` must be supported (Spec 004).

### Examples

```bash
# Propose-only (safe): no file writes
uv run erdos loop 6 --no-apply

# Non-interactive (dangerous): apply up to 3 iterations
ERDOS_LLM_COMMAND="./scripts/llm.sh" uv run erdos loop 6 --yes --max-iter 3

# Machine output (propose-only)
uv run erdos --json loop 6 --no-apply
```

---

## 2) Execution Model (SSOT)

At a high level:

1. Ensure `formal/lean/` exists and is initialized (reuse `erdos lean init` logic if needed).
2. Ensure the target file exists:
   - default: `formal/lean/Erdos/Problem{PROBLEM_ID:03d}.lean`
   - create via `Formalizer.generate_skeleton(...)` if missing
3. Run Lean check via `LeanRunner.check(...)`.
4. If compilation succeeds and there are **no `sorry`** occurrences, exit success.
5. Otherwise:
   - build a prompt containing:
     - the current Lean file (or relevant excerpt)
     - Lean errors (from `LeanCheckResult.errors`)
     - the problem statement (`ProblemRecord`)
     - optional retrieved context (via `SearchIndex.search`)
   - run the external LLM command (subprocess) to propose an edit
   - show the proposed patch and request confirmation (unless `--yes`)
   - apply the patch (unless `--no-apply`)
   - repeat until success or max iterations reached

**Invariant:** The loop never silently modifies files. Either:

- it prompts the user, or
- `--yes` is provided.

---

## 3) Safety Guardrails (Non-negotiable)

1. **Patch-only edits**
   - The LLM must output a unified diff (or a structured “replace lines X–Y” patch).
   - Reject free-form code dumps.
2. **Scoped edits**
   - Only allow modifications under `formal/lean/Erdos/`.
3. **Hard limits**
   - max iterations
   - max patch size (lines / bytes)
   - max file size included in prompt
4. **No network by default**
   - The CLI itself does not call external APIs directly.
   - LLM usage is via a user-configured command (Spec 011 pattern).

---

## 4) Output Schema (JSON)

All JSON output must be wrapped in `CLIOutput` (Spec 003). `data` must include:

```json
{
  "problem_id": 6,
  "status": "max_iterations",
  "iterations_completed": 10,
  "iterations_max": 10,
  "file": "formal/lean/Erdos/Problem006.lean",
  "no_apply": true,
  "llm": {
    "enabled": true,
    "command": "./scripts/llm.sh"
  },
  "last_check": {
    "success": false,
    "error_count": 2,
    "has_sorry": true
  }
}
```

Notes:

- When `--no-apply` is set, `status` may be `no_progress` even if a patch was proposed.
- When `--json` is enabled, no progress/human text may be written to stdout.

---

## 5) Implementation (Modules to Create in v1.2)

### 5.1 `src/erdos/core/loop.py`

Responsibilities:

- Orchestrate the loop and return `CLIOutput` summaries.
- Provide helpers:
  - `count_sorries(text: str) -> int`
  - `apply_unified_diff(path: Path, diff_text: str) -> None` (strict validation)

### 5.2 `src/erdos/commands/loop.py`

Follow Spec 004 patterns and call core loop logic.

---

## 6) Verification (Testable Even While Deferred)

When implemented, the following tests are required:

### Unit tests (no Lean required)

- `count_sorries` correctness on small Lean snippets.
- Patch validation rejects:
  - edits outside `formal/lean/Erdos/`
  - oversized patches
  - non-diff outputs

### Integration tests (optional; marked `requires_lean`)

- Run `erdos loop <id> --no-apply` in a temp Lean project and assert it exits 0 and does not modify files.

---

## References

- subprocess execution (Python): `https://docs.python.org/3/library/subprocess.html`
- Lean runner + skeleton generation: `docs/_archive/specs/spec-007-lean-integration.md`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.2.0 | 2026-01-18 | Rewrite: align with v1 `src/erdos/core` structure and Spec 011 external LLM approach |

