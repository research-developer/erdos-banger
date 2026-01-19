# erdos-banger - Ralph Wiggum Loop Prompt

You are implementing specs for the erdos-banger CLI toolkit using **Ironclad TDD**.
This prompt runs headless via:

```bash
MAX=50
TIMEOUT=14400
ITER_TIMEOUT=600

TIMEOUT_CMD="${TIMEOUT_CMD:-}"
if [[ -z "$TIMEOUT_CMD" ]]; then
  if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    echo "Missing timeout command. Install coreutils (macOS) or use Linux 'timeout'." >&2
    exit 1
  fi
fi

mkdir -p logs/ralph

"$TIMEOUT_CMD" "$TIMEOUT" bash -c '
  for i in $(seq 1 '"$MAX"'); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"
    echo "=== Iteration $i/'"$MAX"' ===" | tee -a "$log"
    '"$TIMEOUT_CMD"' '"$ITER_TIMEOUT"' claude --dangerously-skip-permissions -p "$(cat PROMPT.md)" 2>&1 | tee -a "$log"
    sleep 2
  done
'
```

If `PROGRESS.md` has no unchecked items, exit cleanly without making changes.

---

## First Action: Read State

**IMMEDIATELY** read state files:

```bash
cat PROGRESS.md
cat docs/specs/README.md
```

Then read the specific spec for your current task.

---

## SPEC-* Self-Review Protocol (APPLY FIRST)

**Before picking up a new task**, check if the MOST RECENTLY completed item is a `SPEC-*` WITHOUT a `[REVIEWED]` marker.

If yes, **THIS ITERATION IS A REVIEW ITERATION**:

1. Read the spec doc and its acceptance criteria
2. Verify the implementation matches ALL acceptance criteria
3. Apply the Critical Review Prompt (below) to your own prior work
4. Check for half-measures:
   - Are there TODO comments that should be resolved?
   - Do tests cover all acceptance criteria?
   - Does SSOT (code) match the spec?
5. **If issues found**:
   - Create a fixup task in PROGRESS.md (e.g., `[ ] **SPEC-010-FIX**: Fix missing tests`)
   - Mark the original as `[NEEDS-FIX]` instead of `[REVIEWED]`
   - Commit and exit
6. **If verified clean**:
   - Add `[REVIEWED]` marker to the spec line
   - Append to Work Log: "SPEC-XXX reviewed and verified"
   - Commit and exit (do NOT start next task this iteration)

---

## Your Task This Iteration

1. Check for unreviewed SPEC-* (see above) - if found, do review, then exit
2. Find the **FIRST** unchecked `[ ]` item in PROGRESS.md
   - If there are no unchecked items, exit cleanly (do not invent new tasks)
3. Read the corresponding spec doc: `docs/specs/spec-XXX-*.md`
4. **READ THE ACCEPTANCE CRITERIA** in the spec - you MUST complete ALL of them
5. Apply the **Critical Review Prompt** (below) to any external feedback
6. **FOLLOW TDD** (see below) - write failing tests FIRST
7. Complete that ONE item fully (all acceptance criteria met, tests pass, quality gates pass)
8. Check off the item in PROGRESS.md: `[ ]` → `[x]`
9. Append a short entry to PROGRESS.md "Work Log" (what changed + files modified)
10. **ATOMIC COMMIT** (see format below)
11. Exit

**DO NOT** attempt multiple tasks. One task per iteration.

### Stop Conditions (Escalate, Don't Thrash)

If you hit any of the following, STOP and request human input (do not keep looping blindly):

1. A spec is ambiguous, contradictory, or references missing SSOT.
2. A tool/dep is missing or incompatible (e.g., `uv sync --frozen` cannot succeed).
3. Quality gates fail after 3 fix attempts for the same root cause.
4. The task would require network access but the spec requires offline determinism.

In these cases:
- write a short `docs/bugs/bug-XXX-*.md` or `docs/debt/debt-XXX-*.md` with reproduced evidence
- add a new unchecked item to `PROGRESS.md`
- commit and exit

### ANTI-REWARD-HACK: "Too Big" Is NOT a Blocker

**CRITICAL:** If a task would touch >10 files or exceed ~500 LoC:
1. Break it into subtasks in PROGRESS.md (e.g., SPEC-010-A, SPEC-010-B, etc.)
2. **IMMEDIATELY start the first subtask in the SAME iteration**
3. Do NOT write a debt doc and exit - that is a reward hack

**Writing documentation ABOUT work is NOT the same as DOING work.**
Escalation docs are only valid for: missing deps, spec contradictions, repeated gate failures.
"It's big" is never a valid reason to stop working.

---

## Critical Review Prompt (MANDATORY)

Before changing code/docs based on feedback (human, CodeRabbit, another model, your own prior output), apply:

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

## TDD Workflow (IRONCLAD - NON-NEGOTIABLE)

### The TDD Cycle

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up, keep tests green

### TDD Rules

1. **No production code without a failing test first**
2. **One test at a time** - Don't batch tests
3. **Minimal implementation** - Only enough to pass the current test
4. **Refactor only when green** - Never refactor with failing tests
5. **Tests document behavior** - Tests are the specification

### Spec → Test → Code Flow

```
docs/specs/spec-010-ingest-command.md  # 1. Read the spec
    ↓
tests/unit/test_arxiv_client.py        # 2. Write failing test
    ↓
uv run pytest tests/unit/test_arxiv_client.py -v  # 3. Verify it fails
    ↓
src/erdos/core/arxiv_client.py         # 4. Implement to pass
    ↓
uv run pytest tests/unit/test_arxiv_client.py -v  # 5. Verify it passes
    ↓
make ci                                 # 6. All quality gates pass
    ↓
git commit                              # 7. Atomic commit
```

---

## Quality Gates (MUST PASS)

Before marking ANY task complete:

```bash
uv run pre-commit run --all-files  # All hooks
uv run ruff check .                # No lint errors
uv run ruff format --check .       # Properly formatted
uv run mypy src/ tests/            # No type errors
uv run pytest -m "not requires_lean and not requires_network" --cov=erdos --cov-fail-under=80
```

Or use:

```bash
make ci
```

If ANY check fails, fix it before proceeding.

---

## Atomic Commit Format

```bash
git add -A && git commit -m "$(cat <<'EOF'
[SPEC-XXX] Type: Brief description

- What was implemented
- Tests added
- Quality gates passed
EOF
)"
```

**Type prefixes:**
- `Implement:` - New feature/module
- `Add:` - Adding to existing module
- `Fix:` - Bug fix
- `Refactor:` - Code cleanup (no behavior change)
- `Test:` - Test-only changes
- `Review:` - Self-review iteration

**Examples:**
- `[SPEC-010] Implement: arXiv metadata client`
- `[SPEC-010] Add: Crossref API client`
- `[SPEC-010-REVIEW] Review: All acceptance criteria verified`

---

## Guardrails

1. **Check for unreviewed SPEC-* first**
2. **ONE task per iteration**
3. **Read PROGRESS.md first**
4. **Read the spec doc**
5. **TDD: Write test BEFORE code**
6. **Verify ALL acceptance criteria**
7. **Quality gates must pass**
8. **Mark task complete ONLY if ALL criteria done**
9. **Commit before exit**
10. **Exit when done**

---

## BEFORE EXIT CHECKLIST (MANDATORY)

**You MUST complete ALL of these steps before exiting:**

```bash
# 1. Run ALL quality gates (never commit without these)
uv run pre-commit run --all-files
uv run ruff check .
uv run ruff format .
uv run mypy src/ tests/
uv run pytest -m "not requires_lean and not requires_network" --cov=erdos --cov-fail-under=80

# 2. Stage ALL changes
git add -A

# 3. Verify nothing is unstaged
git status  # Should show all staged or clean

# 4. Commit with proper message
git commit -m "[SPEC-XXX] Type: description"
```

**CRITICAL - Do NOT exit if:**

- `git status` shows unstaged changes
- Any quality gate failed
- You haven't committed
- Task has unchecked acceptance criteria but PROGRESS.md shows `[x]`

If you made no changes (because there were no active tasks), exit without committing.

---

## File Locations (SSOT)

- Specs: `docs/specs/spec-*.md`
- Archived specs: `docs/_archive/specs/`
- Source: `src/erdos/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Fixtures: `tests/fixtures/`
- Templates: `src/erdos/templates/`

---

## Test Markers

```bash
# Default: Skip Lean and network tests
uv run pytest -m "not requires_lean and not requires_network"

# All tests (requires Lean installed)
uv run pytest

# Only Lean tests
uv run pytest -m "requires_lean"

# Only network tests
uv run pytest -m "requires_network"
```

---

## Completion

When ALL items in PROGRESS.md are checked AND all quality gates pass, exit cleanly.
The loop operator verifies via PROGRESS.md state, not output parsing.

**A++ Standard means:**
- ALL PROGRESS.md items are `[x]`
- ALL SPEC-* items have `[REVIEWED]` markers
- ALL spec acceptance criteria are satisfied
- ALL quality gates pass
- Clean git working tree
