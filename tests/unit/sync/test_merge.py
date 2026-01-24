"""Tests for sync merge logic (SPEC-035)."""

from __future__ import annotations

import pytest

from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry
from erdos.core.sync.merge import merge_all_problems, merge_problem_data
from erdos.core.sync.models import (
    SubmoduleProblemData,
    WebsiteProblemData,
    WebsiteReferenceData,
)


class TestMergeProblemData:
    """Tests for merge_problem_data function."""

    def test_merge_both_sources(self) -> None:
        """Merge submodule and website data for a complete record."""
        submodule = SubmoduleProblemData(
            problem_id=6,
            status="proved",
            prize=100,
            tags=["number theory", "primes"],
            oeis_ids=["A335277"],
            formalized=True,
        )
        website = WebsiteProblemData(
            problem_id=6,
            title="Small primes in arithmetic progressions",
            statement="Let $p_1 < p_2 < \\ldots$ be the sequence of primes...",
            references=[
                WebsiteReferenceData(
                    key="GreenTao2008",
                    doi="10.4007/annals.2008.167.481",
                )
            ],
        )

        result = merge_problem_data(6, submodule=submodule, website=website)

        assert result is not None
        assert result.id == 6
        # From website
        assert result.title == "Small primes in arithmetic progressions"
        assert "primes" in result.statement
        assert len(result.references) == 1
        assert result.references[0].key == "GreenTao2008"
        # From submodule
        assert result.status == ProblemStatus.PROVED
        assert result.prize == 100
        assert result.tags == ["number theory", "primes"]
        assert result.oeis_ids == ["A335277"]
        assert result.formalized is True

    def test_submodule_only_returns_none(self) -> None:
        """Submodule alone is insufficient (no title/statement)."""
        submodule = SubmoduleProblemData(
            problem_id=6,
            status="proved",
            prize=100,
        )

        result = merge_problem_data(6, submodule=submodule)

        # Cannot create ProblemRecord without title and statement
        assert result is None

    def test_website_only_uses_defaults(self) -> None:
        """Website alone provides title/statement, uses defaults for rest."""
        website = WebsiteProblemData(
            problem_id=6,
            title="Test Problem",
            statement="Prove that X.",
        )

        result = merge_problem_data(6, website=website)

        assert result is not None
        assert result.id == 6
        assert result.title == "Test Problem"
        assert result.statement == "Prove that X."
        # Defaults when no submodule
        assert result.status == ProblemStatus.OPEN
        assert result.prize == 0
        assert result.tags == []
        assert result.formalized is False

    def test_existing_preserves_notes(self) -> None:
        """Existing record's notes are preserved by default."""
        existing = ProblemRecord(
            id=6,
            title="Old Title",
            statement="Old statement",
            status=ProblemStatus.OPEN,
            notes="Important research note",
        )
        website = WebsiteProblemData(
            problem_id=6,
            title="New Title",
            statement="New statement",
        )

        result = merge_problem_data(6, website=website, existing=existing)

        assert result is not None
        assert result.title == "New Title"
        assert result.statement == "New statement"
        assert result.notes == "Important research note"

    def test_existing_notes_overwritten_when_flag_set(self) -> None:
        """Notes are cleared when overwrite_notes is True."""
        existing = ProblemRecord(
            id=6,
            title="Old Title",
            statement="Old statement",
            status=ProblemStatus.OPEN,
            notes="Should be removed",
        )
        website = WebsiteProblemData(
            problem_id=6,
            title="New Title",
            statement="New statement",
        )

        result = merge_problem_data(
            6, website=website, existing=existing, overwrite_notes=True
        )

        assert result is not None
        assert result.notes is None

    def test_existing_fallback_for_missing_sources(self) -> None:
        """Existing record provides fallback for all fields."""
        existing = ProblemRecord(
            id=6,
            title="Existing Title",
            statement="Existing statement",
            status=ProblemStatus.PROVED,
            prize=500,
            tags=["existing tag"],
            oeis_ids=["A123456"],
            formalized=True,
        )

        # No submodule or website data
        result = merge_problem_data(6, existing=existing)

        assert result is not None
        assert result.title == "Existing Title"
        assert result.status == ProblemStatus.PROVED
        assert result.prize == 500
        assert result.formalized is True

    def test_submodule_overrides_existing_status(self) -> None:
        """Submodule data overrides existing status."""
        existing = ProblemRecord(
            id=6,
            title="Title",
            statement="Statement",
            status=ProblemStatus.OPEN,
        )
        submodule = SubmoduleProblemData(
            problem_id=6,
            status="proved",
            prize=100,
        )

        result = merge_problem_data(6, submodule=submodule, existing=existing)

        assert result is not None
        assert result.status == ProblemStatus.PROVED
        assert result.prize == 100

    def test_website_overrides_existing_title_statement(self) -> None:
        """Website data overrides existing title and statement."""
        existing = ProblemRecord(
            id=6,
            title="Old Title",
            statement="Old statement",
            status=ProblemStatus.OPEN,
        )
        website = WebsiteProblemData(
            problem_id=6,
            title="New Title from Website",
            statement="New statement from website",
        )

        result = merge_problem_data(6, website=website, existing=existing)

        assert result is not None
        assert result.title == "New Title from Website"
        assert result.statement == "New statement from website"

    def test_empty_website_title_uses_existing(self) -> None:
        """Empty website title falls back to existing."""
        existing = ProblemRecord(
            id=6,
            title="Existing Title",
            statement="Existing statement",
            status=ProblemStatus.OPEN,
        )
        website = WebsiteProblemData(
            problem_id=6,
            title=None,  # Empty
            statement="New statement",
        )

        result = merge_problem_data(6, website=website, existing=existing)

        assert result is not None
        assert result.title == "Existing Title"
        assert result.statement == "New statement"

    def test_empty_website_statement_uses_existing(self) -> None:
        """Empty website statement falls back to existing."""
        existing = ProblemRecord(
            id=6,
            title="Existing Title",
            statement="Existing statement",
            status=ProblemStatus.OPEN,
        )
        website = WebsiteProblemData(
            problem_id=6,
            title="New Title",
            statement=None,  # Empty
        )

        result = merge_problem_data(6, website=website, existing=existing)

        assert result is not None
        assert result.title == "New Title"
        assert result.statement == "Existing statement"

    def test_submodule_problem_id_mismatch_raises(self) -> None:
        """Submodule problem_id mismatch raises ValueError."""
        submodule = SubmoduleProblemData(problem_id=7, status="open")

        with pytest.raises(ValueError, match="Submodule problem_id mismatch"):
            merge_problem_data(6, submodule=submodule)

    def test_website_problem_id_mismatch_raises(self) -> None:
        """Website problem_id mismatch raises ValueError."""
        website = WebsiteProblemData(problem_id=7, title="Test", statement="Test")

        with pytest.raises(ValueError, match="Website problem_id mismatch"):
            merge_problem_data(6, website=website)

    def test_no_data_returns_none(self) -> None:
        """No data at all returns None."""
        result = merge_problem_data(6)
        assert result is None

    def test_status_normalization(self) -> None:
        """Various status formats are normalized."""
        website = WebsiteProblemData(problem_id=6, title="Test", statement="Test")

        # Test "proved (Lean)" normalization
        submodule = SubmoduleProblemData(problem_id=6, status="proved (Lean)")
        result = merge_problem_data(6, submodule=submodule, website=website)
        assert result is not None
        assert result.status == ProblemStatus.PROVED

        # Test "verifiable" maps to unknown
        submodule2 = SubmoduleProblemData(problem_id=6, status="verifiable")
        result2 = merge_problem_data(6, submodule=submodule2, website=website)
        assert result2 is not None
        assert result2.status == ProblemStatus.UNKNOWN

    def test_references_conversion(self) -> None:
        """Website references are converted to ReferenceEntry format."""
        website = WebsiteProblemData(
            problem_id=6,
            title="Test",
            statement="Test",
            references=[
                WebsiteReferenceData(
                    key="Er65",
                    citation="P. Erdős (1965)",
                    doi="10.1234/test",
                    arxiv_id="math/0404188",
                    url="https://example.com",
                ),
            ],
        )

        result = merge_problem_data(6, website=website)

        assert result is not None
        assert len(result.references) == 1
        ref = result.references[0]
        assert isinstance(ref, ReferenceEntry)
        assert ref.key == "Er65"
        assert ref.citation == "P. Erdős (1965)"
        assert ref.doi == "10.1234/test"
        assert ref.arxiv_id == "math/0404188"
        assert ref.url == "https://example.com"

    def test_tags_from_submodule_replace_existing(self) -> None:
        """Submodule tags replace existing tags entirely."""
        existing = ProblemRecord(
            id=6,
            title="Test",
            statement="Test",
            status=ProblemStatus.OPEN,
            tags=["old tag 1", "old tag 2"],
        )
        submodule = SubmoduleProblemData(
            problem_id=6,
            status="open",
            tags=["new tag"],
        )

        result = merge_problem_data(6, submodule=submodule, existing=existing)

        assert result is not None
        assert result.tags == ["new tag"]

    def test_empty_submodule_tags_uses_existing(self) -> None:
        """Empty submodule tags fall back to existing tags."""
        existing = ProblemRecord(
            id=6,
            title="Test",
            statement="Test",
            status=ProblemStatus.OPEN,
            tags=["existing tag"],
        )
        submodule = SubmoduleProblemData(
            problem_id=6,
            status="open",
            tags=[],  # Empty
        )

        result = merge_problem_data(6, submodule=submodule, existing=existing)

        assert result is not None
        assert result.tags == ["existing tag"]


class TestMergeAllProblems:
    """Tests for merge_all_problems function."""

    def test_merge_multiple_problems(self) -> None:
        """Merge data for multiple problems."""
        submodule_data = {
            1: SubmoduleProblemData(problem_id=1, status="open", prize=500),
            2: SubmoduleProblemData(problem_id=2, status="proved", prize=0),
        }
        website_data = {
            1: WebsiteProblemData(problem_id=1, title="Problem 1", statement="Stmt 1"),
            2: WebsiteProblemData(problem_id=2, title="Problem 2", statement="Stmt 2"),
        }

        results = merge_all_problems(submodule_data, website_data)

        assert len(results) == 2
        assert results[0].id == 1
        assert results[0].status == ProblemStatus.OPEN
        assert results[1].id == 2
        assert results[1].status == ProblemStatus.PROVED

    def test_sorted_by_id(self) -> None:
        """Results are sorted by problem ID ascending."""
        submodule_data = {
            100: SubmoduleProblemData(problem_id=100, status="open"),
            5: SubmoduleProblemData(problem_id=5, status="proved"),
            50: SubmoduleProblemData(problem_id=50, status="open"),
        }
        website_data = {
            100: WebsiteProblemData(problem_id=100, title="P100", statement="S100"),
            5: WebsiteProblemData(problem_id=5, title="P5", statement="S5"),
            50: WebsiteProblemData(problem_id=50, title="P50", statement="S50"),
        }

        results = merge_all_problems(submodule_data, website_data)

        assert [r.id for r in results] == [5, 50, 100]

    def test_union_of_ids(self) -> None:
        """All IDs from all sources are processed."""
        submodule_data = {
            1: SubmoduleProblemData(problem_id=1, status="open"),
        }
        website_data = {
            2: WebsiteProblemData(problem_id=2, title="P2", statement="S2"),
        }
        existing = {
            3: ProblemRecord(
                id=3,
                title="P3",
                statement="S3",
                status=ProblemStatus.OPEN,
            ),
        }

        results = merge_all_problems(submodule_data, website_data, existing)

        # ID 1: submodule only -> None (no title/statement)
        # ID 2: website only -> valid
        # ID 3: existing only -> valid
        assert len(results) == 2
        assert {r.id for r in results} == {2, 3}

    def test_incomplete_data_filtered_out(self) -> None:
        """Problems without title/statement are filtered out."""
        submodule_data = {
            1: SubmoduleProblemData(problem_id=1, status="open"),
            2: SubmoduleProblemData(problem_id=2, status="proved"),
        }
        website_data = {
            # Only problem 1 has website data
            1: WebsiteProblemData(problem_id=1, title="P1", statement="S1"),
        }

        results = merge_all_problems(submodule_data, website_data)

        # Problem 2 has no title/statement, so it's filtered out
        assert len(results) == 1
        assert results[0].id == 1

    def test_existing_problems_preserved(self) -> None:
        """Existing problems are included even without new data."""
        existing = {
            1: ProblemRecord(
                id=1,
                title="Existing Problem",
                statement="Existing statement",
                status=ProblemStatus.PROVED,
                notes="Keep this note",
            ),
        }

        results = merge_all_problems({}, {}, existing)

        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].notes == "Keep this note"

    def test_overwrite_notes_flag(self) -> None:
        """overwrite_notes flag is passed through to merge."""
        existing = {
            1: ProblemRecord(
                id=1,
                title="P1",
                statement="S1",
                status=ProblemStatus.OPEN,
                notes="Should be cleared",
            ),
        }

        results = merge_all_problems({}, {}, existing, overwrite_notes=True)

        assert len(results) == 1
        assert results[0].notes is None

    def test_empty_inputs(self) -> None:
        """Empty inputs return empty list."""
        results = merge_all_problems({}, {})
        assert results == []

    def test_deterministic_order(self) -> None:
        """Same inputs always produce same order."""
        submodule = {
            i: SubmoduleProblemData(problem_id=i, status="open")
            for i in [3, 1, 4, 1, 5, 9, 2, 6]
        }
        website = {
            i: WebsiteProblemData(problem_id=i, title=f"P{i}", statement=f"S{i}")
            for i in submodule
        }

        results1 = merge_all_problems(submodule, website)
        results2 = merge_all_problems(submodule, website)

        assert [r.id for r in results1] == [r.id for r in results2]
        assert [r.id for r in results1] == sorted(set(submodule.keys()))
