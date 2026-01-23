#!/usr/bin/env bash
#
# Ralph Wiggum Watchdog (Overnight Monitoring)
#
# Runs alongside `scripts/ralph-loop.sh` and watches for:
# - stalled iteration logs (likely hung process)
# - guardrail errors/warnings in iteration logs
# - dirty working tree at completion time
#
# Intended usage (in another tmux pane):
#   ./scripts/ralph-watchdog.sh
#
# Environment variables:
#   SESSION_NAME   tmux session to watch (default: erdos-ralph)
#   MAX_AGE        seconds without log updates before failing (default: 900)
#   POLL           polling interval seconds (default: 30)
#   DURATION       total run seconds (default: 28800 = 8 hours)
#
# Output:
#   Appends status + any detected issues to logs/ralph/watchdog.log

set -euo pipefail

cd "$(dirname "$0")/.."

SESSION_NAME="${SESSION_NAME:-erdos-ralph}"
MAX_AGE="${MAX_AGE:-900}"
POLL="${POLL:-30}"
DURATION="${DURATION:-28800}"

LOG_DIR="logs/ralph"
OUT_LOG="${LOG_DIR}/watchdog.log"

mkdir -p "${LOG_DIR}"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

stat_mtime() {
  local path="$1"
  if stat -f %m "$path" >/dev/null 2>&1; then
    stat -f %m "$path"
  else
    stat -c %Y "$path"
  fi
}

latest_iteration_log() {
  ls -1 "${LOG_DIR}"/iteration_*.log 2>/dev/null | sort | tail -n 1 || true
}

issue_patterns() {
  cat <<'EOF'
ERROR: PROGRESS\.md indicates completion but git working tree is dirty
WARNING: Staged but uncommitted changes detected
To fix:
FAILED:
Traceback
make: \*\*\*
EOF
}

echo "[$(timestamp)] watchdog start (duration=${DURATION}s, poll=${POLL}s, max_age=${MAX_AGE}s, session=${SESSION_NAME})" >> "${OUT_LOG}"

start_epoch="$(date +%s)"
last_seen_log=""

while true; do
  now_epoch="$(date +%s)"
  if (( now_epoch - start_epoch >= DURATION )); then
    echo "[$(timestamp)] watchdog finished (duration reached)" >> "${OUT_LOG}"
    exit 0
  fi

  if command -v tmux >/dev/null 2>&1; then
    if ! tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
      echo "[$(timestamp)] watchdog exit (tmux session not found: ${SESSION_NAME})" >> "${OUT_LOG}"
      exit 0
    fi
  fi

  latest="$(latest_iteration_log)"
  if [[ -z "${latest}" ]]; then
    echo "[$(timestamp)] waiting: no iteration logs yet" >> "${OUT_LOG}"
    sleep "${POLL}"
    continue
  fi

  if [[ "${latest}" != "${last_seen_log}" ]]; then
    echo "[$(timestamp)] now watching: ${latest}" >> "${OUT_LOG}"
    last_seen_log="${latest}"
  fi

  mtime="$(stat_mtime "${latest}")"
  age="$(( now_epoch - mtime ))"
  if (( age > MAX_AGE )); then
    {
      echo "[$(timestamp)] ERROR: iteration log appears stale (age=${age}s > ${MAX_AGE}s): ${latest}"
      echo "---- tail(${latest}) ----"
      tail -n 200 "${latest}" || true
      echo "---- git status --porcelain ----"
      git status --porcelain || true
      echo "---- end ----"
    } >> "${OUT_LOG}"
    exit 1
  fi

  if command -v rg >/dev/null 2>&1; then
    patterns="$(issue_patterns)"
    if rg -n -S -f <(printf '%s\n' "${patterns}") "${latest}" >/dev/null 2>&1; then
      {
        echo "[$(timestamp)] ERROR: issue pattern detected in ${latest}"
        rg -n -S -f <(printf '%s\n' "${patterns}") "${latest}" || true
        echo "---- tail(${latest}) ----"
        tail -n 200 "${latest}" || true
        echo "---- git status --porcelain ----"
        git status --porcelain || true
        echo "---- end ----"
      } >> "${OUT_LOG}"
      exit 1
    fi
  fi

  sleep "${POLL}"
done
