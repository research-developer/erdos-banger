"""Tests for sync models (SPEC-035)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from erdos.core.sync.models import (
    ProofLink,
    ProofLinksCache,
    ProofProvenance,
    SubmoduleProblemData,
    SubmoduleSyncStatus,
    VerificationStatus,
    VerificationStrength,
    WebsiteProblemData,
    WebsiteReferenceData,
    WebsiteSyncStatus,
)


class TestSubmoduleProblemData:
    """Tests for SubmoduleProblemData model."""

    def test_valid_minimal(self) -> None:
        data = SubmoduleProblemData(problem_id=1, status="open")
        assert data.problem_id == 1
        assert data.status == "open"
        assert data.prize == 0
        assert data.tags == []
        assert data.oeis_ids == []
        assert data.formalized is False

    def test_valid_full(self) -> None:
        data = SubmoduleProblemData(
            problem_id=6,
            status="proved",
            status_last_update="2025-08-31",
            prize=100,
            tags=["number theory", "primes"],
            oeis_ids=["A335277"],
            formalized=True,
            formalized_last_update="2025-09-18",
        )
        assert data.problem_id == 6
        assert data.status == "proved"
        assert data.prize == 100
        assert data.formalized is True
        assert "number theory" in data.tags

    def test_invalid_problem_id(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            SubmoduleProblemData(problem_id=0, status="open")

    def test_negative_prize_rejected(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            SubmoduleProblemData(problem_id=1, status="open", prize=-100)

    def test_frozen(self) -> None:
        data = SubmoduleProblemData(problem_id=1, status="open")
        with pytest.raises(ValidationError):
            data.status = "proved"  # type: ignore[misc]


class TestSubmoduleProblemDataFromUpstream:
    """Tests for SubmoduleProblemData.from_upstream_yaml()."""

    def test_parse_standard_format(self) -> None:
        raw = {
            "number": "6",
            "prize": "$100",
            "status": {"state": "proved", "last_update": "2025-08-31"},
            "oeis": ["A335277"],
            "formalized": {"state": "yes", "last_update": "2025-09-18"},
            "tags": ["number theory", "primes"],
        }
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.problem_id == 6
        assert data.status == "proved"
        assert data.status_last_update == "2025-08-31"
        assert data.prize == 100
        assert data.oeis_ids == ["A335277"]
        assert data.formalized is True
        assert data.formalized_last_update == "2025-09-18"
        assert data.tags == ["number theory", "primes"]

    def test_parse_prize_no(self) -> None:
        raw = {"number": "5", "prize": "no", "status": {"state": "open"}}
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.prize == 0

    def test_parse_prize_numeric(self) -> None:
        raw = {"number": "4", "prize": "$10000", "status": {"state": "proved"}}
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.prize == 10000

    def test_parse_oeis_filters_na(self) -> None:
        raw = {"number": "7", "oeis": ["N/A"], "status": {"state": "open"}}
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.oeis_ids == []

    def test_parse_oeis_mixed(self) -> None:
        raw = {
            "number": "3",
            "oeis": ["A003002", "N/A", "A003003"],
            "status": {"state": "open"},
        }
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.oeis_ids == ["A003002", "A003003"]

    def test_parse_formalized_no(self) -> None:
        raw = {
            "number": "5",
            "formalized": {"state": "no"},
            "status": {"state": "open"},
        }
        data = SubmoduleProblemData.from_upstream_yaml(raw)
        assert data.formalized is False

    def test_parse_missing_number(self) -> None:
        raw = {"prize": "$100", "status": {"state": "open"}}
        with pytest.raises(ValueError, match="Missing required field 'number'"):
            SubmoduleProblemData.from_upstream_yaml(raw)

    def test_parse_invalid_number(self) -> None:
        raw = {"number": "abc", "status": {"state": "open"}}
        with pytest.raises(ValueError, match="Invalid problem number"):
            SubmoduleProblemData.from_upstream_yaml(raw)


class TestSubmoduleSyncStatus:
    """Tests for SubmoduleSyncStatus model."""

    def test_empty_status(self) -> None:
        status = SubmoduleSyncStatus()
        assert status.commit_hash is None
        assert status.synced_at is None
        assert status.problems_count == 0
        assert status.stale is None

    def test_full_status(self) -> None:
        now = datetime.now(UTC)
        status = SubmoduleSyncStatus(
            commit_hash="abc123",
            previous_commit_hash="def456",
            synced_at=now,
            problems_count=1135,
            stale=False,
        )
        assert status.commit_hash == "abc123"
        assert status.previous_commit_hash == "def456"
        assert status.problems_count == 1135
        assert status.stale is False

    def test_roundtrip_json(self) -> None:
        now = datetime.now(UTC)
        status = SubmoduleSyncStatus(
            commit_hash="abc123",
            synced_at=now,
            problems_count=100,
        )
        json_str = status.model_dump_json()
        restored = SubmoduleSyncStatus.model_validate_json(json_str)
        assert restored.commit_hash == status.commit_hash


class TestWebsiteProblemData:
    """Tests for WebsiteProblemData model."""

    def test_valid_minimal(self) -> None:
        data = WebsiteProblemData(problem_id=6)
        assert data.problem_id == 6
        assert data.title is None
        assert data.statement is None
        assert data.tags == []
        assert data.references == []

    def test_valid_full(self) -> None:
        ref = WebsiteReferenceData(
            key="GreenTao2008",
            citation="B. Green, T. Tao, The primes contain...",
            doi="10.4007/annals.2008.167.481",
        )
        data = WebsiteProblemData(
            problem_id=6,
            title="Small primes in arithmetic progressions",
            statement="Let $p_1 < p_2 < \\ldots$ be the sequence of primes...",
            tags=["number theory", "primes"],
            references=[ref],
            status_badge_text="PROVED (LEAN)",
        )
        assert data.title == "Small primes in arithmetic progressions"
        assert len(data.references) == 1
        assert data.references[0].key == "GreenTao2008"


class TestWebsiteReferenceData:
    """Tests for WebsiteReferenceData model."""

    def test_valid_minimal(self) -> None:
        ref = WebsiteReferenceData(key="Er65")
        assert ref.key == "Er65"
        assert ref.citation is None

    def test_valid_full(self) -> None:
        ref = WebsiteReferenceData(
            key="GreenTao2008",
            citation="B. Green, T. Tao (2008)",
            doi="10.4007/annals.2008.167.481",
            arxiv_id="math/0404188",
            url="https://annals.math.princeton.edu/2008/167-2/p03",
        )
        assert ref.doi == "10.4007/annals.2008.167.481"
        assert ref.arxiv_id == "math/0404188"

    def test_empty_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="at least 1 character"):
            WebsiteReferenceData(key="")


class TestWebsiteSyncStatus:
    """Tests for WebsiteSyncStatus model."""

    def test_default_values(self) -> None:
        status = WebsiteSyncStatus(problem_id=6)
        assert status.problem_id == 6
        assert status.fetched_at is None
        assert status.http_status is None
        assert status.parse_success is False
        assert status.warnings == []

    def test_with_error(self) -> None:
        status = WebsiteSyncStatus(
            problem_id=6,
            http_status=403,
            parse_success=False,
            parse_error="Access denied",
        )
        assert status.http_status == 403
        assert status.parse_error == "Access denied"


class TestProofLink:
    """Tests for ProofLink model."""

    def test_valid_minimal(self) -> None:
        link = ProofLink(url="https://github.com/user/proof")
        assert link.url == "https://github.com/user/proof"
        assert link.author is None
        assert link.posted_at is None

    def test_valid_full(self) -> None:
        now = datetime.now(UTC)
        link = ProofLink(
            url="https://github.com/user/erdos-347-proof",
            author="mathprover",
            posted_at=now,
            lean_version_hint="v4.8.0",
        )
        assert link.author == "mathprover"
        assert link.lean_version_hint == "v4.8.0"


class TestProofLinksCache:
    """Tests for ProofLinksCache model."""

    def test_empty_links(self) -> None:
        now = datetime.now(UTC)
        cache = ProofLinksCache(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=now,
        )
        assert cache.problem_id == 347
        assert cache.links == []

    def test_with_links(self) -> None:
        now = datetime.now(UTC)
        link1 = ProofLink(url="https://github.com/user1/proof")
        link2 = ProofLink(url="https://github.com/user2/proof")
        cache = ProofLinksCache(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=now,
            links=[link1, link2],
        )
        assert len(cache.links) == 2


class TestProofProvenance:
    """Tests for ProofProvenance model."""

    def test_unverified_default(self) -> None:
        now = datetime.now(UTC)
        prov = ProofProvenance(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=now,
            repo_url="https://github.com/user/proof",
        )
        assert prov.verification_status == VerificationStatus.UNVERIFIED
        assert prov.verification_strength == VerificationStrength.NONE
        assert prov.repo_commit is None

    def test_verified_proof(self) -> None:
        now = datetime.now(UTC)
        prov = ProofProvenance(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=now,
            repo_url="https://github.com/user/proof",
            repo_commit="abc123def456",
            verification_status=VerificationStatus.VERIFIED,
            verification_strength=VerificationStrength.NO_SORRIES,
            verified_at=now,
            verification_command="lake build",
            toolchain="leanprover/lean4:v4.8.0",
            verified_files=["Erdos/Problem347.lean"],
        )
        assert prov.verification_status == VerificationStatus.VERIFIED
        assert prov.verification_strength == VerificationStrength.NO_SORRIES
        assert len(prov.verified_files) == 1

    def test_roundtrip_json(self) -> None:
        now = datetime.now(UTC)
        prov = ProofProvenance(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=now,
            repo_url="https://github.com/user/proof",
            posted_by="mathprover",
            verification_status=VerificationStatus.INCONCLUSIVE,
            verification_strength=VerificationStrength.BUILD_ONLY,
            verification_error="Could not identify problem file",
        )
        json_str = prov.model_dump_json()
        restored = ProofProvenance.model_validate_json(json_str)
        assert restored.problem_id == prov.problem_id
        assert restored.verification_status == VerificationStatus.INCONCLUSIVE


class TestVerificationEnums:
    """Tests for verification enums."""

    def test_verification_status_values(self) -> None:
        assert VerificationStatus.UNVERIFIED.value == "unverified"
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.INCONCLUSIVE.value == "inconclusive"
        assert VerificationStatus.FAILED.value == "failed"
        assert VerificationStatus.SOURCE_UNAVAILABLE.value == "source_unavailable"

    def test_verification_strength_values(self) -> None:
        assert VerificationStrength.NONE.value == "none"
        assert VerificationStrength.BUILD_ONLY.value == "build_only"
        assert VerificationStrength.NO_SORRIES.value == "no_sorries"
