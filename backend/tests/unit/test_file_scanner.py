"""File scanner and exclusion tests."""

from __future__ import annotations

import hashlib

import pytest

from app.services.errors import (
    NoSupportedSourceFilesError,
    RepositoryTooManyFilesError,
)
from app.services.file_scanner_service import scan_repository


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def test_scanner_builds_deterministic_inventory(tmp_path) -> None:
    _write(tmp_path / "src" / "main.py", "def main():\n    return 1\n")
    _write(tmp_path / "src" / "app.js", "export function app() { return 1; }\n")
    _write(tmp_path / "src" / "view.jsx", "export const v = <div />;\n")
    _write(tmp_path / "README.md", "# docs\n")

    result = scan_repository(tmp_path, use_git_ls_files=False)

    assert [item.relative_path for item in result.files] == [
        "src/app.js",
        "src/main.py",
        "src/view.jsx",
    ]
    by_path = {item.relative_path: item for item in result.files}
    assert by_path["src/main.py"].language == "python"
    assert by_path["src/view.jsx"].language == "javascript"
    assert by_path["src/main.py"].content_hash == hashlib.sha256(
        b"def main():\n    return 1\n"
    ).hexdigest()
    assert (tmp_path / "README.md").as_posix() not in [
        item.relative_path for item in result.files
    ]


def test_scanner_excludes_mandatory_directories_lockfiles_and_secrets(tmp_path) -> None:
    _write(tmp_path / "src" / "main.py", "def main():\n    return 1\n")
    _write(tmp_path / "node_modules" / "pkg" / "index.js", "module.exports = 1;\n")
    _write(tmp_path / "dist" / "bundle.js", "console.log(1);\n")
    _write(tmp_path / "__pycache__" / "cached.py", "value = 1\n")
    _write(tmp_path / "package-lock.json", "{}\n")
    _write(tmp_path / ". env.pem", "not a real key\n")
    _write(tmp_path / "private.pem", "not a real key\n")
    _write(tmp_path / ".env", "SECRET=1\n")
    _write(tmp_path / "src" / "app.min.js", "console.log('minified');\n")

    result = scan_repository(tmp_path, use_git_ls_files=False)
    reasons = {item.relative_path: item.reason for item in result.skipped}

    assert [item.relative_path for item in result.files] == ["src/main.py"]
    assert reasons["node_modules/pkg/index.js"] == "excluded_directory"
    assert reasons["dist/bundle.js"] == "excluded_directory"
    assert reasons["__pycache__/cached.py"] == "excluded_directory"
    assert reasons["package-lock.json"] == "lock_file"
    assert reasons["private.pem"] == "secret_file"
    assert reasons[".env"] == "secret_file"
    assert reasons["src/app.min.js"] == "minified_or_compiled_output"


def test_scanner_skips_binary_and_non_utf8_content(tmp_path) -> None:
    _write(tmp_path / "src" / "ok.py", "value = 1\n")
    (tmp_path / "src" / "bad.py").write_bytes(b"value = 1\x00\n")
    (tmp_path / "src" / "nonutf8.py").write_bytes(b"value = \xff\n")

    result = scan_repository(tmp_path, use_git_ls_files=False)
    reasons = {item.relative_path: item.reason for item in result.skipped}

    assert [item.relative_path for item in result.files] == ["src/ok.py"]
    assert reasons["src/bad.py"] == "binary_content"
    assert reasons["src/nonutf8.py"] == "binary_or_non_utf8_content"


def test_scanner_respects_fallback_gitignore(tmp_path) -> None:
    _write(tmp_path / ".gitignore", "ignored.py\nbuild_output/\n")
    _write(tmp_path / "ignored.py", "value = 1\n")
    _write(tmp_path / "build_output" / "generated.py", "value = 2\n")
    _write(tmp_path / "kept.py", "def kept():\n    return 3\n")

    result = scan_repository(tmp_path, use_git_ls_files=False)

    assert [item.relative_path for item in result.files] == ["kept.py"]


def test_scanner_enforces_file_size_limit_with_reason(tmp_path) -> None:
    _write(tmp_path / "big.py", "value = 'x' * 100\n")
    _write(tmp_path / "small.py", "value = 1\n")

    result = scan_repository(
        tmp_path,
        max_file_size_bytes=10,
        use_git_ls_files=False,
    )

    assert [item.relative_path for item in result.files] == ["small.py"]
    assert result.skipped[0].relative_path == "big.py"
    assert result.skipped[0].reason == "file_too_large"


def test_scanner_raises_when_file_count_limit_is_exceeded(tmp_path) -> None:
    _write(tmp_path / "one.py", "def one():\n    return 1\n")
    _write(tmp_path / "two.py", "def two():\n    return 2\n")

    with pytest.raises(RepositoryTooManyFilesError):
        scan_repository(tmp_path, max_files=1, use_git_ls_files=False)


def test_scanner_raises_when_no_supported_files_remain(tmp_path) -> None:
    _write(tmp_path / "README.md", "# no code\n")

    with pytest.raises(NoSupportedSourceFilesError):
        scan_repository(tmp_path, use_git_ls_files=False)
