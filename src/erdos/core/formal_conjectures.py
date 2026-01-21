"""Formal conjectures integration for importing upstream Lean formalizations.

This module handles:
1. Parsing upstream formalization metadata from teorth/erdosproblems
2. Fetching Lean files from google-deepmind/formal-conjectures
3. Comparing local vs upstream formalizations
4. Tracking provenance of imported files
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - Used at runtime
from typing import Any

import requests
import yaml

from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


# Source repository constants
FORMAL_CONJECTURES_REPO = "google-deepmind/formal-conjectures"
FORMAL_CONJECTURES_BASE_URL = (
    "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/"
)


class FormalConjecturesError(Exception):
    """Error raised by formal_conjectures operations."""

    def __init__(self, message: str, *, error_type: str = "Error") -> None:
        super().__init__(message)
        self.error_type = error_type


# ============================================================================
# Upstream Metadata
# ============================================================================


@dataclass(frozen=True)
class UpstreamFormalizationInfo:
    """Information about upstream formalization status."""

    problem_id: int
    formalized: bool
    state: str | None = None
    last_update: str | None = None
    source: str = FORMAL_CONJECTURES_REPO
    url: str | None = None


def parse_upstream_formalization_status(
    metadata: dict[str, Any],
) -> UpstreamFormalizationInfo:
    """Parse formalization status from upstream metadata entry.

    Args:
        metadata: Single problem entry from upstream problems.yaml

    Returns:
        UpstreamFormalizationInfo with formalized status
    """
    problem_id = int(metadata.get("number", 0))
    formalized_data = metadata.get("formalized")

    if formalized_data is None or not isinstance(formalized_data, dict):
        return UpstreamFormalizationInfo(
            problem_id=problem_id,
            formalized=False,
            state=None,
        )

    state = formalized_data.get("state")
    last_update = formalized_data.get("last_update")
    formalized = state == "yes"

    return UpstreamFormalizationInfo(
        problem_id=problem_id,
        formalized=formalized,
        state=state,
        last_update=last_update,
        url=build_upstream_url(problem_id) if formalized else None,
    )


def load_upstream_metadata(yaml_path: Path) -> dict[int, UpstreamFormalizationInfo]:
    """Load upstream formalization metadata from problems.yaml.

    Args:
        yaml_path: Path to upstream problems.yaml (e.g., data/erdosproblems/data/problems.yaml)

    Returns:
        Dict mapping problem_id to UpstreamFormalizationInfo

    Raises:
        FormalConjecturesError: If file not found or invalid
    """
    if not yaml_path.exists():
        raise FormalConjecturesError(
            f"Upstream metadata file not found: {yaml_path}",
            error_type="ConfigError",
        )

    try:
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise FormalConjecturesError(
            f"Failed to parse upstream metadata: {e}",
            error_type="ParseError",
        ) from e

    if not isinstance(data, list):
        raise FormalConjecturesError(
            f"Expected list of problems, got {type(data).__name__}",
            error_type="ParseError",
        )

    result: dict[int, UpstreamFormalizationInfo] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        info = parse_upstream_formalization_status(item)
        if info.problem_id > 0:
            result[info.problem_id] = info

    return result


# ============================================================================
# URL Building and Paths
# ============================================================================


def build_upstream_url(problem_id: int, source: str = FORMAL_CONJECTURES_REPO) -> str:
    """Build URL to fetch upstream Lean file.

    Args:
        problem_id: Problem number
        source: Source repository (currently only formal-conjectures supported)

    Returns:
        URL to raw Lean file content
    """
    if source == FORMAL_CONJECTURES_REPO:
        return f"{FORMAL_CONJECTURES_BASE_URL}FormalConjectures/ErdosProblems/{problem_id}.lean"
    raise FormalConjecturesError(f"Unknown source repository: {source}")


def get_cache_path(project_path: Path, problem_id: int) -> Path:
    """Get cache path for upstream Lean file.

    Args:
        project_path: Path to Lean project (e.g., formal/lean)
        problem_id: Problem number

    Returns:
        Path to cache file
    """
    return (
        project_path
        / ".upstream_cache"
        / "formal-conjectures"
        / "ErdosProblems"
        / f"{problem_id}.lean"
    )


def get_local_file_path(project_path: Path, problem_id: int) -> Path:
    """Get local Lean file path for a problem.

    Args:
        project_path: Path to Lean project (e.g., formal/lean)
        problem_id: Problem number

    Returns:
        Path to local Lean file (e.g., formal/lean/Erdos/Problem006.lean)
    """
    return project_path / "Erdos" / f"Problem{problem_id:03d}.lean"


# ============================================================================
# Sorry Detection
# ============================================================================


def has_sorry(content: str) -> bool:
    """Check if Lean content contains sorry or admit.

    Args:
        content: Lean file content

    Returns:
        True if sorry/admit found outside comments
    """
    # Remove block comments
    content_no_block = re.sub(r"/\-.*?\-/", "", content, flags=re.DOTALL)

    # Process line by line, removing single-line comments
    for line in content_no_block.split("\n"):
        # Remove everything after --
        code_part = line.split("--")[0]
        # Check for sorry/admit at word boundaries
        if re.search(r"\bsorry\b", code_part) or re.search(r"\badmit\b", code_part):
            return True

    return False


# ============================================================================
# File Hash
# ============================================================================


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 hash

    Raises:
        FormalConjecturesError: If file not found
    """
    if not file_path.exists():
        raise FormalConjecturesError(
            f"File not found: {file_path}",
            error_type="NotFound",
        )

    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


# ============================================================================
# Provenance Tracking
# ============================================================================


@dataclass
class ProvenanceEntry:
    """Record of an imported formalization."""

    problem_id: int
    source: str
    url: str
    imported_at: datetime
    sha256: str
    remote_etag: str | None = None


@dataclass
class ProvenanceFile:
    """Provenance tracking file model."""

    schema_version: int = 1
    imports: list[ProvenanceEntry] = field(default_factory=list)

    def get_by_problem_id(self, problem_id: int) -> ProvenanceEntry | None:
        """Find provenance entry by problem ID."""
        for entry in self.imports:
            if entry.problem_id == problem_id:
                return entry
        return None

    def upsert(self, entry: ProvenanceEntry) -> None:
        """Insert or update provenance entry."""
        for i, existing in enumerate(self.imports):
            if existing.problem_id == entry.problem_id:
                self.imports[i] = entry
                return
        self.imports.append(entry)


def save_provenance(prov_path: Path, prov: ProvenanceFile) -> None:
    """Save provenance file to disk.

    Args:
        prov_path: Path to provenance file
        prov: ProvenanceFile to save
    """
    prov_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "schema_version": prov.schema_version,
        "imports": [
            {
                "problem_id": e.problem_id,
                "source": e.source,
                "url": e.url,
                "imported_at": e.imported_at.isoformat(),
                "sha256": e.sha256,
                **({"remote_etag": e.remote_etag} if e.remote_etag else {}),
            }
            for e in prov.imports
        ],
    }

    with prov_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_provenance(prov_path: Path) -> ProvenanceFile:
    """Load provenance file from disk.

    Args:
        prov_path: Path to provenance file

    Returns:
        ProvenanceFile (empty if file doesn't exist)
    """
    if not prov_path.exists():
        return ProvenanceFile()

    with prov_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return ProvenanceFile()

    imports = []
    for item in data.get("imports", []):
        imports.append(
            ProvenanceEntry(
                problem_id=item["problem_id"],
                source=item["source"],
                url=item["url"],
                imported_at=datetime.fromisoformat(item["imported_at"]),
                sha256=item["sha256"],
                remote_etag=item.get("remote_etag"),
            )
        )

    return ProvenanceFile(
        schema_version=data.get("schema_version", 1),
        imports=imports,
    )


# ============================================================================
# Fetch Upstream Files
# ============================================================================


@dataclass
class FetchResult:
    """Result of fetching upstream Lean file."""

    content: str
    sha256: str
    url: str
    etag: str | None = None
    from_cache: bool = False


def fetch_upstream_lean_file(
    project_path: Path,
    problem_id: int,
    *,
    source_url: str | None = None,
    no_network: bool = False,
) -> FetchResult:
    """Fetch upstream Lean file, using cache if available.

    Args:
        project_path: Path to Lean project
        problem_id: Problem number
        source_url: Override source URL (default: derived from formal-conjectures)
        no_network: If True, only use cached file

    Returns:
        FetchResult with content and metadata

    Raises:
        FormalConjecturesError: On network error or if no_network and not cached
    """
    cache_path = get_cache_path(project_path, problem_id)
    url = source_url or build_upstream_url(problem_id)

    # Try cache first
    if cache_path.exists():
        logger.debug("Using cached file: %s", cache_path)
        content = cache_path.read_text(encoding="utf-8")
        sha256 = hashlib.sha256(cache_path.read_bytes()).hexdigest()
        return FetchResult(
            content=content,
            sha256=sha256,
            url=url,
            from_cache=True,
        )

    if no_network:
        raise FormalConjecturesError(
            f"Upstream file for problem {problem_id} is not cached and --no-network is set",
            error_type="NetworkError",
        )

    # Fetch from network
    logger.debug("Fetching upstream file: %s", url)
    try:
        response = fetch_with_retry(url, timeout=30)
    except requests.RequestException as e:
        raise FormalConjecturesError(
            f"Failed to fetch upstream file: {e}",
            error_type="NetworkError",
        ) from e

    if response.status_code != 200:
        raise FormalConjecturesError(
            f"HTTP {response.status_code} fetching {url}",
            error_type="NetworkError",
        )

    content_bytes = response.content
    content = content_bytes.decode("utf-8")
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    etag = response.headers.get("ETag")

    # Write to cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(content_bytes)
    logger.debug("Cached upstream file: %s", cache_path)

    return FetchResult(
        content=content,
        sha256=sha256,
        url=url,
        etag=etag,
        from_cache=False,
    )


# ============================================================================
# Local Formalization Info
# ============================================================================


@dataclass
class LocalFormalizationInfo:
    """Information about local formalization file."""

    path: Path
    exists: bool
    has_sorry: bool | None = None
    sha256: str | None = None
    last_modified: datetime | None = None

    @classmethod
    def from_file(cls, file_path: Path) -> LocalFormalizationInfo:
        """Create info from file path.

        Args:
            file_path: Path to local Lean file

        Returns:
            LocalFormalizationInfo with file details
        """
        if not file_path.exists():
            return cls(path=file_path, exists=False)

        content = file_path.read_text(encoding="utf-8")
        content_bytes = file_path.read_bytes()
        stat = file_path.stat()

        return cls(
            path=file_path,
            exists=True,
            has_sorry=has_sorry(content),
            sha256=hashlib.sha256(content_bytes).hexdigest(),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )
