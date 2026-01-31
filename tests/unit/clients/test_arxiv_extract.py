"""Unit tests for arXiv source extraction."""

import gzip
import io
import tarfile

import pytest

from erdos.core.clients.arxiv import extract_arxiv_text


def test_extract_arxiv_text_largest_tex_wins():
    """Test that the largest .tex file is selected for extraction."""
    # Create a synthetic tar.gz with multiple .tex files
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add smaller .tex file
        small_tex = (
            b"\\documentclass{article}\n\\begin{document}\nSmall.\n\\end{document}"
        )
        small_info = tarfile.TarInfo(name="small.tex")
        small_info.size = len(small_tex)
        tar.addfile(small_info, io.BytesIO(small_tex))

        # Add larger .tex file
        large_tex = (
            b"\\documentclass{article}\n"
            b"\\begin{document}\n"
            b"This is the main content with more text. " * 20 + b"\n\\end{document}"
        )
        large_info = tarfile.TarInfo(name="main.tex")
        large_info.size = len(large_tex)
        tar.addfile(large_info, io.BytesIO(large_tex))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should extract the larger file (main.tex)
    assert b"main content" in result
    assert b"Small." not in result


def test_extract_arxiv_text_nested_tex_files():
    """Test extraction works with .tex files in subdirectories."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add .tex file in subdirectory
        tex_content = b"\\documentclass{article}\n\\begin{document}\nNested content.\n\\end{document}"
        tex_info = tarfile.TarInfo(name="src/main.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    assert b"Nested content" in result


def test_extract_arxiv_text_caps_at_2mb():
    """Test that extracted text is capped at 2 MiB."""
    # Create a very large .tex file (3 MiB)
    large_content = b"x" * (3 * 1024 * 1024)  # 3 MiB
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_info = tarfile.TarInfo(name="huge.tex")
        tex_info.size = len(large_content)
        tar.addfile(tex_info, io.BytesIO(large_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should be capped at 2 MiB
    assert len(result) == 2 * 1024 * 1024


def test_extract_arxiv_text_no_tex_files():
    """Test extraction fails gracefully when no .tex files present."""
    # Create tar with only non-.tex files
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        readme_content = b"This is a README file"
        readme_info = tarfile.TarInfo(name="README.md")
        readme_info.size = len(readme_content)
        tar.addfile(readme_info, io.BytesIO(readme_content))

    tar_buffer.seek(0)

    with pytest.raises(ValueError, match=r"No \.tex files found"):
        extract_arxiv_text(tar_buffer.read())


def test_extract_arxiv_text_utf8_decode_with_errors_replace():
    """Test that invalid UTF-8 sequences are replaced, not crashed."""
    # Create .tex file with invalid UTF-8
    tex_content = b"Valid text \xff\xfe invalid bytes more text"
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tex_info = tarfile.TarInfo(name="mixed.tex")
        tex_info.size = len(tex_content)
        tar.addfile(tex_info, io.BytesIO(tex_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should decode successfully with replacement characters
    assert b"Valid text" in result
    assert b"more text" in result
    # The invalid bytes should be replaced (exact replacement depends on implementation)


def test_extract_arxiv_text_empty_tarball():
    """Test extraction with empty tarball."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz"):
        pass  # Empty tarball

    tar_buffer.seek(0)

    with pytest.raises(ValueError, match=r"No \.tex files found"):
        extract_arxiv_text(tar_buffer.read())


def test_extract_arxiv_text_single_file_gzip():
    """Test extraction of single gzip-compressed .tex file (BUG-054)."""
    # Create a single .tex file content
    tex_content = (
        b"\\documentclass{article}\n"
        b"\\begin{document}\n"
        b"This is a gzipped single file.\n"
        b"\\end{document}"
    )

    # Gzip compress the .tex content directly (not as a tarball)
    gzipped = gzip.compress(tex_content)

    result = extract_arxiv_text(gzipped)

    assert b"gzipped single file" in result
    assert b"\\documentclass" in result


def test_extract_arxiv_text_gzip_non_latex_fails():
    """Test that gzip fallback fails for non-LaTeX content (BUG-054)."""
    # Create non-LaTeX content
    non_latex_content = b"This is just plain text without any LaTeX commands."

    # Gzip compress it
    gzipped = gzip.compress(non_latex_content)

    with pytest.raises(ValueError, match="Gzip content is not LaTeX"):
        extract_arxiv_text(gzipped)


def test_extract_arxiv_text_invalid_format_raises_tar_error():
    """Test that invalid data raises TarError after gzip fallback fails."""
    # Random bytes that are neither tar nor gzip
    random_bytes = b"not a valid archive format at all"

    with pytest.raises(tarfile.TarError, match="Not valid tar or gzip"):
        extract_arxiv_text(random_bytes)


# Security tests (DEBT-125)


def test_extract_arxiv_text_ignores_path_traversal():
    """Test that path traversal attacks are ignored (security)."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add malicious path traversal file
        evil_content = (
            b"\\documentclass{article}\n\\begin{document}\nEvil\n\\end{document}"
        )
        evil_info = tarfile.TarInfo(name="../../../etc/passwd.tex")
        evil_info.size = len(evil_content)
        tar.addfile(evil_info, io.BytesIO(evil_content))

        # Add safe file
        safe_content = b"\\documentclass{article}\n\\begin{document}\nSafe content.\n\\end{document}"
        safe_info = tarfile.TarInfo(name="paper.tex")
        safe_info.size = len(safe_content)
        tar.addfile(safe_info, io.BytesIO(safe_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should extract safe file, ignore malicious one
    assert b"Safe content" in result
    assert b"Evil" not in result


def test_extract_arxiv_text_ignores_absolute_paths():
    """Test that absolute paths are ignored (security)."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add absolute path file
        abs_content = (
            b"\\documentclass{article}\n\\begin{document}\nAbsolute\n\\end{document}"
        )
        abs_info = tarfile.TarInfo(name="/etc/passwd.tex")
        abs_info.size = len(abs_content)
        tar.addfile(abs_info, io.BytesIO(abs_content))

        # Add safe file
        safe_content = (
            b"\\documentclass{article}\n\\begin{document}\nSafe.\n\\end{document}"
        )
        safe_info = tarfile.TarInfo(name="main.tex")
        safe_info.size = len(safe_content)
        tar.addfile(safe_info, io.BytesIO(safe_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should extract safe file, ignore absolute path
    assert b"Safe" in result
    assert b"Absolute" not in result


def test_extract_arxiv_text_ignores_symlinks():
    """Test that symlinks are ignored (security)."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Add symlink to /etc/passwd
        symlink_info = tarfile.TarInfo(name="evil.tex")
        symlink_info.type = tarfile.SYMTYPE
        symlink_info.linkname = "/etc/passwd"
        tar.addfile(symlink_info)

        # Add safe file
        safe_content = (
            b"\\documentclass{article}\n\\begin{document}\nReal file.\n\\end{document}"
        )
        safe_info = tarfile.TarInfo(name="paper.tex")
        safe_info.size = len(safe_content)
        tar.addfile(safe_info, io.BytesIO(safe_content))

    tar_buffer.seek(0)
    result = extract_arxiv_text(tar_buffer.read())

    # Should extract safe file, ignore symlink
    assert b"Real file" in result


def test_extract_arxiv_text_only_malicious_files_raises():
    """Test that tarball with only malicious paths raises ValueError."""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        # Only malicious files
        evil_content = (
            b"\\documentclass{article}\n\\begin{document}\nEvil\n\\end{document}"
        )
        evil_info = tarfile.TarInfo(name="../../../tmp/evil.tex")
        evil_info.size = len(evil_content)
        tar.addfile(evil_info, io.BytesIO(evil_content))

    tar_buffer.seek(0)

    with pytest.raises(ValueError, match=r"No \.tex files found"):
        extract_arxiv_text(tar_buffer.read())
