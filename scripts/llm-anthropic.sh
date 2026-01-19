#!/usr/bin/env bash
# LLM wrapper for erdos CLI - Anthropic Messages API.
# Reads prompt from stdin, writes response text to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"

    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    value="${value%%#*}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "$value" =~ ^\".*\"$ ]]; then
      value="${value:1:-1}"
    elif [[ "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:-1}"
    fi

    export "${key}=${value}"
  done < "$env_file"
}

load_env_file "${REPO_ROOT}/.env"

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY not set}"
: "${ANTHROPIC_MODEL:=claude-opus-4-5-20251101}"
: "${ANTHROPIC_MAX_TOKENS:=1024}"
: "${ANTHROPIC_VERSION:=2023-06-01}"
: "${ANTHROPIC_BASE_URL:=https://api.anthropic.com}"

BUILD_PAYLOAD_PY=$(cat <<'PY'
import json
import os
import sys

prompt = sys.stdin.read()
model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5-20251101")
max_tokens_raw = os.environ.get("ANTHROPIC_MAX_TOKENS", "1024")
try:
    max_tokens = int(max_tokens_raw)
except ValueError:
    max_tokens = 1024

payload: dict[str, object] = {
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

if isinstance(data, dict) and data.get("type") == "error":
    err = data.get("error")
    if isinstance(err, dict) and isinstance(err.get("message"), str):
        print(err["message"], file=sys.stderr)
        raise SystemExit(1)
    print("Anthropic API error", file=sys.stderr)
    raise SystemExit(1)

content = data.get("content") if isinstance(data, dict) else None
parts: list[str] = []
if isinstance(content, list):
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])

if parts:
    print("".join(parts))
    raise SystemExit(0)

print("Unexpected response shape:", file=sys.stderr)
print(raw[:4000], file=sys.stderr)
raise SystemExit(1)
PY
)

python3 -c "$BUILD_PAYLOAD_PY" \
  | curl -sS "${ANTHROPIC_BASE_URL}/v1/messages" \
      -H "x-api-key: ${ANTHROPIC_API_KEY}" \
      -H "anthropic-version: ${ANTHROPIC_VERSION}" \
      -H "Content-Type: application/json" \
      -d @- \
  | python3 -c "$PARSE_RESPONSE_PY"
