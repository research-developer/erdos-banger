"""Sync cache schemas and data extraction models (SPEC-035).

This module defines Pydantic models for:
1. Sync cache status (tracking when/what was synced)
2. Extracted data from each source (submodule, website, forum)
3. Proof provenance records

All models are designed for deterministic serialization and offline-first operation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import ConfigDict, Field

from erdos.core.models.base import ErdosBaseModel


# =============================================================================
# Enums
# =============================================================================


class VerificationStatus(str, Enum):
    """Status of proof verification."""

    UNVERIFIED = "unverified"  # Verification not attempted
    VERIFIED = "verified"  # Proof verified (no sorries)
    INCONCLUSIVE = "inconclusive"  # Build passed but couldn't confirm no sorries
    FAILED = "failed"  # Verification failed
    SOURCE_UNAVAILABLE = "source_unavailable"  # Repository not accessible


class VerificationStrength(str, Enum):
    """Strength of proof verification."""

    NONE = "none"  # No verification attempted
    BUILD_ONLY = "build_only"  # lake build succeeded
    NO_SORRIES = "no_sorries"  # Verified no sorry statements


# =============================================================================
# Helper functions for parsing upstream YAML
# =============================================================================


def _parse_problem_id(raw: dict[str, Any]) -> int:
    """Extract and validate problem_id from upstream YAML."""
    number = raw.get("number")
    if number is None:
        raise ValueError("Missing required field 'number'")
    try:
        return int(number)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid problem number: {number!r}") from e


def _parse_status(raw: dict[str, Any]) -> tuple[str, str | None]:
    """Parse status from upstream YAML. Returns (state, last_update)."""
    status_obj = raw.get("status", {})
    if isinstance(status_obj, dict):
        return status_obj.get("state", "unknown"), status_obj.get("last_update")
    return (str(status_obj) if status_obj else "unknown"), None


def _parse_prize(raw: dict[str, Any]) -> int:
    """Parse prize from upstream YAML (handles '$500' and 'no' formats)."""
    prize_raw = raw.get("prize", "no")
    if isinstance(prize_raw, str):
        if prize_raw.lower() == "no":
            return 0
        prize_str = prize_raw.replace("$", "").replace(",", "").strip()
        try:
            return int(prize_str) if prize_str else 0
        except ValueError:
            return 0
    if isinstance(prize_raw, int | float):
        return int(prize_raw)
    return 0


def _parse_oeis(raw: dict[str, Any]) -> list[str]:
    """Parse OEIS IDs from upstream YAML (filters 'N/A' entries)."""
    oeis_raw = raw.get("oeis", [])
    return [
        oid
        for oid in (oeis_raw if isinstance(oeis_raw, list) else [])
        if isinstance(oid, str) and oid.upper() != "N/A"
    ]


def _parse_formalized(raw: dict[str, Any]) -> tuple[bool, str | None]:
    """Parse formalized field. Returns (is_formalized, last_update)."""
    formalized_obj = raw.get("formalized", {})
    if isinstance(formalized_obj, dict):
        state = formalized_obj.get("state", "no")
        return state.lower() == "yes", formalized_obj.get("last_update")
    if isinstance(formalized_obj, bool):
        return formalized_obj, None
    return False, None


def _parse_tags(raw: dict[str, Any]) -> list[str]:
    """Parse tags from upstream YAML."""
    tags_raw = raw.get("tags", [])
    if not isinstance(tags_raw, list):
        return []

    tags: list[str] = []
    for t in tags_raw:
        if not isinstance(t, str):
            continue
        cleaned = t.strip()
        if cleaned:
            tags.append(cleaned)
    return tags


# =============================================================================
# Submodule Data Models
# =============================================================================


class SubmoduleProblemData(ErdosBaseModel):
    """
    Extracted data from a single problem in teorth/erdosproblems submodule.

    Maps to the upstream YAML schema:
    - number: "1" (string, 1-indexed)
    - prize: "$500" or "no"
    - status: { state: "open", last_update: "2025-08-31" }
    - oeis: ["A276661"]
    - formalized: { state: "yes", last_update: "2025-08-31" }
    - tags: ["number theory", "additive combinatorics"]
    """

    model_config = ConfigDict(frozen=True)

    problem_id: Annotated[int, Field(ge=1, description="Problem ID (1-indexed)")]
    status: Annotated[
        str, Field(description="Status state (open/proved/disproved/etc)")
    ]
    status_last_update: Annotated[
        str | None, Field(default=None, description="ISO date of last status update")
    ] = None
    prize: Annotated[
        int, Field(ge=0, default=0, description="Prize amount in USD (0 if 'no')")
    ] = 0
    tags: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list
    )
    oeis_ids: Annotated[
        list[str], Field(default_factory=list, description="OEIS sequence IDs")
    ] = Field(default_factory=list)
    formalized: Annotated[
        bool, Field(default=False, description="Has DeepMind formalization")
    ] = False
    formalized_last_update: Annotated[
        str | None,
        Field(default=None, description="ISO date of last formalized update"),
    ] = None

    @classmethod
    def from_upstream_yaml(cls, raw: dict[str, Any]) -> SubmoduleProblemData:
        """Parse from upstream teorth/erdosproblems YAML format.

        Args:
            raw: Raw dict from problems.yaml

        Returns:
            Parsed SubmoduleProblemData

        Raises:
            ValueError: If required fields are missing or malformed
        """
        problem_id = _parse_problem_id(raw)
        status, status_last_update = _parse_status(raw)
        prize = _parse_prize(raw)
        oeis_ids = _parse_oeis(raw)
        formalized, formalized_last_update = _parse_formalized(raw)
        tags = _parse_tags(raw)

        return cls(
            problem_id=problem_id,
            status=str(status),
            status_last_update=status_last_update,
            prize=prize,
            tags=tags,
            oeis_ids=oeis_ids,
            formalized=formalized,
            formalized_last_update=formalized_last_update,
        )


class SubmoduleSyncStatus(ErdosBaseModel):
    """
    Sync cache status for the submodule.

    Stored at: data/sync_cache/submodule_status.json
    """

    model_config = ConfigDict(frozen=True)

    commit_hash: Annotated[
        str | None, Field(default=None, description="Current submodule commit SHA")
    ] = None
    previous_commit_hash: Annotated[
        str | None, Field(default=None, description="Previous commit before sync")
    ] = None
    synced_at: Annotated[
        datetime | None, Field(default=None, description="When sync was performed")
    ] = None
    problems_count: Annotated[
        int, Field(ge=0, default=0, description="Number of problems in submodule")
    ] = 0
    stale: Annotated[
        bool | None,
        Field(default=None, description="Whether submodule is behind remote"),
    ] = None


# =============================================================================
# Website Data Models
# =============================================================================


class WebsiteReferenceData(ErdosBaseModel):
    """
    A reference extracted from the erdosproblems.com website.

    Maps to the ProblemRecord.references schema for compatibility.
    """

    model_config = ConfigDict(frozen=True)

    key: Annotated[str, Field(min_length=1, description="Reference key (e.g., 'Er65')")]
    citation: Annotated[str | None, Field(default=None)] = None
    doi: Annotated[str | None, Field(default=None)] = None
    arxiv_id: Annotated[str | None, Field(default=None)] = None
    url: Annotated[str | None, Field(default=None)] = None


class WebsiteProblemData(ErdosBaseModel):
    """
    Extracted data from erdosproblems.com main problem page.

    URL pattern: https://www.erdosproblems.com/{problem_id}
    """

    model_config = ConfigDict(frozen=True)

    problem_id: Annotated[int, Field(ge=1, description="Problem ID")]
    title: Annotated[str | None, Field(default=None, description="Problem title")] = (
        None
    )
    statement: Annotated[
        str | None,
        Field(default=None, description="Problem statement (may include LaTeX)"),
    ] = None
    tags: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list
    )
    references: Annotated[list[WebsiteReferenceData], Field(default_factory=list)] = (
        Field(default_factory=list)
    )
    status_badge_text: Annotated[
        str | None,
        Field(default=None, description="Status badge text for cross-check only"),
    ] = None
    latex_source_url: Annotated[
        str | None, Field(default=None, description="URL to raw LaTeX source")
    ] = None
    fetched_at: Annotated[
        datetime | None, Field(default=None, description="When page was fetched")
    ] = None


class WebsiteSyncStatus(ErdosBaseModel):
    """
    Sync cache status for a single website problem page.

    Stored at: data/sync_cache/website/{problem_id}.json
    """

    model_config = ConfigDict(frozen=True)

    problem_id: Annotated[int, Field(ge=1)]
    fetched_at: Annotated[datetime | None, Field(default=None)] = None
    http_status: Annotated[int | None, Field(default=None)] = None
    parse_success: Annotated[bool, Field(default=False)] = False
    parse_error: Annotated[str | None, Field(default=None)] = None
    warnings: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list
    )
    cached_html_path: Annotated[str | None, Field(default=None)] = None


# =============================================================================
# Forum / Proof Models
# =============================================================================


class ProofLink(ErdosBaseModel):
    """
    A proof repository link extracted from the forum.

    URL pattern: https://www.erdosproblems.com/forum/thread/{problem_id}
    """

    model_config = ConfigDict(frozen=True)

    url: Annotated[str, Field(description="GitHub/GitLab repository URL")]
    author: Annotated[
        str | None, Field(default=None, description="Forum username (best-effort)")
    ] = None
    posted_at: Annotated[
        datetime | None,
        Field(default=None, description="Post timestamp (best-effort)"),
    ] = None
    lean_version_hint: Annotated[
        str | None, Field(default=None, description="Lean version if mentioned")
    ] = None


class ProofProvenance(ErdosBaseModel):
    """
    Best-effort provenance record for an external proof repository.

    Stored at: data/sync_cache/proofs/{problem_id}/provenance.json
    """

    model_config = ConfigDict(frozen=True)

    problem_id: Annotated[int, Field(ge=1)]
    forum_thread_url: Annotated[str, Field(description="Forum thread URL")]
    extracted_at: Annotated[datetime, Field(description="When links were extracted")]

    repo_url: Annotated[str, Field(description="Selected proof repository URL")]
    repo_commit: Annotated[
        str | None, Field(default=None, description="Commit SHA at verification time")
    ] = None

    posted_by: Annotated[
        str | None, Field(default=None, description="Forum username")
    ] = None
    posted_at: Annotated[
        datetime | None, Field(default=None, description="Forum post timestamp")
    ] = None

    verification_status: Annotated[
        VerificationStatus,
        Field(default=VerificationStatus.UNVERIFIED),
    ] = VerificationStatus.UNVERIFIED
    verification_strength: Annotated[
        VerificationStrength,
        Field(default=VerificationStrength.NONE),
    ] = VerificationStrength.NONE
    verification_error: Annotated[
        str | None,
        Field(default=None, description="Short, user-facing error reason"),
    ] = None
    verified_at: Annotated[datetime | None, Field(default=None)] = None
    verification_command: Annotated[
        str | None, Field(default=None, description="e.g., 'lake build'")
    ] = None
    toolchain: Annotated[
        str | None, Field(default=None, description="lean-toolchain contents")
    ] = None
    verified_files: Annotated[
        list[str], Field(default_factory=list, description="Paths that were checked")
    ] = Field(default_factory=list)
    log_path: Annotated[
        str | None, Field(default=None, description="Path to verify.log")
    ] = None


class ProofLinksCache(ErdosBaseModel):
    """
    Cache of extracted proof links from a forum thread.

    Stored at: data/sync_cache/proofs/{problem_id}/links.json
    """

    model_config = ConfigDict(frozen=True)

    problem_id: Annotated[int, Field(ge=1)]
    forum_thread_url: Annotated[str, Field(description="Forum thread URL")]
    extracted_at: Annotated[datetime, Field(description="When extraction occurred")]
    links: Annotated[list[ProofLink], Field(default_factory=list)] = Field(
        default_factory=list
    )
