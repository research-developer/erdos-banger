"""Integration tests for erdos convert command argument validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


@pytest.fixture
def isolated_convert_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up isolated environment with a dummy PDF file."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"
    monkeypatch.setenv("ERDOS_DATA_PATH", str(fixtures_path.parent))

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% dummy\n")
    return pdf_path


class TestConvertCommand:
    def test_llm_service_requires_use_llm(self, isolated_convert_env: Path) -> None:
        result = runner.invoke(
            app,
            ["--json", "convert", str(isolated_convert_env), "--llm-service", "claude"],
        )
        assert result.exit_code == ExitCode.USAGE_ERROR
        output = json.loads(result.stdout)
        assert output["success"] is False
        assert "--llm-service requires --use-llm" in output["error"]["message"]
