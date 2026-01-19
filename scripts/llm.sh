#!/usr/bin/env bash
# Default LLM wrapper entrypoint for erdos.
# Delegates to a concrete provider script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/llm-openai.sh"
