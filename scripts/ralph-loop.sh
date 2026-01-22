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
echo ""

rm -rf logs/ralph 2>/dev/null || true
mkdir -p logs/ralph

for i in $(seq 1 "$MAX"); do
    n=$(printf "%03d" "$i")
    log="logs/ralph/iteration_${n}.log"

    echo "=== Iteration $i/$MAX ===" >> "$log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration $i/$MAX"

    # Run claude - output goes to file, no piping (avoids EPIPE)
    "$TIMEOUT_CMD" "$ITER_TIMEOUT" claude --dangerously-skip-permissions \
        -p "$(cat PROMPT.md)" >> "$log" 2>&1 || {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iteration $i exited with code $?"
    }

    # GUARDRAIL: Check for staged-but-uncommitted changes (FP-007)
    # If the iteration timed out or crashed after staging but before committing,
    # warn loudly so we don't lose work
    if git diff --cached --quiet 2>/dev/null; then
        : # No staged changes, all good
    else
        echo "" >> "$log"
        echo "WARNING: Staged but uncommitted changes detected!" >> "$log"
        echo "    The iteration may have timed out before committing." >> "$log"
        echo "    Run 'git status' and 'git diff --cached' to inspect." >> "$log"
        echo "    Consider committing manually: git commit -m 'WIP: iteration $i incomplete'" >> "$log"
        echo "" >> "$log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Staged but uncommitted changes! Check logs/ralph/iteration_${n}.log"
    fi

    # Check completion
    if ! grep -q "^\- \[ \]" PROGRESS.md; then
        # Guardrail: Never exit "successfully" with a dirty working tree.
        # This catches cases where PROGRESS.md was edited but docs were not committed,
        # or other changes were left unstaged/uncommitted.
        if [[ -n "$(git status --porcelain)" ]]; then
            echo "" >> "$log"
            echo "ERROR: PROGRESS.md indicates completion but git working tree is dirty." >> "$log"
            echo "       Refusing to exit cleanly to avoid losing work." >> "$log"
            echo "       Run 'git status' to inspect and commit/push outstanding changes." >> "$log"
            echo "" >> "$log"
            git status --porcelain >> "$log" || true
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: PROGRESS complete but repo dirty. Inspect logs/ralph/iteration_${n}.log"
            exit 1
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] All tasks complete!"
        echo "All tasks complete!" >> "$log"
        break
    fi

    sleep 2
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ralph loop finished."
