#!/usr/bin/env bash
# Ralph Wiggum Loop Runner (First Principles)
#
# Usage: ./scripts/ralph-loop.sh
#
# The Ralph Wiggum technique: same prompt repeated until done.
# State lives in files (PROGRESS.md), not in context.
#
# Monitor in another terminal:
#   tail -f logs/ralph/iteration_*.log
#   watch -n5 'git log --oneline -5'

set -euo pipefail

cd "$(dirname "$0")/.."

MAX="${MAX:-50}"
ITER_TIMEOUT="${ITER_TIMEOUT:-600}"

dirty_paths() {
  {
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
  } | sort -u | sed '/^$/d'
}

try_finalize_sprint_docs() {
  local log="$1"

  local paths=""
  paths="$(dirty_paths || true)"

  if [[ -z "${paths}" ]]; then
    return 0
  fi

  local disallowed=""
  disallowed="$(printf '%s\n' "${paths}" | grep -Ev '^(docs/|PROGRESS\.md)$' || true)"
  if [[ -n "${disallowed}" ]]; then
    {
      echo ""
      echo "ERROR: Sprint complete but repo dirty (non-doc files changed)."
      echo "       Refusing to auto-commit. Inspect and recover manually:"
      echo "         git status --porcelain=v1"
      echo "         git diff"
      echo ""
      echo "Dirty paths:"
      printf '%s\n' "${paths}"
    } >> "${log}"
    return 1
  fi

  {
    echo ""
    echo "INFO: Sprint complete but repo dirty (docs/PROGRESS only). Finalizing sprint docs..."
    echo ""
  } >> "${log}"

  if ! git add PROGRESS.md docs >> "${log}" 2>&1; then
    echo "ERROR: Failed to stage sprint docs/PROGRESS for finalization." >> "${log}"
    return 1
  fi

  if git diff --cached --quiet 2>/dev/null; then
    echo "ERROR: No staged changes after staging sprint docs/PROGRESS." >> "${log}"
    return 1
  fi

  if ! git commit -m "docs: finalize sprint state" >> "${log}" 2>&1; then
    echo "ERROR: Failed to commit sprint finalization docs." >> "${log}"
    return 1
  fi

  if ! git push >> "${log}" 2>&1; then
    echo "ERROR: Failed to push sprint finalization docs." >> "${log}"
    return 1
  fi

  echo "INFO: Sprint docs finalized and pushed." >> "${log}"
  return 0
}

# Find timeout command (macOS needs gtimeout from coreutils)
if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
else
    echo "ERROR: Missing timeout command." >&2
    echo "  macOS: brew install coreutils" >&2
    echo "  Linux: timeout should be available" >&2
    exit 1
fi

echo "=== Ralph Wiggum Loop ==="
echo "Branch: $(git branch --show-current)"
echo "Max iterations: $MAX"
echo "Iteration timeout: ${ITER_TIMEOUT}s"
echo ""
echo "Monitor: tail -f logs/ralph/iteration_*.log"
echo "Watchdog: ./scripts/ralph-watchdog.sh"
echo ""

if ! grep -q "^\- \[ \]" PROGRESS.md; then
    if [[ -n "$(git status --porcelain)" ]]; then
        mkdir -p logs/ralph
        log="logs/ralph/recovery.log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sprint complete but repo dirty. Attempting recovery..." >> "${log}"
        if ! try_finalize_sprint_docs "${log}"; then
            echo "ERROR: Sprint complete but repo dirty. See ${log}." >&2
            exit 1
        fi
    fi

    echo "All tasks complete (no unchecked items in PROGRESS.md). Exiting."
    exit 0
fi

rm -rf logs/ralph 2>/dev/null || true
mkdir -p logs/ralph

for i in $(seq 1 "$MAX"); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"

    echo "=== Iteration $i/$MAX ===" >> "$log"
    start_msg="[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration $i/$MAX"
    echo "$start_msg" >> "$log"
    echo "$start_msg"

    # Run claude - output goes to file (reduces EPIPE risk from piping; timeouts can still trigger EPIPE)
    "$TIMEOUT_CMD" "$ITER_TIMEOUT" claude --dangerously-skip-permissions \
        -p "$(cat PROMPT.md)" >> "$log" 2>&1 || {
        exit_code=$?
        exit_msg="[$(date '+%Y-%m-%d %H:%M:%S')] Iteration $i/$MAX exited with code $exit_code"
        echo "$exit_msg" >> "$log"
        echo "$exit_msg"
    }

    # GUARDRAIL: Check for staged-but-uncommitted changes (FP-007)
    # If the iteration timed out or crashed after staging but before committing,
    # warn loudly so we don't lose work
    if git diff --cached --quiet 2>/dev/null; then
        : # No staged changes, all good
    else
        {
            echo ""
            echo "WARNING: Staged but uncommitted changes detected!"
            echo "    The iteration may have timed out before committing."
            echo "    Run 'git status' and 'git diff --cached' to inspect."
            echo "    Consider committing manually: git commit -m 'WIP: iteration $i incomplete'"
            echo ""
        } >> "$log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Staged but uncommitted changes! Check logs/ralph/iteration_${n}.log"
    fi

    # Check completion
    if ! grep -q "^\- \[ \]" PROGRESS.md; then
        # Guardrail: Never exit "successfully" with a dirty working tree.
        # If the only remaining changes are docs/PROGRESS, auto-commit them as a recovery step.
        if [[ -n "$(git status --porcelain)" ]]; then
            if ! try_finalize_sprint_docs "$log"; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: PROGRESS complete but repo dirty. Inspect logs/ralph/iteration_${n}.log"
                exit 1
            fi
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] All tasks complete!"
        echo "All tasks complete!" >> "$log"
        break
    fi

    sleep 2
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ralph loop finished."
