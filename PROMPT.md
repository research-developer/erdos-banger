# erdos-banger - Ralph Wiggum Loop Prompt (Spec/Feature Implementation)

You are implementing **exactly one** task from `PROGRESS.md` per iteration using **Ironclad TDD** and **Rob C. Martin discipline**.

If `PROGRESS.md` has no unchecked items:
- if `git status --porcelain` is clean, exit cleanly without making changes.
- if the repo is dirty, run **Recovery Mode** (below) to commit/push the final docs/PROGRESS updates, then exit.

---

## First Action: Read State (Mandatory)

Immediately read:

```bash
git status --porcelain=v1
cat PROGRESS.md
cat docs/specs/README.md
cat docs/bugs/README.md
cat docs/adr/README.md
```

Then read the specific SSOT doc referenced by the current task (spec/deck/path).

---

## Recovery Mode (Dirty Repo / Sprint Complete)

If `PROGRESS.md` has **no unchecked** items but `git status --porcelain=v1` is **not empty**:

1. **Do not start a new task**. You are finishing a previous iteration that timed out mid-docs.
2. Inspect what changed:

   ```bash
   git status --porcelain=v1
   git diff
   git diff --cached
   ```

3. If changes are **docs/PROGRESS only**, commit and push:

   ```bash
   git add -A
   git commit -m "docs: finalize sprint state"
   git push
   ```

4. If changes include **production code or tests** that were not committed:
   - stop and request human review (do not guess a commit message)
   - write a bug deck in `docs/bugs/` describing the incomplete state and how to recover
   - exit

---

## Your Task This Iteration (One Item Only)

### Phase 1: Read & Plan

1. Find the **FIRST** unchecked `[ ]` item in `PROGRESS.md`
   - If there are no unchecked items, exit cleanly (do not invent new tasks)
2. Identify the SSOT doc(s) for the task:
   - **SPEC-XXX**: read `docs/specs/spec-XXX-*.md` (active) or `docs/_archive/specs/spec-XXX-*.md` (implemented SSOT)
   - **DEBT-XXX**: read `docs/debt/debt-XXX-*.md` (active) or `docs/_archive/debt/debt-XXX-*.md` (implemented SSOT)
   - If the task references a filepath, read that file directly
3. **READ THE ACCEPTANCE CRITERIA** — complete ALL of them
4. Apply the **Critical Review Prompt** (below) to validate the task against SSOT

### Phase 2: Implement (TDD)

1. **FOLLOW TDD**:
   - behavior changes: write a failing test first
   - pure refactors: add tests only if needed to prevent regression
2. Complete that ONE item fully:
   - acceptance criteria met
   - `make ci` passes

### Phase 3: Commit Code FIRST (Critical!)

1. **COMMIT CODE CHANGES IMMEDIATELY** after `make ci` passes:

   ```bash
   git add -A
   git diff --cached --name-only
   git commit -m "<type>: <description>"
   ```

   - This ensures code changes are saved even if the iteration times out later
   - Note the commit hash (e.g., `abc1234`) for the next step

### Phase 4: Update Documentation (References the Commit)

1. Update the relevant docs for traceability:
   - If there is a deck/spec, record the commit hash and mark status appropriately
   - If the task is just code, add a short note to `PROGRESS.md` Work Log
2. Check off the item in `PROGRESS.md` (`[ ]` → `[x]`) and add a short Work Log entry

### Phase 5: Commit Docs & Push

1. **COMMIT DOCS** and **PUSH**:

   ```bash
   git add -A
   git diff --cached --name-only
   git commit -m "docs: update sprint state"
   git push
   ```

2. **If this completes the sprint** (no unchecked boxes remain), also run:
   - `make test-all`
   - If `mcp` tests were skipped, optionally install extras and re-run:
     - `uv sync --extra mcp` then `uv run pytest tests/integration/test_mcp_server.py tests/unit/mcp/test_tools.py`
3. Exit

Do not batch tasks.

---

## Critical Review Prompt (MANDATORY)

Before changing code based on the SSOT doc (spec/debt/bug):

```text
Review the claim or feedback (it may be from an internal or external agent).
Validate every claim from first principles. If—and only if—it's true and
helpful, update the system to align with the SSOT, implemented cleanly and
completely (Rob C. Martin discipline). Find and fix all half-measures,
reward hacks, and partial fixes if they exist. Be critically adversarial
with good intentions for constructive criticism. Ship the exact end-to-end
implementation we need.
```

---

## Stop Conditions (Escalate, Don’t Thrash)

Stop and request human input if:

1. The debt deck is inaccurate or contradicts the codebase SSOT.
2. The task would require >10 files or >500 LOC changes in a single iteration.
3. `make ci` fails after 3 attempts for the same root cause.
4. A required external tool/dep is missing and cannot be installed from the spec (e.g., optional extras not present).

If you stop:
- write a bug deck in `docs/bugs/`
- add a new unchecked item to `PROGRESS.md`
- commit and exit

---

## Quality Gates (MUST PASS)

Before marking ANY task complete:

```bash
make ci
```

### Final Quality Gate (Sprint Complete)

If `PROGRESS.md` has **no unchecked** items remaining (the sprint is complete), additionally run:

```bash
make test-all
```

If any tests fail, do **not** declare the sprint complete:
- write a bug deck in `docs/bugs/`
- add a new unchecked item to `PROGRESS.md`
- commit and exit

---

## Git Rules (Non-Negotiable)

- Never `git rebase`
- Never `git pull`
- Never `git merge`

If push fails due to divergence:

```bash
git push --force-with-lease
```
