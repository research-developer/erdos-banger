"""Tests for ask logging (DEBT-113)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from erdos.core.ask.logging import log_ask_interaction, read_ask_log_entries


class TestLogAskInteraction:
    """Tests for log_ask_interaction function."""

    def test_creates_log_file(self, tmp_path: Path) -> None:
        """Verify log file is created in expected location."""
        log_path = log_ask_interaction(
            problem_id=848,
            question="What is known?",
            answer="Several partial results exist.",
            sources=[],
            llm_enabled=True,
            log_dir=tmp_path,
        )

        assert log_path.exists()
        assert log_path.name == "problem_848.jsonl"
        assert log_path.parent == tmp_path

    def test_persists_full_answer(self, tmp_path: Path) -> None:
        """Verify full LLM answer is persisted, not just length."""
        answer_text = "This is the full answer from the LLM with all details."

        log_ask_interaction(
            problem_id=6,
            question="What partial results exist?",
            answer=answer_text,
            sources=[],
            llm_enabled=True,
            llm_command="echo 'test'",
            llm_exit_code=0,
            log_dir=tmp_path,
        )

        log_path = tmp_path / "problem_6.jsonl"
        entries = [json.loads(line) for line in log_path.read_text().splitlines()]

        assert len(entries) == 1
        assert entries[0]["answer"] == answer_text  # Full text, not length!
        assert entries[0]["question"] == "What partial results exist?"

    def test_appends_to_existing_log(self, tmp_path: Path) -> None:
        """Verify multiple queries append to same problem log."""
        for i in range(3):
            log_ask_interaction(
                problem_id=100,
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[],
                llm_enabled=True,
                log_dir=tmp_path,
            )

        log_path = tmp_path / "problem_100.jsonl"
        entries = [json.loads(line) for line in log_path.read_text().splitlines()]

        assert len(entries) == 3
        assert [e["question"] for e in entries] == [
            "Question 0",
            "Question 1",
            "Question 2",
        ]

    def test_logs_source_metadata(self, tmp_path: Path) -> None:
        """Verify source metadata is captured."""
        sources = [
            {
                "chunk_id": "chunk_001",
                "source_type": "problem_statement",
                "reference_doi": "10.1234/test",
                "text": "Full source text here",  # Should NOT be in log
            },
        ]

        log_ask_interaction(
            problem_id=42,
            question="Test?",
            answer="Answer",
            sources=sources,
            llm_enabled=True,
            log_dir=tmp_path,
        )

        log_path = tmp_path / "problem_42.jsonl"
        entry = json.loads(log_path.read_text().strip())

        assert entry["source_count"] == 1
        assert entry["sources"][0]["chunk_id"] == "chunk_001"
        assert entry["sources"][0]["source_type"] == "problem_statement"
        # Verify full text is NOT logged (keep logs compact)
        assert "text" not in entry["sources"][0]

    def test_handles_no_llm(self, tmp_path: Path) -> None:
        """Verify logging works when LLM is disabled."""
        log_ask_interaction(
            problem_id=7,
            question="Just a question",
            answer=None,
            sources=[],
            llm_enabled=False,
            log_dir=tmp_path,
        )

        log_path = tmp_path / "problem_7.jsonl"
        entry = json.loads(log_path.read_text().strip())

        assert entry["answer"] is None
        assert entry["llm"]["enabled"] is False

    def test_schema_version_included(self, tmp_path: Path) -> None:
        """Verify schema version is included for future migrations."""
        log_ask_interaction(
            problem_id=1,
            question="Q",
            answer="A",
            sources=[],
            llm_enabled=True,
            log_dir=tmp_path,
        )

        log_path = tmp_path / "problem_1.jsonl"
        entry = json.loads(log_path.read_text().strip())

        assert entry["schema_version"] == 1
        assert "timestamp" in entry
        datetime.fromisoformat(entry["timestamp"])

    def test_read_entries_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Reading a missing log file should return empty results (no error)."""
        entries, parse_errors, log_path = read_ask_log_entries(123, log_dir=tmp_path)
        assert entries == []
        assert parse_errors == 0
        assert log_path == tmp_path / "problem_123.jsonl"

    def test_read_entries_skips_malformed_lines(self, tmp_path: Path) -> None:
        """Malformed JSONL lines should be skipped and counted."""
        log_path = tmp_path / "problem_1.jsonl"
        log_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": 1,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "problem_id": 1,
                            "question": "Q",
                            "answer": "A",
                            "source_count": 0,
                            "sources": [],
                            "llm": {"enabled": False},
                        }
                    ),
                    "{not valid json",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        entries, parse_errors, _ = read_ask_log_entries(1, log_dir=tmp_path)
        assert len(entries) == 1
        assert parse_errors == 1

    def test_read_entries_respects_limit(self, tmp_path: Path) -> None:
        """Only the most recent N entries should be returned."""
        for i in range(5):
            log_ask_interaction(
                problem_id=9,
                question=f"Question {i}",
                answer=f"Answer {i}",
                sources=[],
                llm_enabled=True,
                log_dir=tmp_path,
            )

        entries, parse_errors, _ = read_ask_log_entries(9, log_dir=tmp_path, limit=2)
        assert parse_errors == 0
        assert [e.question for e in entries] == ["Question 3", "Question 4"]
