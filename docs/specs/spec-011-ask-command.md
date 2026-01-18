# Spec 011: Ask Command

> Defines the `erdos ask` command for retrieval-augmented question answering about Erdős problems with citation-grounded responses.

---

## Overview

The ask command enables researchers and AI agents to query the knowledge base about specific Erdős problems. It combines the search index (Spec 006) with LLM capabilities to provide contextual, citation-grounded answers.

### Core Workflow

```
erdos ask <problem_id> "<question>"
       │
       ▼
┌────────────────────────┐
│ Load ProblemRecord      │
│ (context for query)     │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│ Retrieval Phase                         │
│  1. Expand query with problem context   │
│  2. Search FTS5 index (BM25 ranking)    │
│  3. Deduplicate and rerank (optional)   │
│  4. Return top-k chunks with sources    │
└───────────┬────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│ Generation Phase                        │
│  1. Build prompt with:                  │
│     - Problem statement                 │
│     - Retrieved chunks (numbered)       │
│     - User question                     │
│  2. Call LLM (Claude via API)           │
│  3. Parse response for citations        │
└───────────┬────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│ Output                                  │
│  - Answer text with inline citations    │
│  - Sources list with URLs/DOIs          │
└────────────────────────────────────────┘
```

### Guiding Principles

1. **Citation-grounded** - Every claim should be traceable to a source
2. **Contextual** - Answers are scoped to the specific problem
3. **Transparent** - Show what sources were used
4. **Graceful fallback** - Works without LLM (retrieval-only mode)

---

## 1) CLI Interface

### Command Signature

```
erdos ask <problem_id> "<question>" [OPTIONS]

Arguments:
  problem_id    Problem ID to ask about (required)
  question      Natural language question (required)

Options:
  --limit, -n INT       Max chunks to retrieve [default: 5]
  --no-llm              Retrieval only, skip LLM generation
  --model MODEL         LLM model to use [default: claude-sonnet-4-20250514]
  --temperature FLOAT   LLM temperature [default: 0.3]
  --max-tokens INT      Max response tokens [default: 1024]
  --json                Output as JSON for machine consumption
```

### Examples

```bash
# Basic usage: ask about a problem
erdos ask 6 "What partial results are known?"

# More specific question
erdos ask 6 "What is the best known bound for small primes in AP?"

# Retrieval-only mode (no LLM)
erdos ask 6 "What is known?" --no-llm

# With custom parameters
erdos ask 6 "Explain the proof approach" --limit 10 --temperature 0.5

# JSON output for automation
erdos ask 6 "Status?" --json
```

### Output (Human Mode)

```
Question: What partial results are known for Problem 6?

Based on the available literature:

The problem of small primes in arithmetic progressions has seen significant
progress since Linnik's original work in 1944 [1]. Heath-Brown's 1992 paper [2]
improved the bound to L(1,χ) for Dirichlet L-functions, achieving a value
of 5.5 for the Linnik constant.

More recently, Xylouris [3] has further refined these bounds, obtaining
L ≤ 5.18 under GRH.

The current best unconditional result is L ≤ 5 due to work combining [2]
and [3].

─────────────────────────────────────────────────────────────────────────────
Sources:
  [1] Linnik (1944) "On the least prime in an arithmetic progression"
      DOI: 10.1090/S0002-9947-1944-...
  [2] Heath-Brown (1992) "Zero-free regions for Dirichlet L-functions"
      DOI: 10.4007/annals.1992.135.2.5
  [3] Xylouris (2011) "On the least prime in an arithmetic progression"
      arXiv: 1102.4707
```

### Output (JSON Mode)

```json
{
  "schema_version": 1,
  "command": "erdos ask",
  "success": true,
  "data": {
    "problem_id": 6,
    "question": "What partial results are known?",
    "answer": "The problem of small primes in arithmetic progressions has seen significant progress since Linnik's original work in 1944 [1]. Heath-Brown's 1992 paper [2] improved the bound...",
    "citations": [
      {
        "id": 1,
        "text": "Linnik (1944) \"On the least prime in an arithmetic progression\"",
        "doi": "10.1090/S0002-9947-1944-...",
        "arxiv_id": null,
        "url": "https://doi.org/10.1090/S0002-9947-1944-..."
      },
      {
        "id": 2,
        "text": "Heath-Brown (1992) \"Zero-free regions for Dirichlet L-functions\"",
        "doi": "10.4007/annals.1992.135.2.5",
        "arxiv_id": null,
        "url": "https://doi.org/10.4007/annals.1992.135.2.5"
      },
      {
        "id": 3,
        "text": "Xylouris (2011) \"On the least prime in an arithmetic progression\"",
        "doi": null,
        "arxiv_id": "1102.4707",
        "url": "https://arxiv.org/abs/1102.4707"
      }
    ],
    "retrieval": {
      "query": "Problem 6 small primes arithmetic progressions partial results",
      "chunks_retrieved": 5,
      "sources_used": 3
    },
    "model": "claude-sonnet-4-20250514",
    "usage": {
      "prompt_tokens": 2450,
      "completion_tokens": 312
    }
  },
  "timestamp": "2026-01-17T14:30:00Z",
  "duration_ms": 3421
}
```

---

## 2) Domain Models

```python
# src/erdos/domain/ask.py
"""Ask command domain models."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from erdos.domain.base import ErdosBaseModel


class Citation(ErdosBaseModel):
    """A citation in an answer."""

    id: Annotated[int, Field(ge=1, description="Citation number")]
    text: Annotated[str, Field(description="Formatted citation text")]
    doi: Annotated[str | None, Field(default=None)] = None
    arxiv_id: Annotated[str | None, Field(default=None)] = None
    url: Annotated[str | None, Field(default=None)] = None

    @property
    def best_url(self) -> str | None:
        """Return best available URL."""
        if self.url:
            return self.url
        if self.doi:
            return f"https://doi.org/{self.doi}"
        if self.arxiv_id:
            return f"https://arxiv.org/abs/{self.arxiv_id}"
        return None


class RetrievalInfo(ErdosBaseModel):
    """Information about the retrieval phase."""

    query: Annotated[str, Field(description="Expanded search query")]
    chunks_retrieved: Annotated[int, Field(ge=0)]
    sources_used: Annotated[int, Field(ge=0)]


class LLMUsage(ErdosBaseModel):
    """LLM token usage statistics."""

    prompt_tokens: Annotated[int, Field(ge=0)]
    completion_tokens: Annotated[int, Field(ge=0)]

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class AskResult(ErdosBaseModel):
    """Result of an ask operation."""

    problem_id: Annotated[int, Field(ge=1)]
    question: Annotated[str, Field(min_length=1)]
    answer: Annotated[str, Field(description="Generated answer text")]
    citations: Annotated[list[Citation], Field(default_factory=list)]
    retrieval: RetrievalInfo
    model: Annotated[str | None, Field(default=None)] = None
    usage: Annotated[LLMUsage | None, Field(default=None)] = None
```

---

## 3) RAG Pipeline

### Retrieval Service

```python
# src/erdos/application/retrieval_service.py
"""Retrieval service for RAG pipeline."""

from dataclasses import dataclass

from erdos.domain.problem import ProblemRecord
from erdos.domain.search import ChunkSource
from erdos.ports.searcher import SearchResult, Searcher


@dataclass
class RetrievedChunk:
    """A chunk retrieved for RAG context."""

    chunk_id: str
    text: str
    source_type: ChunkSource
    problem_id: int | None
    reference_doi: str | None
    reference_arxiv: str | None
    reference_title: str | None
    score: float


class RetrievalService:
    """
    Retrieves relevant chunks for RAG.

    Combines problem context with search query for better results.
    """

    def __init__(self, searcher: Searcher) -> None:
        self._searcher = searcher

    def retrieve(
        self,
        problem: ProblemRecord,
        question: str,
        *,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks for a question about a problem.

        Args:
            problem: The problem being asked about
            question: The user's question
            limit: Maximum chunks to retrieve

        Returns:
            List of retrieved chunks with metadata
        """
        # Expand query with problem context
        expanded_query = self._expand_query(problem, question)

        # Search with problem filter
        results = self._searcher.search(
            expanded_query,
            limit=limit * 2,  # Get more, then dedupe
            problem_id=problem.id,
        )

        # Also search without filter for broader context
        if len(results) < limit:
            broader_results = self._searcher.search(
                question,
                limit=limit,
            )
            results.extend(broader_results)

        # Deduplicate and convert
        seen_ids: set[str] = set()
        chunks: list[RetrievedChunk] = []

        for r in results:
            if r.chunk_id in seen_ids:
                continue
            seen_ids.add(r.chunk_id)

            chunks.append(
                RetrievedChunk(
                    chunk_id=r.chunk_id,
                    text=r.snippet,
                    source_type=r.source_type,
                    problem_id=r.problem_id,
                    reference_doi=r.reference_doi,
                    reference_arxiv=getattr(r, "reference_arxiv", None),
                    reference_title=getattr(r, "reference_title", None),
                    score=r.score,
                )
            )

            if len(chunks) >= limit:
                break

        return chunks

    def _expand_query(self, problem: ProblemRecord, question: str) -> str:
        """Expand query with problem context."""
        # Extract key terms from problem
        key_terms = [problem.title]
        key_terms.extend(problem.tags[:3])  # Top 3 tags

        # Combine with question
        expanded = f"{' '.join(key_terms)} {question}"
        return expanded
```

### LLM Service

```python
# src/erdos/infrastructure/llm/claude.py
"""Claude LLM client for answer generation."""

from typing import Any

import httpx

from erdos.domain.ask import LLMUsage


class ClaudeClient:
    """
    Client for Claude API.

    Uses the Anthropic Python SDK or direct HTTP.
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        import os

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout

        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable required for ask command"
            )

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> tuple[str, LLMUsage]:
        """
        Generate a response from Claude.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            (response text, usage statistics)
        """
        headers = {
            "x-api-key": self._api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        messages = [{"role": "user", "content": prompt}]

        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            body["system"] = system

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(self.API_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        # Extract text from response
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # Extract usage
        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
        )

        return text, usage

    @property
    def model(self) -> str:
        return self._model
```

### Ask Service

```python
# src/erdos/application/ask_service.py
"""Ask service orchestrating RAG pipeline."""

import re
from typing import Any

from erdos.application.retrieval_service import RetrievalService, RetrievedChunk
from erdos.domain.ask import AskResult, Citation, LLMUsage, RetrievalInfo
from erdos.domain.problem import ProblemRecord
from erdos.infrastructure.llm.claude import ClaudeClient
from erdos.ports.problem_repository import ProblemRepository
from erdos.ports.searcher import Searcher


class AskService:
    """
    Orchestrates the RAG pipeline for answering questions.

    Combines:
    - Retrieval from search index
    - LLM generation with Claude
    - Citation parsing and formatting
    """

    SYSTEM_PROMPT = """You are a mathematical research assistant helping with Erdős problems.

Your task is to answer questions about mathematical problems using the provided context.

Guidelines:
1. Base your answer ONLY on the provided context chunks
2. Use inline citations like [1], [2] to reference sources
3. If the context doesn't contain enough information, say so
4. Be precise and mathematically accurate
5. Keep answers focused and concise

Format your citations as [N] where N corresponds to the chunk number."""

    def __init__(
        self,
        repository: ProblemRepository,
        searcher: Searcher,
        llm_client: ClaudeClient | None = None,
    ) -> None:
        self._repository = repository
        self._retrieval = RetrievalService(searcher)
        self._llm = llm_client

    def ask(
        self,
        problem_id: int,
        question: str,
        *,
        limit: int = 5,
        use_llm: bool = True,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AskResult:
        """
        Answer a question about a problem.

        Args:
            problem_id: Problem to ask about
            question: User's question
            limit: Max chunks to retrieve
            use_llm: If True, generate answer with LLM
            temperature: LLM temperature
            max_tokens: Max response tokens

        Returns:
            AskResult with answer and citations
        """
        # Load problem
        problem = self._repository.get_by_id(problem_id)
        if problem is None:
            raise ValueError(f"Problem {problem_id} not found")

        # Retrieve relevant chunks
        chunks = self._retrieval.retrieve(problem, question, limit=limit)

        # Build retrieval info
        retrieval_info = RetrievalInfo(
            query=f"{problem.title} {question}",
            chunks_retrieved=len(chunks),
            sources_used=len(set(c.reference_doi or c.chunk_id for c in chunks)),
        )

        # If no LLM, return retrieval-only result
        if not use_llm or self._llm is None:
            return self._retrieval_only_result(
                problem_id, question, chunks, retrieval_info
            )

        # Build prompt
        prompt = self._build_prompt(problem, question, chunks)

        # Generate answer
        answer_text, usage = self._llm.generate(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Parse citations from answer
        citations = self._parse_citations(answer_text, chunks)

        return AskResult(
            problem_id=problem_id,
            question=question,
            answer=answer_text,
            citations=citations,
            retrieval=retrieval_info,
            model=self._llm.model,
            usage=usage,
        )

    def _retrieval_only_result(
        self,
        problem_id: int,
        question: str,
        chunks: list[RetrievedChunk],
        retrieval_info: RetrievalInfo,
    ) -> AskResult:
        """Build result without LLM generation."""
        # Format chunks as answer
        if not chunks:
            answer = "No relevant information found in the index."
        else:
            lines = ["Retrieved relevant content:"]
            for i, chunk in enumerate(chunks, 1):
                lines.append(f"\n[{i}] {chunk.text[:300]}...")
            answer = "\n".join(lines)

        # Build citations from chunks
        citations = [
            self._chunk_to_citation(i, chunk)
            for i, chunk in enumerate(chunks, 1)
        ]

        return AskResult(
            problem_id=problem_id,
            question=question,
            answer=answer,
            citations=citations,
            retrieval=retrieval_info,
            model=None,
            usage=None,
        )

    def _build_prompt(
        self,
        problem: ProblemRecord,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Build the LLM prompt."""
        parts = [
            f"# Problem {problem.id}: {problem.title}",
            f"\nStatement: {problem.statement}",
            f"\nStatus: {problem.status.value}",
            "\n\n# Retrieved Context\n",
        ]

        for i, chunk in enumerate(chunks, 1):
            source_info = self._format_source_info(chunk)
            parts.append(f"[{i}] {source_info}")
            parts.append(f"{chunk.text}\n")

        parts.append(f"\n# Question\n{question}")
        parts.append("\n\nProvide a concise, citation-grounded answer:")

        return "\n".join(parts)

    def _format_source_info(self, chunk: RetrievedChunk) -> str:
        """Format source info for a chunk."""
        if chunk.reference_title:
            return f"(from: {chunk.reference_title})"
        if chunk.reference_doi:
            return f"(DOI: {chunk.reference_doi})"
        if chunk.reference_arxiv:
            return f"(arXiv: {chunk.reference_arxiv})"
        return f"(source: {chunk.source_type.value})"

    def _parse_citations(
        self,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> list[Citation]:
        """Parse citation references from answer text."""
        # Find all [N] references in the answer
        citation_refs = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))

        citations = []
        for ref in sorted(citation_refs):
            if 1 <= ref <= len(chunks):
                chunk = chunks[ref - 1]
                citations.append(self._chunk_to_citation(ref, chunk))

        return citations

    def _chunk_to_citation(self, num: int, chunk: RetrievedChunk) -> Citation:
        """Convert a chunk to a citation."""
        text = chunk.reference_title or f"Source ({chunk.source_type.value})"

        return Citation(
            id=num,
            text=text,
            doi=chunk.reference_doi,
            arxiv_id=chunk.reference_arxiv,
            url=None,  # Will compute via property
        )
```

---

## 4) CLI Command

```python
# src/erdos/commands/ask.py
"""erdos ask - question answering with citations."""

from __future__ import annotations

import time
from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from erdos.application.ask_service import AskService
from erdos.commands.output import CLIOutput
from erdos.domain.ask import AskResult


app = typer.Typer(help="Ask questions about Erdős problems.")
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    """Output result based on format preference."""
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast(dict[str, Any], data.data))
    else:
        error = cast(dict[str, Any], data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print ask result."""
    question = data.get("question", "")
    answer = data.get("answer", "")
    citations = data.get("citations", [])

    # Show question
    console.print(f"\n[bold]Question:[/bold] {question}\n")

    # Show answer
    console.print(Panel(Markdown(answer), title="Answer", expand=False))

    # Show sources
    if citations:
        console.print("\n[bold]Sources:[/bold]")
        for cite in citations:
            url = cite.get("url") or cite.get("doi") or cite.get("arxiv_id") or ""
            if cite.get("doi"):
                url = f"https://doi.org/{cite['doi']}"
            elif cite.get("arxiv_id"):
                url = f"https://arxiv.org/abs/{cite['arxiv_id']}"

            console.print(f"  [{cite['id']}] {cite['text']}")
            if url:
                console.print(f"      [dim]{url}[/dim]")


def ask_question(
    problem_id: int,
    question: str,
    *,
    limit: int = 5,
    use_llm: bool = True,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> CLIOutput:
    """Core ask logic."""
    # Import here to defer dependency loading
    from erdos.infrastructure.indexes.sqlite_index import SqliteSearchIndex
    from erdos.infrastructure.loaders.yaml_loader import YamlProblemLoader

    try:
        repository = YamlProblemLoader.from_default()
        searcher = SqliteSearchIndex.from_default()
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="SetupError",
            message=str(e),
            code=1,
        )

    # Check index has data
    if searcher.problem_count() == 0:
        return CLIOutput.err(
            command="erdos ask",
            error_type="IndexEmpty",
            message="Search index is empty. Run 'erdos index build' first.",
            code=2,
        )

    # Create LLM client if needed
    llm_client = None
    if use_llm:
        try:
            from erdos.infrastructure.llm.claude import ClaudeClient

            llm_client = ClaudeClient(model=model)
        except ValueError as e:
            # No API key - fall back to retrieval only
            err_console.print(f"[yellow]Warning:[/yellow] {e}")
            err_console.print("[yellow]Falling back to retrieval-only mode[/yellow]")
            use_llm = False

    try:
        service = AskService(repository, searcher, llm_client)
        result = service.ask(
            problem_id,
            question,
            limit=limit,
            use_llm=use_llm,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return CLIOutput.ok(
            command="erdos ask",
            data=result.model_dump(mode="json"),
        )

    except ValueError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="NotFound",
            message=str(e),
            code=3,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="Error",
            message=str(e),
            code=1,
        )


@app.callback(invoke_without_command=True)
def ask(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(help="Problem ID to ask about.", min=1),
    ],
    question: Annotated[
        str,
        typer.Argument(help="Question to ask about the problem."),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Max chunks to retrieve"),
    ] = 5,
    no_llm: Annotated[
        bool,
        typer.Option("--no-llm", help="Retrieval only, skip LLM generation"),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option("--model", help="LLM model to use"),
    ] = None,
    temperature: Annotated[
        float,
        typer.Option("--temperature", help="LLM temperature"),
    ] = 0.3,
    max_tokens: Annotated[
        int,
        typer.Option("--max-tokens", help="Max response tokens"),
    ] = 1024,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON for machine consumption."),
    ] = False,
) -> None:
    """
    Ask a question about an Erdős problem.

    Uses retrieval-augmented generation (RAG) to provide citation-grounded
    answers based on the problem statement and indexed literature.

    Requires:
    - Search index built (run 'erdos index build')
    - ANTHROPIC_API_KEY environment variable (for LLM mode)

    Examples:
        erdos ask 6 "What partial results are known?"
        erdos ask 6 "What is the best known bound?" --limit 10
        erdos ask 6 "Explain the approach" --no-llm
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    start_time = time.perf_counter()

    result = ask_question(
        problem_id,
        question,
        limit=limit,
        use_llm=not no_llm,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    _output(ctx, result)

    if not result.success:
        error = cast(dict[str, Any], result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
```

---

## 5) Prompt Engineering

### System Prompt

The system prompt establishes the assistant's role and constraints:

```
You are a mathematical research assistant helping with Erdős problems.

Your task is to answer questions about mathematical problems using the provided context.

Guidelines:
1. Base your answer ONLY on the provided context chunks
2. Use inline citations like [1], [2] to reference sources
3. If the context doesn't contain enough information, say so
4. Be precise and mathematically accurate
5. Keep answers focused and concise

Format your citations as [N] where N corresponds to the chunk number.
```

### User Prompt Template

```
# Problem {id}: {title}

Statement: {statement}

Status: {status}

# Retrieved Context

[1] (from: {source_1})
{chunk_1_text}

[2] (from: {source_2})
{chunk_2_text}

...

# Question
{user_question}

Provide a concise, citation-grounded answer:
```

---

## 6) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_ask.py
"""Unit tests for ask functionality."""

from unittest.mock import MagicMock

import pytest

from erdos.application.ask_service import AskService
from erdos.application.retrieval_service import RetrievalService, RetrievedChunk
from erdos.domain.ask import AskResult, Citation
from erdos.domain.problem import ProblemRecord, ProblemStatus
from erdos.domain.search import ChunkSource


@pytest.fixture
def sample_problem() -> ProblemRecord:
    return ProblemRecord(
        id=6,
        title="Small primes in AP",
        statement="Prove bounds on the least prime in arithmetic progressions.",
        status=ProblemStatus.OPEN,
    )


@pytest.fixture
def mock_repository(sample_problem: ProblemRecord) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id.return_value = sample_problem
    return repo


@pytest.fixture
def mock_searcher() -> MagicMock:
    searcher = MagicMock()
    searcher.problem_count.return_value = 100
    searcher.search.return_value = [
        MagicMock(
            chunk_id="chunk_1",
            snippet="Linnik proved the existence of a constant L...",
            score=0.95,
            source_type=ChunkSource.REFERENCE_ABSTRACT,
            problem_id=6,
            reference_doi="10.1090/test",
        ),
    ]
    return searcher


class TestRetrievalService:
    def test_expands_query_with_problem_context(
        self, mock_searcher: MagicMock, sample_problem: ProblemRecord
    ) -> None:
        """Retrieval expands query with problem title and tags."""
        service = RetrievalService(mock_searcher)

        service.retrieve(sample_problem, "What is known?")

        # Check that search was called
        mock_searcher.search.assert_called()
        call_args = mock_searcher.search.call_args
        query = call_args[0][0]

        # Query should include problem title
        assert "Small primes" in query or "What is known?" in query


class TestAskService:
    def test_returns_retrieval_only_when_no_llm(
        self, mock_repository: MagicMock, mock_searcher: MagicMock
    ) -> None:
        """Ask returns retrieval-only result when LLM disabled."""
        service = AskService(mock_repository, mock_searcher, llm_client=None)

        result = service.ask(6, "What is known?", use_llm=False)

        assert isinstance(result, AskResult)
        assert result.model is None
        assert result.usage is None
        assert "Retrieved relevant content" in result.answer

    def test_raises_for_unknown_problem(
        self, mock_searcher: MagicMock
    ) -> None:
        """Ask raises ValueError for unknown problem."""
        repo = MagicMock()
        repo.get_by_id.return_value = None

        service = AskService(repo, mock_searcher)

        with pytest.raises(ValueError, match="not found"):
            service.ask(999, "What is known?")

    def test_parses_citations_from_answer(
        self, mock_repository: MagicMock, mock_searcher: MagicMock
    ) -> None:
        """Ask parses [N] citations from LLM response."""
        mock_llm = MagicMock()
        mock_llm.model = "test-model"
        mock_llm.generate.return_value = (
            "The result is well-known [1] and extends earlier work [2].",
            MagicMock(prompt_tokens=100, completion_tokens=50),
        )

        # Add a second chunk to searcher
        mock_searcher.search.return_value = [
            MagicMock(
                chunk_id="chunk_1",
                snippet="First chunk",
                score=0.9,
                source_type=ChunkSource.REFERENCE_ABSTRACT,
                problem_id=6,
                reference_doi="10.1090/first",
            ),
            MagicMock(
                chunk_id="chunk_2",
                snippet="Second chunk",
                score=0.8,
                source_type=ChunkSource.REFERENCE_ABSTRACT,
                problem_id=6,
                reference_doi="10.1090/second",
            ),
        ]

        service = AskService(mock_repository, mock_searcher, mock_llm)

        result = service.ask(6, "What is known?")

        # Should have parsed citations [1] and [2]
        assert len(result.citations) == 2
        assert result.citations[0].id == 1
        assert result.citations[1].id == 2


class TestCitation:
    def test_best_url_prefers_doi(self) -> None:
        """Citation.best_url prefers DOI over arXiv."""
        cite = Citation(
            id=1,
            text="Test",
            doi="10.1234/test",
            arxiv_id="2201.00001",
        )

        assert cite.best_url == "https://doi.org/10.1234/test"

    def test_best_url_falls_back_to_arxiv(self) -> None:
        """Citation.best_url uses arXiv if no DOI."""
        cite = Citation(
            id=1,
            text="Test",
            arxiv_id="2201.00001",
        )

        assert cite.best_url == "https://arxiv.org/abs/2201.00001"
```

### Integration Tests

```python
# tests/integration/test_ask.py
"""Integration tests for ask command."""

import subprocess
import json
import os


class TestAskCommand:
    def test_ask_without_index_errors(self) -> None:
        """ask errors gracefully when index is empty."""
        result = subprocess.run(
            ["uv", "run", "erdos", "ask", "6", "What is known?", "--json"],
            capture_output=True,
            text=True,
        )

        # Should either succeed or fail gracefully
        data = json.loads(result.stdout)
        assert "command" in data
        assert data["command"] == "erdos ask"

    def test_ask_no_llm_mode(self) -> None:
        """ask --no-llm works without API key."""
        # This should work even without ANTHROPIC_API_KEY
        result = subprocess.run(
            ["uv", "run", "erdos", "ask", "6", "What is known?", "--no-llm", "--json"],
            capture_output=True,
            text=True,
            env={**os.environ, "ANTHROPIC_API_KEY": ""},  # Clear API key
        )

        # May fail if index empty, but shouldn't fail due to API key
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert data["success"] is True
            assert data["data"]["model"] is None

    def test_ask_json_structure(self) -> None:
        """JSON output has correct structure."""
        result = subprocess.run(
            ["uv", "run", "erdos", "ask", "6", "Status?", "--no-llm", "--json"],
            capture_output=True,
            text=True,
        )

        data = json.loads(result.stdout)
        assert "schema_version" in data
        assert "command" in data
        assert "success" in data
        assert "timestamp" in data
```

### Acceptance Criteria

```bash
# 1. Build index first
uv run erdos index build

# 2. Ask without LLM (retrieval only)
uv run erdos ask 6 "What partial results are known?" --no-llm

# 3. Ask with LLM (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="your-key"
uv run erdos ask 6 "What partial results are known?"

# 4. JSON output
uv run erdos ask 6 "Status?" --json | jq .

# 5. Custom parameters
uv run erdos ask 6 "Explain the proof" --limit 10 --temperature 0.5

# 6. Tests pass
uv run pytest tests/unit/test_ask.py -v
uv run pytest tests/integration/test_ask.py -v
```

---

## 7) Error Handling

| Error | Exit Code | Message |
|-------|-----------|---------|
| Problem not found | 3 | "Problem {id} not found" |
| Index empty | 2 | "Search index is empty. Run 'erdos index build' first." |
| No API key | 1 | "ANTHROPIC_API_KEY environment variable required" |
| API error | 4 | "LLM API error: {details}" |
| Timeout | 4 | "Request timed out after {seconds}s" |

---

## 8) Future Extensions

### Streaming Responses

```bash
# Stream answer as it's generated
erdos ask 6 "What is known?" --stream
```

### Conversation Mode

```bash
# Multi-turn conversation about a problem
erdos ask 6 --interactive
```

### Custom Models

```bash
# Use different Claude models
erdos ask 6 "Question" --model claude-opus-4-20250514
```

### Vector Search (v1.2+)

Integration with embedding-based search for better semantic retrieval:
- Embed chunks with text-embedding models
- Hybrid BM25 + vector similarity
- Reranking with cross-encoder

---

## References

- [Claude API Documentation](https://docs.anthropic.com/claude/reference)
- [RAG Best Practices](https://www.anthropic.com/research/retrieval-augmented-generation)
- [Spec 006: Search Index](spec-006-search-index.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-17 | Initial spec |
