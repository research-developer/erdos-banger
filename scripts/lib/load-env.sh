#!/usr/bin/env bash
# Shared .env file loader for erdos LLM wrapper scripts.
# Source this file to get load_env_file() function.
#
# Usage:
#   source "${SCRIPT_DIR}/lib/load-env.sh"
#   load_env_file "/path/to/.env"
#
# Limitations:
#   - Only supports simple KEY=value lines
#   - Strips inline comments (# after value)
#   - Handles single/double quoted values
#   - Does NOT support multiline values
#   - Does NOT support shell expansion ($VAR, ${VAR})

# load_env_file: Load and export variables from a .env file
#
# Args:
#   $1: Path to .env file (optional - returns 0 if file doesn't exist)
#
# Returns:
#   0: Success (even if file doesn't exist)
#   Non-zero: Read error
load_env_file() {
  local env_file="$1"
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue

    # Split on first '='
    local key="${line%%=*}"
    local value="${line#*=}"

    # Trim whitespace from key
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    # Strip optional leading "export " from key
    if [[ "$key" =~ ^export[[:space:]]+ ]]; then
      key="${key#export}"
      key="${key#"${key%%[![:space:]]*}"}"
      key="${key%"${key##*[![:space:]]}"}"
    fi

    # Validate key to avoid `export` failures under set -e
    if [[ -z "$key" ]] || ! [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi

    # Trim whitespace from value
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    # Remove surrounding quotes if present (bash 3.2 compatible).
    # Only strip inline comments for unquoted values so quoted strings like
    # FOO="a#b" round-trip correctly.
    if [[ "$value" =~ ^\".*\"$ ]] || [[ "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    else
      # Strip inline comments for unquoted values and trim again.
      value="${value%%#*}"
      value="${value#"${value%%[![:space:]]*}"}"
      value="${value%"${value##*[![:space:]]}"}"
    fi

    export "${key}=${value}"
  done < "$env_file"
}
