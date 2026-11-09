"""Syntax-aware chunking tests."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from app.services.chunking_service import CodeChunker


def _chunker(**overrides):
    settings = {"max_chars": 4000, "max_tokens": 1000, "overlap_lines": 2}
    settings.update(overrides)
    return CodeChunker(**settings)


def _chunks(source: str, *, extension=".py", **overrides):
    return _chunker(**overrides).process_content(
        repository_id=uuid4(),
        commit_sha="abc123",
        file_path="src/example.py",
        extension=extension,
        language="python" if extension == ".py" else "javascript",
        source=source,
    )


def test_small_function_remains_one_complete_chunk() -> None:
    source = "def add(a, b):\n    return a + b\n"
    chunks = _chunks(source)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_type == "function"
    assert chunk.symbol_name == "add"
    assert chunk.start_line == 1
    assert chunk.end_line == 2
    assert chunk.complete is True
    assert chunk.partial is False
    assert chunk.chunk_strategy == "syntax"
    assert chunk.content_hash == hashlib.sha256(chunk.content.encode()).hexdigest()


def test_chunk_ids_are_deterministic_for_same_identity() -> None:
    repository_id = uuid4()
    source = "def add(a, b):\n    return a + b\n"
    chunker = _chunker()
    first = chunker.process_content(
        repository_id=repository_id,
        commit_sha="abc123",
        file_path="src/example.py",
        extension=".py",
        language="python",
        source=source,
    )
    second = chunker.process_content(
        repository_id=repository_id,
        commit_sha="abc123",
        file_path="src/example.py",
        extension=".py",
        language="python",
        source=source,
    )

    assert first[0].chunk_id == second[0].chunk_id

    changed = chunker.process_content(
        repository_id=repository_id,
        commit_sha="def456",
        file_path="src/example.py",
        extension=".py",
        language="python",
        source=source,
    )
    assert changed[0].chunk_id != first[0].chunk_id


def test_method_chunk_preserves_parent_context() -> None:
    source = "class Service:\n    def run(self):\n        return 111111111111111111111111111\n"
    chunks = _chunker(max_chars=60).process_content(
        repository_id=uuid4(),
        commit_sha="abc",
        file_path="src/service.py",
        extension=".py",
        language="python",
        source=source,
    )
    methods = [chunk for chunk in chunks if chunk.symbol_name == "run"]

    assert methods
    assert methods[0].parent_symbol == "Service"
    assert methods[0].parent_context == "class Service:"


def test_oversized_class_uses_summary_and_method_chunks() -> None:
    source = """class Service:
    def first(self):
        return 111111111111111111111111111111
    def second(self):
        return 222222222222222222222222222222
"""
    chunks = _chunks(source, max_chars=70)
    by_name = {}
    for chunk in chunks:
        by_name.setdefault(chunk.symbol_name, []).append(chunk)

    assert by_name["Service"][0].chunk_strategy == "class_summary"
    assert by_name["Service"][0].complete is False
    assert by_name["first"][0].chunk_type == "method"
    assert by_name["first"][0].complete is True
    assert by_name["second"][0].chunk_type == "method"
    assert all(chunk.partial is False for chunk in by_name["first"])


def test_oversized_function_splits_at_statement_boundaries() -> None:
    source = """def calculate():
    alpha = 1
    beta = 2
    gamma = 3
    delta = 4
    epsilon = 5
    return alpha + beta + gamma + delta + epsilon
"""
    chunks = _chunks(source, max_chars=50)
    function_chunks = [chunk for chunk in chunks if chunk.symbol_name == "calculate"]

    assert len(function_chunks) >= 2
    assert all(chunk.complete is False for chunk in function_chunks)
    assert all(chunk.partial is True for chunk in function_chunks)
    assert all(chunk.chunk_strategy == "syntax_split" for chunk in function_chunks)
    assert sorted(chunk.part_index for chunk in function_chunks) == list(
        range(1, len(function_chunks) + 1)
    )
    positions = [
        (chunk.start_line, chunk.end_line) for chunk in function_chunks
    ]
    assert positions == sorted(positions)


def test_parse_failure_uses_marked_fallback_chunks() -> None:
    source = "def broken(:\n    pass\n"
    chunks = _chunks(source, max_chars=40)

    assert chunks
    assert all(chunk.chunk_strategy == "fallback" for chunk in chunks)
    assert all(chunk.complete is False for chunk in chunks)
    assert all(chunk.partial is True for chunk in chunks)
    assert all(chunk.symbol_name is None for chunk in chunks)


def test_file_without_functions_uses_module_fallback() -> None:
    source = "TOKEN = 'x'\nOTHER = 'y'\n"
    chunks = _chunks(source)

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "module"
    assert chunks[0].chunk_strategy == "fallback"
    assert chunks[0].content == "TOKEN = 'x'\nOTHER = 'y'"
