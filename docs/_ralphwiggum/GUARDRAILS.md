# Ralph Wiggum Guardrails (Persistent Notes)

This document is a **living record** of guardrails, failure patterns, and “gotchas” observed while running long autonomous loops in this repo.

**Goal:** prevent repeated mistakes across sessions by making lessons durable.

---

## How to Use

- When a failure pattern is observed (reward hacking attempt, repeated CI failure, spec ambiguity), add an entry under **Observed Failure Patterns**.
- When we change the protocol/prompt/quality gates to address a pattern, record it under **Guardrail Changes** with the commit hash.
- Keep entries concrete and actionable (symptom → root cause → mitigation).

---

## Observed Failure Patterns

### FP-001: “Passes locally, fails in CI” drift

- Symptom: developer runs a subset of checks; CI fails on a different gate.
- Common cause: local workflow doesn’t run `make ci` (or pre-commit) before pushing.
- Mitigation: treat `make ci` as the minimum bar before every commit; keep CI and Makefile aligned.

### FP-002: Hung iteration (no progress, no output)

- Symptom: the loop stalls on an iteration (e.g., tool invocation never returns).
- Mitigation: enforce per-iteration timeouts and capture logs under `logs/ralph/` for post-mortem.

### FP-003: SSOT path drift (specs moved, checklists stale)

- Symptom: protocol/checklist references files that no longer exist (e.g., `docs/debt/README.md` after moving active trackers to `docs/_debt/`).
- Common cause: reorganizing docs without updating `docs/_ralphwiggum/**`.
- Mitigation: treat `docs/_ralphwiggum/**` as “operational SSOT” and update it in the same PR whenever docs move.

### FP-005: Git rebase derailment on push failure

- Symptom: Ralph hits "branches have diverged" and attempts `git rebase` or `git pull --rebase`, causing merge conflicts that stall the loop.
- Common cause: Multiple commits pushed in quick succession, or a race condition with the remote.
- Mitigation: **On the Ralph branch, NEVER use `git rebase` or `git pull`**. If `git push` fails due to divergence, use `git push --force-with-lease` (safe force push). The Ralph branch is autonomous - divergence means something unexpected happened, and force-push is the correct recovery.

### FP-004: Secrets accidentally end up in tracked logs

- Symptom: API keys (or other secrets) are copied into tracked files during debugging or loop summaries.
- Common cause: pasting raw `.env` content or command output into tracked files (docs, specs, prompts).
- Mitigation: never paste secrets; keep `.env` gitignored; scan tracked files and staged diffs before pushing:
  - `git diff --cached | rg -in "(sk-|sk-ant-|ghp_|AIza|arstl_|xoxb-|hf_)"` (what you're about to push)
  - `git ls-files -z | xargs -0 rg -in "(sk-|sk-ant-|ghp_|AIza|arstl_|xoxb-|hf_)"` (full tracked tree)

### FP-006: EPIPE / stream-destroyed errors from timeouts and piping

- Symptom: the Claude CLI exits mid-iteration with `Error: write EPIPE` / `ERR_STREAM_DESTROYED` and/or exit code `124`.
- Common causes:
  - Piping Claude output through `tee` (`claude ... | tee -a log`).
  - The per-iteration `timeout`/`gtimeout` kills the Claude process, and the Node CLI crashes while writing during shutdown.
- Mitigations:
  - Always append output via redirection (never pipe Claude output through `tee`):
    - Bad: `claude -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log"`
    - Good: `claude -p "$(cat PROMPT.md)" >> "$log" 2>&1`
  - If you see repeated exit `124`, increase `ITER_TIMEOUT` for that sprint (or split tasks smaller).
  - Treat occasional EPIPE as a recoverable failure mode: ensure the runner commits/pushes progress so the next iteration can continue.

### FP-007: Staged but uncommitted changes (iteration timeout before commit)

- Symptom: Iteration completes all work, stages changes, updates PROGRESS.md (marking task done), but never commits. Loop sees "all tasks complete" and exits, leaving work staged but not committed.
- Root cause: PROMPT.md had commit step AFTER updating PROGRESS.md. If iteration times out after PROGRESS.md update but before commit, the loop completion check (`grep -q "^\- \[ \]" PROGRESS.md`) reads from the working directory (which shows task complete) and exits.
- Mitigation (PROMPT.md fix): Restructured steps to commit code changes FIRST (Phase 3), then update docs/PROGRESS.md (Phase 4), then commit docs and push (Phase 5). This ensures code is saved even if the iteration times out during documentation updates.
- Mitigation (ralph-loop.sh fix): Added guardrail check after each iteration that warns loudly if staged-but-uncommitted changes are detected. On sprint completion, auto-commits docs/`PROGRESS.md` if (and only if) those are the only dirty paths.

### FP-008: Commit message does not match staged diff

- Symptom: commit message suggests a broader change than what actually shipped (e.g., “docs(debt)” but only `PROGRESS.md` changed).
- Root cause: committing without reviewing the staged diff.
- Mitigation: before every commit, run:
  - `git diff --cached --name-only`
  - `git diff --cached`

---

## Guardrail Changes (Protocol/Prompt/CI)

- 2026-01-24: Hardened sprint-complete recovery. Updated PROMPT.md with explicit “Recovery Mode” and improved commit-diff validation. Updated `scripts/ralph-loop.sh` to auto-finalize docs/`PROGRESS.md` on completion (docs-only) instead of exiting dirty.
- 2026-01-22: Added FP-007 (staged but uncommitted changes). Restructured PROMPT.md to commit code FIRST, then docs. Hardened `scripts/ralph-loop.sh` to warn on staged-but-uncommitted changes and refuse to exit cleanly with a dirty working tree.
- 2026-01-22: Added FP-006 (EPIPE errors). Updated `scripts/ralph-loop.sh` to use direct file redirection instead of piping through `tee`. Updated protocol.md to recommend the script.
- 2026-01-21: Added FP-005 (git rebase derailment). Updated PROMPT.md and protocol.md to explicitly forbid `git rebase` and `git pull`, with `--force-with-lease` as the recovery for divergence.
- 2026-01-19: Added iteration + total runtime timeouts and per-iteration logs (`logs/ralph/`) to the recommended loop commands.
