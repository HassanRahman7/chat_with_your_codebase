"""Deterministic, security-aware repository file scanning.

The scanner produces an inventory of eligible Python/JavaScript files. It
never executes repository code, never follows symlinks outside the clone, and
applies mandatory exclusions before any optional ignore-file behavior.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.parsers.parser_registry import language_for_extension
from app.services.errors import (
    NoSupportedSourceFilesError,
    RepositoryTooManyFilesError,
)

logger = logging.getLogger(__name__)

EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".cache",
    "coverage",
    "vendor",
    ".terraform",
}

LOCK_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "bun.lock",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
}

SECRET_FILE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "credentials.json",
    "service-account.json",
}

SECRET_FILE_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
    ".der",
    ".jks",
    ".keystore",
}

IGNORED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".o",
    ".obj",
    ".a",
    ".lib",
    ".jar",
    ".war",
    ".ear",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}


@dataclass(frozen=True)
class SourceFile:
    relative_path: str
    language: str
    extension: str
    size_bytes: int
    content_hash: str
    absolute_path: Path


@dataclass(frozen=True)
class SkippedFile:
    relative_path: str
    reason: str


@dataclass
class ScanResult:
    files: list[SourceFile] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)


def scan_repository(
    repository_root: str | Path,
    *,
    max_files: int | None = None,
    max_file_size_mb: int | None = None,
    max_file_size_bytes: int | None = None,
    use_git_ls_files: bool = True,
) -> ScanResult:
    """Return a deterministic inventory of eligible source files.

    ``use_git_ls_files`` is disabled by tests and by fallback scanning. Real
    clones contain a Git checkout, so tracked-file enumeration is the normal
    path and automatically excludes ignored/untracked build output.
    """
    root = Path(repository_root).resolve()
    if not root.is_dir():
        logger.warning("Repository root does not exist: %s", repository_root)
        return ScanResult()

    max_files = settings.max_repository_files if max_files is None else max_files
    if max_file_size_bytes is None:
        max_file_size_mb = (
            settings.max_file_size_mb if max_file_size_mb is None else max_file_size_mb
        )
        max_file_size_bytes = max_file_size_mb * 1024 * 1024

    if use_git_ls_files:
        candidates = _list_candidate_files(root)
        if candidates is None:
            candidates = _walk_files(root)
    else:
        candidates = _walk_files(root)

    files: list[SourceFile] = []
    skipped: list[SkippedFile] = []

    for relative_path in sorted(candidates):
        result = _inspect_file(
            root,
            relative_path,
            max_file_size_bytes=max_file_size_bytes,
        )
        if isinstance(result, SourceFile):
            files.append(result)
        else:
            skipped.append(result)

    files.sort(key=lambda item: item.relative_path)
    if len(files) > max_files:
        raise RepositoryTooManyFilesError(
            "The repository contains more supported source files than the "
            "configured limit."
        )
    if not files:
        raise NoSupportedSourceFilesError(
            "The repository contains no supported Python or JavaScript source "
            "files."
        )
    return ScanResult(files=files, skipped=skipped)


def _list_candidate_files(root: Path) -> list[str] | None:
    """Return tracked files from Git, or ``None`` to request a fallback walk."""
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return [item for item in completed.stdout.split("\0") if item]


def _walk_files(root: Path) -> list[str]:
    gitignore = _load_gitignore(root)
    candidates: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        relative_path = path.relative_to(root).as_posix()
        if _is_ignored_by_gitignore(relative_path, gitignore):
            continue
        candidates.append(relative_path)
    return candidates


def _inspect_file(
    root: Path,
    relative_path: str,
    *,
    max_file_size_bytes: int,
) -> SourceFile | SkippedFile:
    if not relative_path or relative_path.startswith(("/", "\\")):
        return SkippedFile(relative_path, "unsafe_path")

    absolute_path = (root / relative_path).resolve()
    root = root.resolve()
    if absolute_path != root and not absolute_path.is_relative_to(root):
        return SkippedFile(relative_path, "path_outside_repository")
    if not absolute_path.is_file():
        return SkippedFile(relative_path, "not_a_file")
    if absolute_path.is_symlink():
        return SkippedFile(relative_path, "symlink_skipped")

    parts = Path(relative_path).parts
    if any(part in EXCLUDED_DIR_NAMES for part in parts[:-1]):
        return SkippedFile(relative_path, "excluded_directory")

    filename = Path(relative_path).name
    extension = Path(relative_path).suffix.lower()
    if filename in LOCK_FILE_NAMES:
        return SkippedFile(relative_path, "lock_file")
    if filename in SECRET_FILE_NAMES or filename.startswith(".env."):
        return SkippedFile(relative_path, "secret_file")
    if extension in SECRET_FILE_SUFFIXES:
        return SkippedFile(relative_path, "secret_file")
    if extension in IGNORED_FILE_SUFFIXES:
        return SkippedFile(relative_path, "binary_or_generated_extension")
    if filename.endswith((".min.js", ".min.jsx", ".bundle.js", ".chunk.js", ".map")):
        return SkippedFile(relative_path, "minified_or_compiled_output")

    language = language_for_extension(extension)
    if language is None:
        return SkippedFile(relative_path, "unsupported_language")

    try:
        size_bytes = absolute_path.stat().st_size
    except OSError:
        return SkippedFile(relative_path, "unreadable_file")
    if size_bytes > max_file_size_bytes:
        return SkippedFile(relative_path, "file_too_large")

    try:
        content = absolute_path.read_bytes()
    except OSError:
        return SkippedFile(relative_path, "unreadable_file")

    if b"\x00" in content:
        return SkippedFile(relative_path, "binary_content")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return SkippedFile(relative_path, "binary_or_non_utf8_content")

    return SourceFile(
        relative_path=relative_path,
        language=language,
        extension=extension,
        size_bytes=size_bytes,
        content_hash=hashlib.sha256(content).hexdigest(),
        absolute_path=absolute_path,
    )


def _load_gitignore(root: Path) -> list[tuple[str, bool]]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: list[tuple[str, bool]] = []
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        patterns.append((line[1:] if negated else line, negated))
    return patterns


def _is_ignored_by_gitignore(
    relative_path: str,
    patterns: list[tuple[str, bool]],
) -> bool:
    ignored = False
    for raw_pattern, negated in patterns:
        pattern = raw_pattern.strip()
        if not pattern:
            continue
        pattern = pattern.removeprefix("/")
        is_directory = pattern.endswith("/")
        pattern = pattern.rstrip("/")
        matched = False
        if is_directory:
            matched = any(
                part == pattern or fnmatch.fnmatch(part, pattern)
                for part in Path(relative_path).parts[:-1]
            )
        elif "/" in pattern:
            matched = fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(
                relative_path, f"*/{pattern}"
            )
        else:
            matched = any(
                fnmatch.fnmatch(part, pattern)
                for part in Path(relative_path).parts
            )
        if matched:
            ignored = not negated
    return ignored
