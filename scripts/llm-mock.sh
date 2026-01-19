#!/usr/bin/env bash
# Mock LLM for testing - reads prompt from stdin and emits a fixed response.

set -euo pipefail

input="$(cat)"
bytes="$(printf '%s' "$input" | wc -c | tr -d ' ')"

echo "This is a mock LLM response for testing purposes."
echo "Input received: ${bytes} bytes"
