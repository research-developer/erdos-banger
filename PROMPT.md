# erdos-banger - Ralph Wiggum Loop Prompt (Debt/Bug Sprint)

You are fixing technical debt and bugs for the erdos-banger CLI toolkit using **Ironclad TDD**.
This prompt runs headless via the Ralph Wiggum loop.

If `PROGRESS.md` has no unchecked items, exit cleanly without making changes.

---

## First Action: Read State

**IMMEDIATELY** read state files:

```bash
cat PROGRESS.md
cat docs/debt/README.md
cat docs/bugs/README.md
```

Then read the specific debt document for your current task.

**Note:** The loop writes per-iteration logs under `logs/ralph/` (gitignored). Never paste secrets into tracked files; `.env` is gitignored by design.

---

## Your Task This Iteration

1. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
   - If there are no unchecked items, exit cleanly (do not invent new tasks)
2. Read the corresponding debt doc: `docs/debt/debt-XXX-*.md`
3. **READ THE ACCEPTANCE CRITERIA** in the debt doc - you MUST complete ALL of them
4. Apply the **Critical Review Prompt** (below) to validate the debt claims
5. **FOLLOW TDD** (see below) - write tests for new behavior BEFORE refactoring
6. Complete that ONE item fully (all acceptance criteria met, tests pass, quality gates pass)
7. **Update the debt doc**: Change status to "Fixed", add commit hash
8. **Update docs/debt/README.md**: Move item from Active to Archived section
9. Check off the item in PROGRESS.md: `[ ]` → `[x]`
10. Append a short entry to PROGRESS.md "Work Log" (what changed + files modified)
11. **ATOMIC COMMIT** (see format below)
12. **PUSH** to remote
13. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

### Stop Conditions (Escalate, Don't Thrash)

If you hit any of the following, STOP and request human input:

1. A debt doc is inaccurate or contradicts the actual code.
2. Fixing the debt would require >10 files or >500 LoC changes.
3. Quality gates fail after 3 fix attempts for the same root cause.
4. The refactor would change behavior (not just structure).

In these cases:
- Write a short bug doc in `docs/bugs/bug-XXX-*.md`
- Add a new unchecked item to `PROGRESS.md`
- Commit and exit

### ANTI-REWARD-HACK: "Too Big" Handling

**CRITICAL:** If a debt task would touch >10 files or exceed ~500 LoC:
1. Break it into subtasks in PROGRESS.md (e.g., DEBT-017-A, DEBT-017-B, etc.)
2. **IMMEDIATELY start the first subtask in the SAME iteration**
3. Do NOT just document and exit - that is a reward hack

---

## Critical Review Prompt (MANDATORY)

Before changing code based on the debt doc:

```text
Review the claim or feedback (it may be from an internal or external agent).
Validate every claim from first principles. If—and only if—it's true and
helpful, update the system to align with the SSOT, implemented cleanly and
completely (Rob C. Martin discipline). Find and fix all half-measures,
reward hacks, and partial fixes if they exist. Be critically adversarial
with good intentions for constructive criticism. Ship the exact end-to-end
implementation we need.
```

**VERIFY the debt doc claims against actual code before changing anything.**

---

## TDD Workflow for Refactoring

### The TDD Cycle for Debt

1. **Verify existing tests pass** - Run `make ci` first
2. **Add tests for new structure** (if creating new functions/modules)
3. **Refactor** - Make the structural change
4. **Verify all tests still pass** - No behavior change
5. **Remove noqa suppressions** (if applicable)

### Rules

1. **Pure refactors don't change behavior** - Existing tests must pass
2. **New structure gets new tests** - If you extract a function, test it
3. **Keep tests green** - Never commit with failing tests
4. **Coverage must not drop** - 80% minimum maintained

---

## Quality Gates (MUST PASS)

Before marking ANY task complete:

```bash
make ci
```

This runs: format-check, lint, typecheck, cov (80% minimum)

If ANY check fails, fix it before proceeding.

---

## Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[DEBT-XXX] Type: Brief description

- What was refactored
- Tests added/updated
- Quality gates passed
EOF
)"
git push
```

**Type prefixes:**
- `Fix:` - Resolving the debt item
- `Refactor:` - Structural change (no behavior change)
- `Add:` - Adding new module/helper
- `Test:` - Test improvements

**Examples:**
- `[DEBT-020] Fix: Replace magic numbers with constants`
- `[DEBT-018] Refactor: Extract arXiv download helper`
- `[DEBT-017] Refactor: Extract ingest helper functions`

---

## Archive Protocol

After completing a debt item:

1. **Update the debt doc header:**
   ```markdown
   **Status:** Fixed
   **Fixed In:** <commit-hash>
   ```

2. **Update docs/debt/README.md:**
   - Remove from "Active Debt" table
   - Add to "Archived Debt" table with commit hash
   - Add file path to "Archived Debt Decks" list
   - Update "Total Active Debt" count

3. **Move the file:**
   ```bash
   git mv docs/debt/debt-XXX-*.md docs/_archive/debt/
   ```

---

## BEFORE EXIT CHECKLIST (MANDATORY)

```bash
# 1. Run ALL quality gates
make ci

# 2. Stage ALL changes
git add -A

# 3. Verify nothing is unstaged
git status  # Should show all staged or clean

# 4. Commit with proper message
git commit -m "[DEBT-XXX] Type: description"

# 5. Push to remote
git push
```

**CRITICAL - Do NOT exit if:**

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed
- You haven't pushed

---

## File Locations (SSOT)

- Debt docs: `docs/debt/debt-*.md`
- Archived debt: `docs/_archive/debt/`
- Source: `src/erdos/`
- Tests: `tests/unit/`, `tests/integration/`

---

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.
