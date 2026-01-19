#!/usr/bin/env bash
# LLM wrapper for erdos CLI - OpenAI Responses API.
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

: "${OPENAI_API_KEY:?OPENAI_API_KEY not set}"
: "${OPENAI_MODEL:=gpt-5.2}"
: "${OPENAI_REASONING_EFFORT:=xhigh}"
: "${OPENAI_BASE_URL:=https://api.openai.com}"

BUILD_PAYLOAD_PY=$(cat <<'PY'
import json
import os
import sys

prompt = sys.stdin.read()
model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
effort = os.environ.get("OPENAI_REASONING_EFFORT")

payload: dict[str, object] = {
    "model": model,
    "input": [{"role": "user", "content": prompt}],
}
if effort:
    payload["reasoning"] = {"effort": effort}

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
    print("Non-JSON response from OpenAI API:", file=sys.stderr)
    print(raw[:4000], file=sys.stderr)
    raise SystemExit(1)

err = data.get("error") if isinstance(data, dict) else None
if err is not None:
    # Some successful Responses API payloads include `"error": null`.
    if err:
        if isinstance(err, dict) and "message" in err:
            print(err["message"], file=sys.stderr)
            raise SystemExit(1)
        print("OpenAI API error", file=sys.stderr)
        raise SystemExit(1)

if isinstance(data, dict) and isinstance(data.get("output_text"), str):
    print(data["output_text"])
    raise SystemExit(0)

parts: list[str] = []
out = data.get("output") if isinstance(data, dict) else None
if isinstance(out, list):
    for item in out:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                parts.append(c["text"])

if parts:
    print("".join(parts))
    raise SystemExit(0)

print("Unexpected response shape:", file=sys.stderr)
print(raw[:4000], file=sys.stderr)
raise SystemExit(1)
PY
)

python3 -c "$BUILD_PAYLOAD_PY" \
  | curl -sS --max-time 120 "${OPENAI_BASE_URL}/v1/responses" \
      -H "Authorization: Bearer ${OPENAI_API_KEY}" \
      -H "Content-Type: application/json" \
      -d @- \
  | python3 -c "$PARSE_RESPONSE_PY"
