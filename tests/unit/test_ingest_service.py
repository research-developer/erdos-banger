"""Unit tests for ingest core logic (SPEC-010-D).

Tests the ingest_problem_references function that orchestrates:
- Loading problem references
- Fetching metadata from arXiv/Crossref
- Managing manifest creation/updates
- Handling idempotence and error cases
"""

import io
import tarfile
from pathlib import Path

import pytest
import responses

from erdos.core.ingest import ingest_problem_references
from erdos.core.models import CLIOutput


@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    """Create a temporary repository root with required directories."""
    lit_dir = tmp_path / "literature"
    (lit_dir / "manifests").mkdir(parents=True)
    (lit_dir / "cache" / "arxiv").mkdir(parents=True)
    (lit_dir / "extracts" / "arxiv").mkdir(parents=True)
    return tmp_path


def test_ingest_no_references(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with a problem that has no references."""
    # Create a minimal problems.yaml with no references
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 999
  title: "Test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references: []
""")

    # Set environment variable to use our test data
    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    result = ingest_problem_references(
        problem_id=999,
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should succeed with zero entries
    assert isinstance(result, CLIOutput)
    if not result.success:
        print(f"Error: {result.error}")
    assert result.success is True
    assert result.data["problem_id"] == 999
    assert result.data["references_total"] == 0
    assert result.data["entries_written"] == 0
    assert result.data["skipped"] == 0

    # Manifest should exist
    manifest_path = temp_repo_root / "literature" / "manifests" / "0999.yaml"
    assert manifest_path.exists()


@responses.activate
def test_ingest_arxiv_reference(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with an arXiv reference."""
    # Setup test data
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 998
  title: "Test problem with arXiv"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock arXiv API response
    arxiv_response_path = Path("tests/fixtures/arxiv_responses/arxiv_2203.00001.xml")
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=arxiv_response_path.read_text(),
        status=200,
    )

    # Mock arXiv tarball download (create minimal tar.gz)
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add a minimal .tex file
        tex_content = b"\\documentclass{article}\n\\begin{document}\nTest content\n\\end{document}"
        tex_info = tarfile.TarInfo(name="main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    responses.add(
        responses.GET,
        "https://arxiv.org/e-print/2203.00001",
        body=tar_buffer.getvalue(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=998,
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should succeed with one entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1
    assert result.data["skipped"] == 0

    # Check manifest
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    # arXiv response includes version suffix
    assert entry["reference"]["arxiv_id"] == "2203.00001v1"
    assert entry["cached"] is True
    assert entry["extracted"] is True


@responses.activate
def test_ingest_doi_reference(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with a DOI reference."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 997
  title: "Test problem with DOI"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Erdos1975"
      doi: "10.1007/BF01940595"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock Crossref API response
    crossref_response_path = Path(
        "tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json"
    )
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1007/BF01940595",
        body=crossref_response_path.read_text(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=997,
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should succeed with one entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1

    # Check manifest - DOI reference should not have cache/extract
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    assert entry["reference"]["doi"] == "10.1007/BF01940595"
    assert entry["cached"] is False
    assert entry["extracted"] is False


@responses.activate
def test_ingest_merged_doi_arxiv(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingest with both DOI and arXiv (should create one merged entry)."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 996
  title: "Test problem with DOI+arXiv"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      doi: "10.1007/BF01940595"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock Crossref API
    crossref_response_path = Path(
        "tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json"
    )
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1007/BF01940595",
        body=crossref_response_path.read_text(),
        status=200,
    )

    # Mock arXiv tarball download
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_content = (
            b"\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}"
        )
        tex_info = tarfile.TarInfo(name="main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    responses.add(
        responses.GET,
        "https://arxiv.org/e-print/2203.00001",
        body=tar_buffer.getvalue(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=996,
        repo_root=temp_repo_root,
        force=False,
        no_download=False,
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should create ONE merged entry
    assert result.success is True
    assert result.data["references_total"] == 1
    assert result.data["entries_written"] == 1

    # Check merged entry has both DOI and arXiv ID
    manifest_data = result.data["manifest"]
    assert len(manifest_data["entries"]) == 1
    entry = manifest_data["entries"][0]
    assert entry["reference"]["doi"] == "10.1007/BF01940595"
    assert entry["reference"]["arxiv_id"] == "2203.00001"
    assert entry["cached"] is True  # arXiv tarball downloaded
    assert entry["extracted"] is True


@responses.activate
def test_ingest_no_download_flag(
    temp_repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test --no-download flag skips arXiv tarballs."""
    problems_yaml = temp_repo_root / "data" / "problems_enriched.yaml"
    problems_yaml.parent.mkdir(parents=True)
    problems_yaml.write_text("""
- id: 995
  title: "Test problem"
  statement: "Test problem statement"
  category: "Graph Theory"
  references:
    - key: "Test2023"
      arxiv_id: "2203.00001"
""")

    monkeypatch.setenv("ERDOS_DATA_PATH", str(temp_repo_root / "data"))

    # Mock only arXiv metadata API (no tarball download expected)
    arxiv_response_path = Path("tests/fixtures/arxiv_responses/arxiv_2203.00001.xml")
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=arxiv_response_path.read_text(),
        status=200,
    )

    result = ingest_problem_references(
        problem_id=995,
        repo_root=temp_repo_root,
        force=False,
        no_download=True,  # Should skip tarball download
        no_network=False,
        timeout=30.0,
        delay=0.0,
        mailto="test@example.com",
    )

    # Should succeed but no cache/extract
    assert result.success is True
    manifest_data = result.data["manifest"]
    entry = manifest_data["entries"][0]
    assert entry["cached"] is False
    assert entry["extracted"] is False
