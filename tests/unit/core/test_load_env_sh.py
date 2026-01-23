"""Tests for scripts/lib/load-env.sh shared .env loader.

These tests run offline and validate that the shared shell script
correctly parses .env files.
"""

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest


# Path to project root - computed once at module load
# Note: This relies on test file being at tests/unit/core/test_load_env_sh.py
# which is 4 directories deep from project root.
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_LOAD_ENV_SCRIPT = _PROJECT_ROOT / "scripts" / "lib" / "load-env.sh"

# Full path to bash for security linters
BASH_PATH = "/bin/bash"


@pytest.fixture
def project_root_path() -> Path:
    """Return project root for tests that need it as fixture."""
    return _PROJECT_ROOT


@pytest.fixture
def load_env_script() -> Path:
    """Return path to load-env.sh script."""
    return _LOAD_ENV_SCRIPT


def run_load_env_test(env_content: str, expected_vars: dict[str, str]) -> None:
    """Run load_env_file and verify exported variables.

    Args:
        env_content: Content to write to temp .env file
        expected_vars: Dict of VAR_NAME -> expected_value to verify
    """
    # Build shell script that sources load-env.sh, loads a temp file, and prints vars
    var_prints = "\n".join(f'echo "{k}=${{{k}:-UNSET}}"' for k in expected_vars)

    script = dedent(f'''
        #!/usr/bin/env bash
        set -euo pipefail

        # Create temp .env file
        TEMP_ENV=$(mktemp)
        cat > "$TEMP_ENV" << 'ENVEOF'
{env_content}
ENVEOF

        # Source and run
        source "{_LOAD_ENV_SCRIPT}"
        load_env_file "$TEMP_ENV"

        # Print variables for verification
{var_prints}

        rm -f "$TEMP_ENV"
    ''')

    result = subprocess.run(  # noqa: S603
        [BASH_PATH, "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Parse output
    actual = {}
    for line in result.stdout.strip().split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            actual[key] = value

    for key, expected in expected_vars.items():
        assert actual.get(key) == expected, (
            f"Variable {key}: expected '{expected}', got '{actual.get(key)}'"
        )


class TestLoadEnvFile:
    """Tests for the load_env_file function."""

    def test_simple_key_value(self) -> None:
        """Simple KEY=value parsing."""
        run_load_env_test(
            "MY_VAR=hello",
            {"MY_VAR": "hello"},
        )

    def test_multiple_variables(self) -> None:
        """Multiple variables on separate lines."""
        run_load_env_test(
            dedent("""
                VAR_A=alpha
                VAR_B=beta
                VAR_C=gamma
            """).strip(),
            {"VAR_A": "alpha", "VAR_B": "beta", "VAR_C": "gamma"},
        )

    def test_comment_lines_ignored(self) -> None:
        """Lines starting with # are ignored."""
        run_load_env_test(
            dedent("""
                # This is a comment
                REAL_VAR=value
                # Another comment
            """).strip(),
            {"REAL_VAR": "value"},
        )

    def test_empty_lines_ignored(self) -> None:
        """Empty lines are ignored."""
        run_load_env_test(
            dedent("""
                VAR_ONE=one

                VAR_TWO=two
            """).strip(),
            {"VAR_ONE": "one", "VAR_TWO": "two"},
        )

    def test_inline_comment_stripped(self) -> None:
        """Inline comments after value are stripped."""
        run_load_env_test(
            "MY_KEY=myvalue # this is a comment",
            {"MY_KEY": "myvalue"},
        )

    def test_double_quoted_value(self) -> None:
        """Double-quoted values have quotes stripped."""
        run_load_env_test(
            'QUOTED="hello world"',
            {"QUOTED": "hello world"},
        )

    def test_single_quoted_value(self) -> None:
        """Single-quoted values have quotes stripped."""
        run_load_env_test(
            "QUOTED='hello world'",
            {"QUOTED": "hello world"},
        )

    def test_quoted_value_with_hash(self) -> None:
        """Quoted values should preserve # characters (no inline comment stripping)."""
        run_load_env_test(
            'TOKEN="a#b#c"',
            {"TOKEN": "a#b#c"},
        )

    def test_invalid_key_skipped(self) -> None:
        """Invalid keys should be skipped (avoid export failures)."""
        script = dedent(f'''
            #!/usr/bin/env bash
            set -euo pipefail

            TEMP_ENV=$(mktemp)
            cat > "$TEMP_ENV" << 'ENVEOF'
BAD KEY=value
ENVEOF

            source "{_LOAD_ENV_SCRIPT}"
            load_env_file "$TEMP_ENV"

            rm -f "$TEMP_ENV"
        ''')

        result = subprocess.run(  # noqa: S603
            [BASH_PATH, "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.returncode == 0

    def test_whitespace_trimmed(self) -> None:
        """Whitespace around key and value is trimmed."""
        run_load_env_test(
            "  MY_KEY  =  my value  ",
            {"MY_KEY": "my value"},
        )

    def test_value_with_equals_sign(self) -> None:
        """Value containing = is preserved (split on first = only)."""
        run_load_env_test(
            "URL=https://example.com?foo=bar",
            {"URL": "https://example.com?foo=bar"},
        )

    def test_missing_file_returns_success(self) -> None:
        """Non-existent file returns success (no error)."""
        script = dedent(f'''
            #!/usr/bin/env bash
            set -euo pipefail
            source "{_LOAD_ENV_SCRIPT}"
            load_env_file "/nonexistent/path/.env"
            echo "SUCCESS"
        ''')

        result = subprocess.run(  # noqa: S603
            [BASH_PATH, "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.returncode == 0
        assert "SUCCESS" in result.stdout


class TestScriptIntegration:
    """Integration tests verifying scripts can be sourced."""

    def test_load_env_script_exists(self, load_env_script: Path) -> None:
        """Verify load-env.sh exists at expected location."""
        assert load_env_script.exists(), f"Missing: {load_env_script}"

    def test_load_env_script_is_valid_bash(self, load_env_script: Path) -> None:
        """Verify load-env.sh has valid bash syntax."""
        result = subprocess.run(  # noqa: S603
            [BASH_PATH, "-n", str(load_env_script)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    @pytest.mark.parametrize(
        "script_name",
        ["llm.sh", "llm-openai.sh", "llm-anthropic.sh"],
    )
    def test_wrapper_scripts_source_shared_loader(
        self, project_root_path: Path, script_name: str
    ) -> None:
        """Verify wrapper scripts source the shared load-env.sh."""
        script_path = project_root_path / "scripts" / script_name
        assert script_path.exists(), f"Missing: {script_path}"

        content = script_path.read_text()
        assert 'source "${SCRIPT_DIR}/lib/load-env.sh"' in content, (
            f"{script_name} should source lib/load-env.sh"
        )
        # Should NOT have inline load_env_file function
        assert "load_env_file()" not in content, (
            f"{script_name} should not have inline load_env_file definition"
        )
