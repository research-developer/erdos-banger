#!/usr/bin/env bash
# LLM wrapper for erdos CLI - calls OpenAI Responses API.
# Reads prompt from stdin, writes response to stdout.
# Uses Responses API to support GPT-5.2 with reasoning.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load environment from .env file
if [[ -f "${REPO_ROOT}/.env" ]]; then
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    # Remove any trailing comments from value
    value="${value%%#*}"
    # Trim whitespace
    value="${value%"${value##*[![:space:]]}"}"
    export "$key=$value"
  done < "${REPO_ROOT}/.env"
fi

: "${OPENAI_API_KEY:?OPENAI_API_KEY not set}"
: "${OPENAI_MODEL:=gpt-5.2}"
: "${OPENAI_REASONING_EFFORT:=xhigh}"

# Read prompt from stdin into variable
PROMPT_TEXT=$(cat)

# Build payload via Python (handles escaping properly)
PAYLOAD=$(echo "$PROMPT_TEXT" | OPENAI_MODEL="$OPENAI_MODEL" OPENAI_REASONING_EFFORT="$OPENAI_REASONING_EFFORT" python3 -c '
import json
import os
import sys

prompt = sys.stdin.read()
model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
effort = os.environ.get("OPENAI_REASONING_EFFORT", "xhigh")

payload = {
    "model": model,
    "input": [{"role": "user", "content": prompt}],
}
if effort:
    payload["reasoning"] = {"effort": effort}

print(json.dumps(payload))
')

# Call API
RESPONSE=$(curl -sS "https://api.openai.com/v1/responses" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# Parse response via Python
echo "$RESPONSE" | python3 -c '
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(f"Non-JSON response: {raw[:500]}", file=sys.stderr)
    sys.exit(1)

if "error" in data:
    err = data["error"]
    msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
    print(msg, file=sys.stderr)
    sys.exit(1)

output = data.get("output", [])
for item in output:
    if item.get("type") == "message":
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                print(content.get("text", ""))
'
