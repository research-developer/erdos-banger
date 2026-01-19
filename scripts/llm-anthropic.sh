#!/usr/bin/env bash
# LLM wrapper for erdos CLI - calls Anthropic API.
# Reads prompt from stdin, writes response to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load environment (optional, local-only).
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY not set}"
: "${ANTHROPIC_MODEL:=claude-sonnet-4-20250514}"
: "${ANTHROPIC_MAX_TOKENS:=4096}"

BUILD_PAYLOAD_PY=$(cat <<'PY'
import json
import os
import sys

prompt = sys.stdin.read()
model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096"))

payload = {
    "model": model,
    "max_tokens": max_tokens,
    "messages": [{"role": "user", "content": prompt}],
}

json.dump(payload, sys.stdout)
PY
)

PARSE_RESPONSE_PY=$(cat <<'PY'
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("Non-JSON response from Anthropic API:", file=sys.stderr)
    print(raw[:4000], file=sys.stderr)
    raise SystemExit(1)

if isinstance(data, dict) and "error" in data:
    err = data["error"]
    if isinstance(err, dict) and "message" in err:
        print(err["message"], file=sys.stderr)
        raise SystemExit(1)
    print("Anthropic API error:", data, file=sys.stderr)
    raise SystemExit(1)

try:
    # Anthropic returns content as a list of blocks
    content = data["content"]
    text_parts = [block["text"] for block in content if block.get("type") == "text"]
    print("".join(text_parts))
except Exception:
    print("Unexpected response shape:", file=sys.stderr)
    print(raw[:4000], file=sys.stderr)
    raise SystemExit(1)
PY
)

python3 -c "$BUILD_PAYLOAD_PY" \
  | curl -sS "https://api.anthropic.com/v1/messages" \
      -H "x-api-key: ${ANTHROPIC_API_KEY}" \
      -H "anthropic-version: 2023-06-01" \
      -H "Content-Type: application/json" \
      -d @- \
  | python3 -c "$PARSE_RESPONSE_PY"
