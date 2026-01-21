# Anthropic (Vendor Notes)

`erdos-banger` integrates with Anthropic via the same subprocess wrapper pattern (`ERDOS_LLM_COMMAND`), not via a Python SDK.

## API Surface (for wrapper scripts)

- Endpoint: `POST https://api.anthropic.com/v1/messages`
- Headers:
  - `x-api-key: $ANTHROPIC_API_KEY`
  - `anthropic-version: <date>`
  - `content-type: application/json`
- Body:
  - `model`
  - `messages` (prompt as a user message)

Docs: https://docs.anthropic.com/en/api/messages-examples

## Security

- Never commit API keys. Keep them in local `.env` (gitignored).
- Wrapper scripts should read prompt from stdin and write only the model response to stdout (errors to stderr).

## Testing Guidance

- Use a deterministic mock wrapper in CI (no network, no keys).
- Mock only the subprocess boundary in Python tests.
