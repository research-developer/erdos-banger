"""Proof repository verification (SPEC-035).

# exempt: DEBT-092 (596 LOC; verification pipeline has 6 bounded contexts:
#   clone, build, no-sorries check, provenance, env sanitization, logs)

This module handles cloning and verifying Lean proofs from external repositories.

SECURITY WARNING: Verification runs untrusted build tooling (`lake build`).
Only use with explicit --verify flag after user consent.

Guardrails (per SPEC-035):
1. Verification is opt-in (--verify flag)
2. Runs in temp directory (never modifies working tree)
3. Sanitizes environment (no API keys passed)
4. Bounded logs (truncated stdout/stderr)
5. Never runs git hooks or recursive submodule updates
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from erdos.core.sync.models import (
    ProofLink,
    ProofProvenance,
    VerificationStatus,
    VerificationStrength,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants
# =============================================================================

# Timeouts (in seconds)
CLONE_TIMEOUT = 120  # 2 minutes for git clone
BUILD_TIMEOUT = 600  # 10 minutes for lake build
NO_SORRIES_TIMEOUT = 120  # 2 minutes for no-sorries check

# Log limits
MAX_LOG_SIZE = 100_000  # 100KB max log size

# Environment variables to strip (security)
STRIPPED_ENV_VARS = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GITLAB_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "API_KEY",
        "SECRET_KEY",
    }
)


# =============================================================================
# Result types
# =============================================================================


@dataclass
class VerificationResult:
    """Result of verifying a proof repository."""

    status: VerificationStatus
    strength: VerificationStrength
    error: str | None = None
    repo_commit: str | None = None
    toolchain: str | None = None
    verified_files: list[str] = field(default_factory=list)
    log_content: str = ""
    verification_command: str | None = None


@dataclass
class CloneResult:
    """Result of cloning a repository."""

    success: bool
    path: Path | None = None
    commit: str | None = None
    error: str | None = None


# =============================================================================
# Environment sanitization
# =============================================================================


def _sanitize_env() -> dict[str, str]:
    """Create a sanitized environment for subprocess execution.

    Strips API keys and sensitive credentials from the environment.
    """
    return {
        key: value
        for key, value in os.environ.items()
        if key not in STRIPPED_ENV_VARS
        and not key.endswith("_API_KEY")
        and not key.endswith("_TOKEN")
        and not key.endswith("_SECRET")
    }


# =============================================================================
# Git operations
# =============================================================================


def clone_repository(
    url: str,
    dest: Path,
    *,
    timeout: float = CLONE_TIMEOUT,
    depth: int = 1,
) -> CloneResult:
    """Clone a repository to a destination directory.

    Args:
        url: Repository URL (https only)
        dest: Destination directory
        timeout: Clone timeout in seconds
        depth: Git clone depth (1 for shallow)

    Returns:
        CloneResult with success status and commit hash
    """
    if not url.startswith("https://"):
        return CloneResult(success=False, error="Only HTTPS URLs are allowed")

    try:
        # Shallow clone without hooks or submodules
        # S603/S607: Intentional - we run git with controlled args, URL is validated
        cmd = [
            "git",
            "clone",
            "--depth",
            str(depth),
            "--no-recurse-submodules",
            "--config",
            "core.hooksPath=/dev/null",
            url,
            str(dest),
        ]
        result = subprocess.run(  # noqa: S603
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env=_sanitize_env(),
            check=False,
        )

        if result.returncode != 0:
            return CloneResult(
                success=False,
                error=f"Git clone failed: {result.stderr.strip()[:500]}",
            )

        # Get commit hash
        # S607: Intentional - git is a standard system command
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=dest,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

        return CloneResult(success=True, path=dest, commit=commit)

    except subprocess.TimeoutExpired:
        return CloneResult(success=False, error=f"Clone timed out after {timeout}s")
    except FileNotFoundError:
        return CloneResult(success=False, error="git command not found")
    except Exception as e:
        return CloneResult(success=False, error=str(e))


# =============================================================================
# Lean verification
# =============================================================================


def _read_toolchain(repo_path: Path) -> str | None:
    """Read lean-toolchain file if present."""
    toolchain_path = repo_path / "lean-toolchain"
    if toolchain_path.exists():
        try:
            return toolchain_path.read_text(encoding="utf-8").strip()
        except Exception:
            return None
    return None


def _truncate_log(log: str, max_size: int = MAX_LOG_SIZE) -> str:
    """Truncate log to max size with truncation notice."""
    if len(log) <= max_size:
        return log
    return log[:max_size] + "\n\n[... log truncated ...]"


def run_lake_build(
    repo_path: Path,
    *,
    timeout: float = BUILD_TIMEOUT,
) -> tuple[bool, str]:
    """Run `lake build` in the repository.

    Args:
        repo_path: Path to the cloned repository
        timeout: Build timeout in seconds

    Returns:
        Tuple of (success, log_content)
    """
    try:
        # S607: Intentional - lake is the Lean build tool
        result = subprocess.run(
            ["lake", "build"],  # noqa: S607
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_sanitize_env(),
            check=False,
        )

        log = f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}"
        log = _truncate_log(log)

        return result.returncode == 0, log

    except subprocess.TimeoutExpired:
        return False, f"Build timed out after {timeout}s"
    except FileNotFoundError:
        return False, "lake command not found (is Lean/elan installed?)"
    except Exception as e:
        return False, f"Build error: {e}"


def _find_problem_files(repo_path: Path, problem_id: int) -> list[Path]:
    """Find Lean files that might contain the proof for a specific problem.

    Searches for files matching common naming patterns.
    """
    patterns = [
        f"**/Problem{problem_id}.lean",
        f"**/problem{problem_id}.lean",
        f"**/P{problem_id}.lean",
        f"**/Erdos{problem_id}.lean",
        f"**/*{problem_id}*.lean",
    ]

    found: list[Path] = []
    for pattern in patterns:
        found.extend(repo_path.glob(pattern))

    # Deduplicate and sort
    return sorted(set(found))


def check_no_sorries(
    repo_path: Path,
    lean_file: Path,
    *,
    timeout: float = NO_SORRIES_TIMEOUT,
) -> tuple[bool, str]:
    """Check a Lean file for sorry statements.

    Uses `lake env lean --no-sorry` to verify no sorry statements exist.

    Args:
        repo_path: Repository root (for lake env)
        lean_file: Path to the Lean file to check
        timeout: Check timeout in seconds

    Returns:
        Tuple of (no_sorries_found, log_content)
    """

    def _looks_like_unknown_option(combined_output: str, option: str) -> bool:
        if option not in combined_output:
            return False
        return (
            "unknown option" in combined_output
            or "unrecognized option" in combined_output
            or "invalid option" in combined_output
            or "unknown flag" in combined_output
        )

    try:
        # Use lake env to get proper Lean environment, then check with --no-sorry.
        #
        # NOTE: The flag name is `--no-sorry` (singular). Some older/alternate
        # toolchains may not support it, so we fall back to a plain compile and
        # detect sorry warnings in output.
        #
        # S603/S607: Intentional - lake is the Lean build tool
        attempts: list[list[str]] = [
            ["lake", "env", "lean", "--no-sorry", str(lean_file)],
            ["lake", "env", "lean", "--no-sorries", str(lean_file)],
            ["lake", "env", "lean", str(lean_file)],
        ]
        last_result: subprocess.CompletedProcess[str] | None = None
        last_cmd: list[str] | None = None

        for cmd in attempts:
            last_cmd = cmd
            last_result = subprocess.run(  # noqa: S603
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_sanitize_env(),
                check=False,
            )

            combined = f"{last_result.stdout}\n{last_result.stderr}".lower()
            if "--no-sorry" in cmd and _looks_like_unknown_option(
                combined, "--no-sorry"
            ):
                continue
            if "--no-sorries" in cmd and _looks_like_unknown_option(
                combined, "--no-sorries"
            ):
                continue
            break

        if last_result is None or last_cmd is None:
            return False, "No-sorries check internal error: no attempts executed"

        log = (
            "=== COMMAND ===\n"
            + " ".join(last_cmd)
            + "\n\n=== STDOUT ===\n"
            + last_result.stdout
            + "\n\n=== STDERR ===\n"
            + last_result.stderr
        )
        log = _truncate_log(log)

        # With --no-sorry, return code is sufficient: sorries become errors.
        if "--no-sorry" in last_cmd or "--no-sorries" in last_cmd:
            return last_result.returncode == 0, log

        # Fallback: detect sorry warnings in output.
        has_sorry = "sorry" in combined
        return last_result.returncode == 0 and not has_sorry, log

    except subprocess.TimeoutExpired:
        return False, f"No-sorries check timed out after {timeout}s"
    except FileNotFoundError:
        return False, "lake command not found"
    except Exception as e:
        return False, f"Check error: {e}"


# =============================================================================
# Main verification function
# =============================================================================


def _verify_problem_files(
    repo_dir: Path,
    problem_id: int,
    logs: list[str],
) -> list[str]:
    """Verify problem-specific files for sorries.

    Args:
        repo_dir: Repository directory
        problem_id: Problem ID to search for
        logs: Log list to append to

    Returns:
        List of verified file paths (no sorries)
    """
    problem_files = _find_problem_files(repo_dir, problem_id)
    verified_files: list[str] = []

    if not problem_files:
        logs.append("Could not identify problem-specific files")
        return verified_files

    logs.append(f"Found {len(problem_files)} potential problem file(s)")

    for pf in problem_files[:3]:  # Check at most 3 files
        relative_path = str(pf.relative_to(repo_dir))
        logs.append(f"Checking {relative_path} for sorries...")

        no_sorry, check_log = check_no_sorries(repo_dir, pf)
        logs.append(check_log)

        if no_sorry:
            verified_files.append(relative_path)
            logs.append(f"✓ {relative_path} has no sorries")
        else:
            logs.append(f"✗ {relative_path} contains sorry or check failed")

    return verified_files


def verify_proof(
    link: ProofLink,
    problem_id: int,
    *,
    work_dir: Path | None = None,
    clone_timeout: float = CLONE_TIMEOUT,
    build_timeout: float = BUILD_TIMEOUT,
) -> VerificationResult:
    """Clone and verify a proof repository.

    This is the main verification entry point. It:
    1. Clones the repository to a temp directory
    2. Runs `lake build` to verify compilation
    3. Attempts to find and verify problem-specific files

    Args:
        link: ProofLink with repository URL
        problem_id: Problem ID being verified
        work_dir: Working directory (temp if not provided)
        clone_timeout: Git clone timeout
        build_timeout: Lake build timeout

    Returns:
        VerificationResult with status, strength, and logs
    """
    logs: list[str] = []
    cleanup_temp = work_dir is None

    if work_dir is None:
        temp_dir = tempfile.mkdtemp(prefix=f"erdos_verify_{problem_id}_")
        work_dir = Path(temp_dir)

    try:
        repo_dir = work_dir / "repo"
        logs.append(f"Cloning {link.url}...")

        # Clone repository
        clone_result = clone_repository(link.url, repo_dir, timeout=clone_timeout)

        if not clone_result.success:
            return VerificationResult(
                status=VerificationStatus.SOURCE_UNAVAILABLE,
                strength=VerificationStrength.NONE,
                error=clone_result.error,
                log_content="\n".join(logs),
            )

        logs.append(f"Cloned successfully (commit: {clone_result.commit})")

        # Read toolchain
        toolchain = _read_toolchain(repo_dir)
        if toolchain:
            logs.append(f"Toolchain: {toolchain}")

        # Run lake build
        logs.append("Running lake build...")
        build_success, build_log = run_lake_build(repo_dir, timeout=build_timeout)
        logs.append(build_log)

        if not build_success:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                strength=VerificationStrength.NONE,
                error="lake build failed",
                repo_commit=clone_result.commit,
                toolchain=toolchain,
                log_content="\n".join(logs),
                verification_command="lake build",
            )

        logs.append("Build succeeded!")

        # Verify problem-specific files
        verified_files = _verify_problem_files(repo_dir, problem_id, logs)

        if verified_files:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                strength=VerificationStrength.NO_SORRIES,
                repo_commit=clone_result.commit,
                toolchain=toolchain,
                verified_files=verified_files,
                log_content="\n".join(logs),
                verification_command="lake build + lake env lean",
            )

        # Build passed but couldn't verify no sorries
        return VerificationResult(
            status=VerificationStatus.INCONCLUSIVE,
            strength=VerificationStrength.BUILD_ONLY,
            error="Could not verify no sorries in problem-specific files",
            repo_commit=clone_result.commit,
            toolchain=toolchain,
            log_content="\n".join(logs),
            verification_command="lake build",
        )

    finally:
        if cleanup_temp and work_dir.exists():
            # S110: Best-effort cleanup of temp directory (non-critical)
            try:
                shutil.rmtree(work_dir)
            except Exception:
                logger.debug("Failed to clean up temp directory: %s", work_dir)


# =============================================================================
# Provenance management
# =============================================================================


def create_provenance(
    problem_id: int,
    link: ProofLink,
    verification: VerificationResult | None = None,
) -> ProofProvenance:
    """Create a provenance record for a proof.

    Args:
        problem_id: Problem ID
        link: The proof link
        verification: Optional verification result

    Returns:
        ProofProvenance record
    """
    now = datetime.now(UTC)

    if verification is None:
        return ProofProvenance(
            problem_id=problem_id,
            forum_thread_url=f"https://www.erdosproblems.com/forum/thread/{problem_id}",
            extracted_at=now,
            repo_url=link.url,
            posted_by=link.author,
            posted_at=link.posted_at,
        )

    return ProofProvenance(
        problem_id=problem_id,
        forum_thread_url=f"https://www.erdosproblems.com/forum/thread/{problem_id}",
        extracted_at=now,
        repo_url=link.url,
        repo_commit=verification.repo_commit,
        posted_by=link.author,
        posted_at=link.posted_at,
        verification_status=verification.status,
        verification_strength=verification.strength,
        verification_error=verification.error,
        verified_at=now
        if verification.status != VerificationStatus.UNVERIFIED
        else None,
        verification_command=verification.verification_command,
        toolchain=verification.toolchain,
        verified_files=verification.verified_files,
    )


def save_provenance(
    provenance: ProofProvenance,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Save provenance record to disk.

    Creates: <cache_dir>/<problem_id>/provenance.json

    Args:
        provenance: ProofProvenance to save
        cache_dir: Base cache directory

    Returns:
        Path to saved file
    """
    if cache_dir is None:
        cache_dir = Path("data/sync_cache/proofs")

    problem_dir = cache_dir / str(provenance.problem_id)
    problem_dir.mkdir(parents=True, exist_ok=True)

    output_path = problem_dir / "provenance.json"

    # Serialize with Pydantic
    data = provenance.model_dump(mode="json")

    # Atomic write
    tmp_path = output_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp_path.replace(output_path)

    return output_path


def save_verification_log(
    problem_id: int,
    log_content: str,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Save verification log to disk.

    Creates: <cache_dir>/<problem_id>/verify.log

    Args:
        problem_id: Problem ID
        log_content: Log content to save
        cache_dir: Base cache directory

    Returns:
        Path to saved file
    """
    if cache_dir is None:
        cache_dir = Path("data/sync_cache/proofs")

    problem_dir = cache_dir / str(problem_id)
    problem_dir.mkdir(parents=True, exist_ok=True)

    output_path = problem_dir / "verify.log"

    # Atomic write
    tmp_path = output_path.with_suffix(".log.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(log_content)
    tmp_path.replace(output_path)

    return output_path
