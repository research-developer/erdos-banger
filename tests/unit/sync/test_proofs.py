"""Tests for proof verification (SPEC-035).

These tests verify the proofs.py module functionality using offline fixtures.
Tests that require actual git cloning or lake builds are marked with requires_lean.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erdos.core.sync.models import ProofLink, VerificationStatus, VerificationStrength
from erdos.core.sync.proofs import (
    CloneResult,
    VerificationResult,
    _find_problem_files,
    _read_toolchain,
    _sanitize_env,
    _truncate_log,
    clone_repository,
    create_provenance,
    save_provenance,
    save_verification_log,
    verify_proof,
)


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "proof_repo"


@pytest.fixture
def proof_link() -> ProofLink:
    """Sample proof link for testing."""
    return ProofLink(
        url="https://github.com/test/erdos-347-proof",
        author="testuser",
        lean_version_hint="Lean 4.3.0",
    )


@pytest.fixture
def repo_with_sorry(tmp_path: Path) -> Path:
    """Create a copy of the with_sorry fixture repo."""
    src = FIXTURES_DIR / "with_sorry"
    dest = tmp_path / "repo_with_sorry"
    shutil.copytree(src, dest)
    return dest


@pytest.fixture
def repo_no_sorry(tmp_path: Path) -> Path:
    """Create a copy of the no_sorry fixture repo."""
    src = FIXTURES_DIR / "no_sorry"
    dest = tmp_path / "repo_no_sorry"
    shutil.copytree(src, dest)
    return dest


# =============================================================================
# Unit tests - Pure functions
# =============================================================================


class TestSanitizeEnv:
    """Tests for environment sanitization."""

    def test_strips_api_keys(self) -> None:
        """API keys are stripped from environment."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "secret", "PATH": "/usr/bin", "HOME": "/home/test"},
        ):
            env = _sanitize_env()
            assert "OPENAI_API_KEY" not in env
            assert "PATH" in env
            assert "HOME" in env

    def test_strips_keys_with_suffix(self) -> None:
        """Keys ending with _API_KEY, _TOKEN, _SECRET are stripped."""
        with patch.dict(
            os.environ,
            {
                "MY_CUSTOM_API_KEY": "secret1",
                "GITHUB_TOKEN": "secret2",
                "DB_SECRET": "secret3",
                "SAFE_VAR": "visible",
            },
        ):
            env = _sanitize_env()
            assert "MY_CUSTOM_API_KEY" not in env
            assert "GITHUB_TOKEN" not in env
            assert "DB_SECRET" not in env
            assert "SAFE_VAR" in env


class TestTruncateLog:
    """Tests for log truncation."""

    def test_short_log_unchanged(self) -> None:
        """Short logs are not truncated."""
        log = "Short log content"
        assert _truncate_log(log) == log

    def test_long_log_truncated(self) -> None:
        """Long logs are truncated with notice."""
        log = "x" * 200_000
        truncated = _truncate_log(log, max_size=1000)
        assert len(truncated) <= 1100  # Max size plus truncation notice
        assert "[... log truncated ...]" in truncated

    def test_exact_max_size_unchanged(self) -> None:
        """Logs exactly at max size are not truncated."""
        log = "x" * 1000
        truncated = _truncate_log(log, max_size=1000)
        assert truncated == log


class TestReadToolchain:
    """Tests for reading lean-toolchain file."""

    def test_reads_toolchain(self, repo_with_sorry: Path) -> None:
        """Reads toolchain from fixture repo."""
        toolchain = _read_toolchain(repo_with_sorry)
        assert toolchain == "leanprover/lean4:v4.12.0"

    def test_missing_toolchain_returns_none(self, tmp_path: Path) -> None:
        """Returns None when toolchain file missing."""
        assert _read_toolchain(tmp_path) is None


class TestFindProblemFiles:
    """Tests for finding problem-specific Lean files."""

    def test_finds_problem_file(self, repo_with_sorry: Path) -> None:
        """Finds Problem347.lean in fixture repo."""
        files = _find_problem_files(repo_with_sorry, 347)
        assert len(files) >= 1
        assert any("Problem347" in str(f) for f in files)

    def test_no_match_returns_empty(self, tmp_path: Path) -> None:
        """Returns empty list when no matching files."""
        files = _find_problem_files(tmp_path, 999)
        assert files == []


# =============================================================================
# Unit tests - Clone operations (mocked)
# =============================================================================


class TestCloneRepository:
    """Tests for repository cloning (mocked subprocess)."""

    def test_rejects_non_https(self, tmp_path: Path) -> None:
        """Rejects non-HTTPS URLs."""
        result = clone_repository("git@github.com:user/repo", tmp_path / "dest")
        assert result.success is False
        assert "HTTPS" in (result.error or "")

    def test_successful_clone(self, tmp_path: Path) -> None:
        """Successful clone returns commit hash."""
        mock_clone = MagicMock(returncode=0, stdout="", stderr="")
        mock_rev = MagicMock(returncode=0, stdout="abc123def456\n", stderr="")

        with patch("erdos.core.sync.proofs.subprocess.run") as mock_run:
            mock_run.side_effect = [mock_clone, mock_rev]
            result = clone_repository("https://github.com/user/repo", tmp_path / "dest")

        assert result.success is True
        assert result.commit == "abc123def456"

    def test_failed_clone(self, tmp_path: Path) -> None:
        """Failed clone returns error message."""
        mock_result = MagicMock(returncode=1, stdout="", stderr="fatal: repo not found")

        with patch("erdos.core.sync.proofs.subprocess.run", return_value=mock_result):
            result = clone_repository(
                "https://github.com/user/nonexistent", tmp_path / "dest"
            )

        assert result.success is False
        assert "repo not found" in (result.error or "")

    def test_clone_timeout(self, tmp_path: Path) -> None:
        """Clone timeout is handled."""
        import subprocess

        with patch(
            "erdos.core.sync.proofs.subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 60),
        ):
            result = clone_repository(
                "https://github.com/user/repo", tmp_path / "dest", timeout=60
            )

        assert result.success is False
        assert "timed out" in (result.error or "").lower()


# =============================================================================
# Unit tests - Verification results
# =============================================================================


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        result = VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            strength=VerificationStrength.NONE,
        )
        assert result.error is None
        assert result.repo_commit is None
        assert result.verified_files == []


class TestCloneResult:
    """Tests for CloneResult dataclass."""

    def test_failed_result(self) -> None:
        """Failed clone result."""
        result = CloneResult(success=False, error="Connection refused")
        assert result.success is False
        assert result.path is None


# =============================================================================
# Unit tests - Provenance management
# =============================================================================


class TestCreateProvenance:
    """Tests for creating provenance records."""

    def test_creates_unverified_provenance(self, proof_link: ProofLink) -> None:
        """Creates provenance without verification."""
        provenance = create_provenance(347, proof_link)

        assert provenance.problem_id == 347
        assert provenance.repo_url == proof_link.url
        assert provenance.posted_by == "testuser"
        assert provenance.verification_status == VerificationStatus.UNVERIFIED
        assert provenance.verification_strength == VerificationStrength.NONE

    def test_creates_verified_provenance(self, proof_link: ProofLink) -> None:
        """Creates provenance with verification result."""
        verification = VerificationResult(
            status=VerificationStatus.VERIFIED,
            strength=VerificationStrength.NO_SORRIES,
            repo_commit="abc123",
            toolchain="leanprover/lean4:v4.3.0",
            verified_files=["Problem347.lean"],
        )

        provenance = create_provenance(347, proof_link, verification)

        assert provenance.verification_status == VerificationStatus.VERIFIED
        assert provenance.verification_strength == VerificationStrength.NO_SORRIES
        assert provenance.repo_commit == "abc123"
        assert provenance.toolchain == "leanprover/lean4:v4.3.0"
        assert provenance.verified_files == ["Problem347.lean"]


class TestSaveProvenance:
    """Tests for saving provenance to disk."""

    def test_saves_provenance_json(self, proof_link: ProofLink, tmp_path: Path) -> None:
        """Saves provenance as JSON."""
        provenance = create_provenance(347, proof_link)
        output_path = save_provenance(provenance, cache_dir=tmp_path)

        assert output_path.exists()
        assert output_path.name == "provenance.json"

        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["problem_id"] == 347
        assert data["repo_url"] == proof_link.url

    def test_creates_problem_directory(
        self, proof_link: ProofLink, tmp_path: Path
    ) -> None:
        """Creates problem-specific directory."""
        provenance = create_provenance(347, proof_link)
        save_provenance(provenance, cache_dir=tmp_path)

        assert (tmp_path / "347").is_dir()
        assert (tmp_path / "347" / "provenance.json").exists()


class TestSaveVerificationLog:
    """Tests for saving verification logs."""

    def test_saves_log_file(self, tmp_path: Path) -> None:
        """Saves verification log to disk."""
        log_content = "Build succeeded!\n\nAll targets built successfully."
        output_path = save_verification_log(347, log_content, cache_dir=tmp_path)

        assert output_path.exists()
        assert output_path.name == "verify.log"
        assert output_path.read_text(encoding="utf-8") == log_content


# =============================================================================
# Unit tests - verify_proof (mocked)
# =============================================================================


class TestVerifyProof:
    """Tests for the main verify_proof function (mocked)."""

    def test_source_unavailable_on_clone_failure(
        self, proof_link: ProofLink, tmp_path: Path
    ) -> None:
        """Returns source_unavailable when clone fails."""
        with patch(
            "erdos.core.sync.proofs.clone_repository",
            return_value=CloneResult(success=False, error="Connection refused"),
        ):
            result = verify_proof(proof_link, 347, work_dir=tmp_path)

        assert result.status == VerificationStatus.SOURCE_UNAVAILABLE
        assert result.strength == VerificationStrength.NONE
        assert "Connection refused" in (result.error or "")

    def test_failed_on_build_failure(
        self, proof_link: ProofLink, tmp_path: Path
    ) -> None:
        """Returns failed when lake build fails."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        with (
            patch(
                "erdos.core.sync.proofs.clone_repository",
                return_value=CloneResult(success=True, path=repo_dir, commit="abc123"),
            ),
            patch(
                "erdos.core.sync.proofs.run_lake_build",
                return_value=(False, "Build failed: missing dependency"),
            ),
            patch("erdos.core.sync.proofs._read_toolchain", return_value=None),
        ):
            result = verify_proof(proof_link, 347, work_dir=tmp_path)

        assert result.status == VerificationStatus.FAILED
        assert result.repo_commit == "abc123"
        assert "lake build failed" in (result.error or "")

    def test_inconclusive_when_no_problem_files(
        self, proof_link: ProofLink, tmp_path: Path
    ) -> None:
        """Returns inconclusive when build passes but no problem files found."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        with (
            patch(
                "erdos.core.sync.proofs.clone_repository",
                return_value=CloneResult(success=True, path=repo_dir, commit="abc123"),
            ),
            patch(
                "erdos.core.sync.proofs.run_lake_build",
                return_value=(True, "Build succeeded"),
            ),
            patch(
                "erdos.core.sync.proofs._read_toolchain", return_value="lean4:v4.3.0"
            ),
            patch("erdos.core.sync.proofs._find_problem_files", return_value=[]),
        ):
            result = verify_proof(proof_link, 347, work_dir=tmp_path)

        assert result.status == VerificationStatus.INCONCLUSIVE
        assert result.strength == VerificationStrength.BUILD_ONLY
        assert result.toolchain == "lean4:v4.3.0"

    def test_verified_when_no_sorries(
        self, proof_link: ProofLink, tmp_path: Path
    ) -> None:
        """Returns verified when no sorries found."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        problem_file = repo_dir / "Problem347.lean"
        problem_file.touch()

        with (
            patch(
                "erdos.core.sync.proofs.clone_repository",
                return_value=CloneResult(success=True, path=repo_dir, commit="abc123"),
            ),
            patch(
                "erdos.core.sync.proofs.run_lake_build",
                return_value=(True, "Build succeeded"),
            ),
            patch(
                "erdos.core.sync.proofs._read_toolchain", return_value="lean4:v4.3.0"
            ),
            patch(
                "erdos.core.sync.proofs._find_problem_files",
                return_value=[problem_file],
            ),
            patch(
                "erdos.core.sync.proofs.check_no_sorries",
                return_value=(True, "No sorries found"),
            ),
        ):
            result = verify_proof(proof_link, 347, work_dir=tmp_path)

        assert result.status == VerificationStatus.VERIFIED
        assert result.strength == VerificationStrength.NO_SORRIES
        assert "Problem347.lean" in result.verified_files

    def test_temp_directory_cleanup(self, proof_link: ProofLink) -> None:
        """Temp directory is cleaned up after verification."""
        with (
            patch(
                "erdos.core.sync.proofs.clone_repository",
                return_value=CloneResult(success=False, error="Failed"),
            ),
            patch("erdos.core.sync.proofs.tempfile.mkdtemp") as mock_mkdtemp,
            patch("erdos.core.sync.proofs.shutil.rmtree") as mock_rmtree,
        ):
            mock_mkdtemp.return_value = "/tmp/erdos_verify_347_abc123"  # noqa: S108

            # Need to mock Path.exists to return True for cleanup
            with patch("erdos.core.sync.proofs.Path.exists", return_value=True):
                verify_proof(proof_link, 347)

            mock_rmtree.assert_called()
