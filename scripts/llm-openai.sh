#!/usr/bin/env bash
# LLM wrapper for erdos CLI - calls OpenAI API.
# Reads prompt from stdin, writes response to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load environment (optional, local-only).
# WARNING: This sources a local file as shell code. Keep `.env` to KEY=VALUE lines.
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

: "${OPENAI_API_KEY:?OPENAI_API_KEY not set}"
: "${OPENAI_MODEL:=gpt-5.2}"
: "${OPENAI_REASONING_EFFORT:=high}"
: "${OPENAI_BASE_URL:=https://api.openai.com}"

python - <<'PY' \
  | curl -sS "${OPENAI_BASE_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${OPENAI_API_KEY}" \
      -H "Content-Type: application/json" \
      -d @- \
  | python - <<'PY'
import json
import os
import sys

prompt = sys.stdin.read()
model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
effort = os.environ.get("OPENAI_REASONING_EFFORT")

payload: dict[str, object] = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
}
if effort:
    payload["reasoning"] = {"effort": effort}

json.dump(payload, sys.stdout)
PY
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("Non-JSON response from OpenAI API:", file=sys.stderr)
    print(raw[:4000], file=sys.stderr)
    raise SystemExit(1)

if isinstance(data, dict) and "error" in data:
    err = data["error"]
    if isinstance(err, dict) and "message" in err:
        print(err["message"], file=sys.stderr)
        raise SystemExit(1)
    print("OpenAI API error", file=sys.stderr)
    raise SystemExit(1)

try:
    print(data["choices"][0]["message"]["content"])
except Exception:
    print("Unexpected response shape:", file=sys.stderr)
    print(raw[:4000], file=sys.stderr)
    raise SystemExit(1)
PY
