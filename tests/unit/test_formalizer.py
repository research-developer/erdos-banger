"""Unit tests for skeleton generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.models import ProblemRecord, ProblemStatus


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def sample_problem() -> ProblemRecord:
    return ProblemRecord(
        id=6,
        title="Small primes",
        statement="Prove that there are infinitely many primes.",
        status=ProblemStatus.OPEN,
        tags=["number theory"],
    )


class TestGenerateSkeleton:
    def test_creates_lean_file(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """generate_skeleton creates .lean file."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")

        output = generate_skeleton(sample_problem, tmp_path)

        assert output.exists()
        assert output.name == "Problem006.lean"

    def test_file_contains_problem_info(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Generated file contains problem information."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")

        output = generate_skeleton(sample_problem, tmp_path)
        content = output.read_text(encoding="utf-8")

        assert "Problem 6" in content
        assert "Small primes" in content
        assert "sorry" in content  # Has placeholder proof

    def test_raises_if_file_exists(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Raises if file exists and overwrite=False."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")
        (tmp_path / "Erdos" / "Problem006.lean").write_text(
            "-- existing", encoding="utf-8"
        )

        with pytest.raises(FormalizerError, match="already exists"):
            generate_skeleton(sample_problem, tmp_path, overwrite=False)

    def test_overwrites_with_force(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Overwrites file when overwrite=True."""
        (tmp_path / "Erdos").mkdir()
        (tmp_path / "Erdos.lean").write_text("import Erdos.Basic\n", encoding="utf-8")
        (tmp_path / "Erdos" / "Problem006.lean").write_text(
            "-- old content", encoding="utf-8"
        )

        output = generate_skeleton(sample_problem, tmp_path, overwrite=True)

        assert "Small primes" in output.read_text(encoding="utf-8")
