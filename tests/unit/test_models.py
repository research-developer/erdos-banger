"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from erdos.core.models import (
    CLIOutput,
    LeanCheckResult,
    LeanError,
    ProblemRecord,
    ProblemStatus,
    ReferenceRecord,
)


class TestProblemStatus:
    def test_from_string_standard(self) -> None:
        assert ProblemStatus.from_string("open") == ProblemStatus.OPEN
        assert ProblemStatus.from_string("proved") == ProblemStatus.PROVED

    def test_from_string_variants(self) -> None:
        assert ProblemStatus.from_string("solved") == ProblemStatus.PROVED
        assert ProblemStatus.from_string("proved (Lean)") == ProblemStatus.PROVED
        assert ProblemStatus.from_string("OPEN") == ProblemStatus.OPEN

    def test_from_string_unknown(self) -> None:
        assert ProblemStatus.from_string("gibberish") == ProblemStatus.UNKNOWN


class TestProblemRecord:
    def test_valid_problem(self) -> None:
        problem = ProblemRecord(
            id=1,
            title="Test",
            statement="Prove X",
            status=ProblemStatus.OPEN,
        )
        assert problem.id == 1
        assert problem.prize == 0  # default

    def test_invalid_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ProblemRecord(id=0, title="Test", statement="X", status=ProblemStatus.OPEN)

    def test_roundtrip_json(self) -> None:
        problem = ProblemRecord(
            id=42,
            title="Test Problem",
            statement="Prove that 1+1=2",
            status=ProblemStatus.PROVED,
            tags=["math"],
        )
        json_str = problem.model_dump_json()
        restored = ProblemRecord.model_validate_json(json_str)
        assert restored == problem

    def test_str_representation(self) -> None:
        problem = ProblemRecord(
            id=6,
            title="Small primes",
            statement="...",
            status=ProblemStatus.PROVED,
            prize=100,
        )
        assert str(problem) == "Problem 6: Small primes ($100) [proved]"


class TestReferenceRecord:
    def test_valid_doi(self) -> None:
        ref = ReferenceRecord(doi="10.1007/BF01940595", title="Test")
        assert ref.doi == "10.1007/BF01940595"

    def test_invalid_doi_rejected(self) -> None:
        with pytest.raises(ValidationError, match="String should match pattern"):
            ReferenceRecord(doi="not-a-doi", title="Test")

    def test_best_url_priority(self) -> None:
        ref = ReferenceRecord(
            doi="10.1234/test",
            arxiv_id="2203.00001",
            oa_url="https://example.com/paper.pdf",
            title="Test",
        )
        assert ref.best_url == "https://example.com/paper.pdf"

        ref2 = ReferenceRecord(arxiv_id="2203.00001", title="Test")
        assert ref2.best_url == "https://arxiv.org/abs/2203.00001"


class TestLeanCheckResult:
    def test_success_result(self) -> None:
        result = LeanCheckResult(file="Test.lean", success=True)
        assert result.success
        assert result.error_count == 0

    def test_error_result(self) -> None:
        result = LeanCheckResult(
            file="Test.lean",
            success=False,
            errors=[
                LeanError(file="Test.lean", line=10, column=5, message="type mismatch")
            ],
        )
        assert not result.success
        assert result.error_count == 1

    def test_has_sorry_detection(self) -> None:
        result = LeanCheckResult(
            file="Test.lean",
            success=False,
            errors=[
                LeanError(
                    file="Test.lean",
                    line=10,
                    column=5,
                    message="declaration uses 'sorry'",
                )
            ],
        )
        assert result.has_sorry


class TestCLIOutput:
    def test_ok_output(self) -> None:
        output = CLIOutput.ok("erdos show", {"id": 1})
        assert output.success
        assert output.data == {"id": 1}
        assert output.error is None

    def test_error_output(self) -> None:
        output = CLIOutput.err("erdos show", "NotFound", "Problem not found", code=3)
        assert not output.success
        assert output.error["type"] == "NotFound"
        assert output.error["code"] == 3
