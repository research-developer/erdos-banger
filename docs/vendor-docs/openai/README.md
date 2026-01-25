# OpenAI (Vendor Notes)

`erdos-banger` intentionally **does not vendor an OpenAI SDK**. Instead, it integrates via a **subprocess wrapper** (`ERDOS_LLM_COMMAND`) so CI and contributors do not require API dependencies or keys.

## API Surface (for wrapper scripts)

- Endpoint: `POST https://api.openai.com/v1/responses`
- Auth: `Authorization: Bearer $OPENAI_API_KEY`
- Input: prompt text via the `input` field
- Optional: reasoning controls via `reasoning.effort` (model-dependent)

Docs: https://platform.openai.com/docs/api-reference/responses/create

## Security

- Never commit API keys. Keep them in local `.env` (gitignored).
- Wrapper scripts should read prompt from stdin and write only the model response to stdout (errors to stderr).

## Testing Guidance

- Use `scripts/llm-mock.sh` (or similar) in CI to keep tests deterministic.
- Unit tests should mock the subprocess boundary, not internal prompt composition.
