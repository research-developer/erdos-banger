"""Unit tests for loop service helpers."""

from __future__ import annotations

from pathlib import Path

from erdos.core.loop.service import MIN_RAG_CHUNK_BYTES, _build_rag_chunks


def _write_synthesis(repo_root: Path, problem_id: int, content: str) -> None:
    synthesis_path = (
        repo_root / "research" / "problems" / f"{problem_id:04d}" / "SYNTHESIS.md"
    )
    synthesis_path.parent.mkdir(parents=True, exist_ok=True)
    synthesis_path.write_text(content, encoding="utf-8")


def test_build_rag_chunks_clamps_large_limit_to_avoid_tiny_chunks(
    tmp_path: Path,
) -> None:
    content = "a" * 1024
    _write_synthesis(tmp_path, 1, content)

    chunks = _build_rag_chunks(1, repo_root=tmp_path, limit=10_000)

    encoded_len = len(content.encode("utf-8"))
    max_reasonable = max(1, encoded_len // MIN_RAG_CHUNK_BYTES or 1)
    assert 1 <= len(chunks) <= max_reasonable


def test_build_rag_chunks_respects_small_limit(tmp_path: Path) -> None:
    _write_synthesis(tmp_path, 1, "a" * 1024)

    chunks = _build_rag_chunks(1, repo_root=tmp_path, limit=2)

    assert len(chunks) <= 2
