"""File tree and source content services.

Resolves repositories, scans the controlled clone for eligible files, and
serves source content only through authorized backend endpoints. Absolute
server paths never reach the client.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID
from app.database.models import Repository
from app.database.session import SessionLocal
from app.services.errors import RepositoryNotFoundError
from app.services.file_scanner_service import SourceFile, scan_repository

logger = logging.getLogger(__name__)


def _build_tree(files: list[SourceFile]) -> list[dict[str, Any]]:
    """Build a nested directory tree from a flat list of source files."""
    root: dict[str, Any] = {}

    for source_file in files:
        parts = Path(source_file.relative_path).parts
        node = root
        for index, part in enumerate(parts):
            is_last = index == len(parts) - 1
            if part not in node:
                if is_last:
                    node[part] = {
                        "name": part,
                        "type": "file",
                        "path": source_file.relative_path,
                        "language": source_file.language,
                        "children": None,
                    }
                else:
                    node[part] = {
                        "name": part,
                        "type": "directory",
                        "path": str(Path(*parts[: index + 1])),
                        "children": {},
                    }
            if is_last:
                break
            node = node[part]["children"]

    def sort_node(children_dict: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for name in sorted(children_dict.keys()):
            item = children_dict[name]
            if item["type"] == "directory":
                item["children"] = sort_node(item["children"])
            items.append(item)
        return items

    return sort_node(root)


def get_file_tree(
    repository_id: UUID,
) -> tuple[Repository, list[dict[str, Any]]]:
    """Return the repository and its nested file tree."""
    db = SessionLocal()
    try:
        repository = db.get(Repository, repository_id)
        if repository is None:
            raise RepositoryNotFoundError()

        local_path = repository.local_path
        if not local_path:
            return repository, []

        try:
            scan_result = scan_repository(
                local_path,
                use_git_ls_files=False,
            )
        except Exception:  # noqa: BLE001 - no files is not an error for browsing
            logger.warning(
                "Could not scan repository id=%s for file tree", repository_id
            )
            return repository, []

        tree = _build_tree(scan_result.files)
        return repository, tree
    finally:
        db.close()


def get_file_content(
    repository_id: UUID,
    relative_path: str,
) -> tuple[Repository, str, str, int, str]:
    """Return repository, content, language, size, and commit SHA for a file.

    The path is resolved against the repository clone and verified to be
    inside the repository root before reading.
    """
    db = SessionLocal()
    try:
        repository = db.get(Repository, repository_id)
        if repository is None:
            raise RepositoryNotFoundError()

        local_path = repository.local_path
        if not local_path:
            raise RepositoryNotFoundError(
                "This repository has no local clone available."
            )

        root = Path(local_path).resolve()
        target = (root / relative_path).resolve()

        if target == root or not target.is_relative_to(root):
            from app.services.errors import RepositoryConflictError

            raise RepositoryConflictError("Unsafe file path.")

        if not target.is_file():
            raise RepositoryNotFoundError("File not found.")

        content = target.read_text(encoding="utf-8", errors="replace")
        size_bytes = target.stat().st_size

        # Determine language from extension using the scanner's registry.
        from app.services.file_scanner_service import language_for_extension

        language = language_for_extension(target.suffix.lower()) or "text"

        return (
            repository,
            content,
            language,
            size_bytes,
            str(repository.active_commit_sha or ""),
        )
    finally:
        db.close()
