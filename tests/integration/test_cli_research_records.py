"""Integration tests for research records CRUD (Spec 024)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return {"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(tmp_path)}


def test_lead_add_list_update_validate(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    add = runner.invoke(
        app,
        [
            "--json",
            "research",
            "lead",
            "add",
            "6",
            "--title",
            "Green-Tao",
            "--notes",
            "promising",
        ],
        env=env,
    )
    assert add.exit_code == 0, add.stdout
    add_payload = json.loads(add.stdout)
    lead_id = add_payload["data"]["record"]["id"]

    listed = runner.invoke(app, ["--json", "research", "lead", "list", "6"], env=env)
    assert listed.exit_code == 0
    list_payload = json.loads(listed.stdout)
    assert any(r["id"] == lead_id for r in list_payload["data"]["records"])

    upd = runner.invoke(
        app,
        [
            "--json",
            "research",
            "lead",
            "update",
            "6",
            lead_id,
            "--status",
            "dead_end",
            "--notes",
            "no longer relevant",
        ],
        env=env,
    )
    assert upd.exit_code == 0
    upd_payload = json.loads(upd.stdout)
    assert upd_payload["data"]["record"]["status"] == "dead_end"

    valid = runner.invoke(app, ["--json", "research", "validate", "6"], env=env)
    assert valid.exit_code == 0


def test_validate_fails_on_corrupt_yaml(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    # Corrupt a lead record file.
    leads_dir = tmp_path / "research" / "problems" / "0006" / "leads"
    leads_dir.mkdir(parents=True, exist_ok=True)
    (leads_dir / "lead_bad.yaml").write_text("not: [valid\n", encoding="utf-8")

    valid = runner.invoke(app, ["--json", "research", "validate", "6"], env=env)
    assert valid.exit_code != 0
    payload = json.loads(valid.stdout)
    assert payload["command"] == "erdos research validate"
    assert payload["success"] is False
    assert payload["error"]["type"] == "InvalidRecord"
