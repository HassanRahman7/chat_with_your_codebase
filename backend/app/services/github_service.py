"""GitHub URL validation and controlled repository cloning.

Only public ``https://github.com/<owner>/<repo>`` URLs are accepted. Repository
content is never executed; cloning uses Git with terminal prompts disabled and
a hard timeout.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.config import settings
from app.services.errors import (
    InvalidGitHubUrlError,
    RepositoryCloneError,
    RepositoryTooLargeError,
)

logger = logging.getLogger(__name__)

_GITHUB_HOSTS = {"github.com", "www.github.com"}
_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    canonical_url: str
    display_name: str


@dataclass(frozen=True)
class CloneResult:
    commit_sha: str
    default_branch: str | None
    local_path: str


def canonicalize_github_url(raw_url: str) -> GitHubRepository:
    """Validate and canonicalize a supported public GitHub repository URL."""
    if not raw_url or len(raw_url) > settings.max_github_url_length:
        raise InvalidGitHubUrlError()

    candidate = raw_url.strip()
    if not candidate or any(ord(character) < 32 for character in candidate):
        raise InvalidGitHubUrlError()

    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise InvalidGitHubUrlError() from exc

    if parsed.scheme.lower() != "https":
        raise InvalidGitHubUrlError()
    if parsed.username or parsed.password:
        raise InvalidGitHubUrlError()
    if parsed.hostname is None or parsed.hostname.lower() not in _GITHUB_HOSTS:
        raise InvalidGitHubUrlError()
    if parsed.port is not None:
        raise InvalidGitHubUrlError()
    if parsed.query or parsed.fragment:
        raise InvalidGitHubUrlError()

    path = parsed.path.strip("/")
    segments = path.split("/")
    if len(segments) != 2:
        raise InvalidGitHubUrlError()

    owner, name = segments
    if name.lower().endswith(".git"):
        name = name[:-4]

    if not owner or not name:
        raise InvalidGitHubUrlError()
    if owner in {".", ".."} or name in {".", ".."}:
        raise InvalidGitHubUrlError()
    if not _OWNER_PATTERN.fullmatch(owner) or owner.endswith("-"):
        raise InvalidGitHubUrlError()
    if not _REPOSITORY_PATTERN.fullmatch(name):
        raise InvalidGitHubUrlError()

    canonical_owner = owner.lower()
    canonical_name = name.lower()
    canonical_url = f"https://github.com/{canonical_owner}/{canonical_name}"

    return GitHubRepository(
        owner=canonical_owner,
        name=canonical_name,
        canonical_url=canonical_url,
        display_name=f"{canonical_owner}/{canonical_name}",
    )


def repository_clone_path(repository_id: object) -> Path:
    """Return the controlled clone destination for a repository UUID."""
    return settings.repository_storage_directory / str(repository_id)


def clone_repository(
    canonical_url: str,
    destination: Path,
    *,
    timeout_seconds: int | None = None,
) -> CloneResult:
    """Shallow-clone a validated public repository into controlled storage.

    The clone is performed with a bounded subprocess and no repository scripts
    or Git hooks are executed. On failure the partial clone is removed.
    """
    root = settings.repository_storage_directory.resolve()
    target = destination.resolve()
    if target == root or not target.is_relative_to(root):
        raise RepositoryCloneError("Unsafe repository clone destination.")

    if target.exists():
        _remove_directory(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"

    command = [
        "git",
        "clone",
        "--depth",
        "1",
        "--no-tags",
        "--single-branch",
        "--",
        canonical_url,
        str(target),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds or settings.clone_timeout_seconds,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _remove_directory(target)
        raise RepositoryCloneError(
            "Cloning the repository timed out.",
            code="repository_clone_timeout",
        ) from exc
    except FileNotFoundError as exc:
        raise RepositoryCloneError(
            "Git is not installed or is not available on PATH.",
            code="git_unavailable",
        ) from exc

    if completed.returncode != 0:
        logger.warning(
            "git clone failed for %s (exit=%s): %s",
            canonical_url,
            completed.returncode,
            (completed.stderr or "").strip()[:500],
        )
        _remove_directory(target)
        raise RepositoryCloneError("Git could not clone the repository.")

    size_bytes = _directory_size(target)
    if size_bytes > settings.max_repository_size_mb * 1024 * 1024:
        _remove_directory(target)
        raise RepositoryTooLargeError(
            "The repository exceeds the configured size limit."
        )

    try:
        commit_sha = _git_output(target, ["rev-parse", "HEAD"]).strip()
        default_branch = _git_output(target, ["branch", "--show-current"]).strip()
        if not default_branch:
            default_branch = _git_output(
                target, ["rev-parse", "--abbrev-ref", "HEAD"]
            ).strip()
    except RepositoryCloneError:
        _remove_directory(target)
        raise

    if not commit_sha:
        _remove_directory(target)
        raise RepositoryCloneError("The cloned repository has no commit.")

    return CloneResult(
        commit_sha=commit_sha,
        default_branch=default_branch or None,
        local_path=str(target),
    )


def remove_repository_directory(path: str | Path) -> None:
    """Safely remove a repository clone inside controlled storage."""
    root = settings.repository_storage_directory.resolve()
    target = Path(path).resolve()
    if target == root or not target.is_relative_to(root):
        raise RepositoryCloneError("Unsafe repository cleanup path.")
    _remove_directory(target)


def _git_output(repository: Path, arguments: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepositoryCloneError("Git metadata could not be read.") from exc

    if completed.returncode != 0:
        raise RepositoryCloneError("Git metadata could not be read.")
    return completed.stdout


def _directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _handle_remove_readonly(func, path, exc_info):
    """On Windows, .git packs can be read-only; chmod and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _remove_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onerror=_handle_remove_readonly)
