"""Syntax-aware code chunking."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.config import settings
from app.parsers.base_parser import Symbol, count_estimated_tokens, slice_lines
from app.parsers.parser_registry import get_parser_for_extension
from app.services.errors import ParserError
from app.services.file_scanner_service import SourceFile

_CHUNK_NAMESPACE = uuid.UUID("9c0c845a-9c9a-4f43-a361-9f7a2675a1b8")


@dataclass(frozen=True)
class CodeChunk:
    chunk_id: str
    repository_id: UUID
    commit_sha: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None
    parent_symbol: str | None
    start_line: int
    end_line: int
    content: str
    content_hash: str
    chunk_strategy: str
    complete: bool
    partial: bool
    parent_context: str | None = None
    part_index: int | None = None
    part_count: int | None = None


class CodeChunker:
    """Create deterministic chunks from normalized parser symbols."""

    def __init__(
        self,
        *,
        max_chars: int | None = None,
        max_tokens: int | None = None,
        overlap_lines: int | None = None,
    ) -> None:
        self.max_chars = settings.chunk_max_chars if max_chars is None else max_chars
        self.max_tokens = (
            settings.chunk_max_tokens if max_tokens is None else max_tokens
        )
        self.overlap_lines = (
            settings.chunk_overlap_lines
            if overlap_lines is None
            else overlap_lines
        )

    def process_source_file(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        source_file: SourceFile,
    ) -> list[CodeChunk]:
        source = source_file.absolute_path.read_text(
            encoding="utf-8", errors="strict"
        )
        return self.process_content(
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=source_file.relative_path,
            extension=source_file.extension,
            language=source_file.language,
            source=source,
        )

    def process_content(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        extension: str,
        language: str,
        source: str,
    ) -> list[CodeChunk]:
        parser = get_parser_for_extension(extension)
        if parser is None:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=source,
                symbol_name=None,
                parent_symbol=None,
            )

        try:
            parse_result = parser.parse_file(file_path, source)
        except ParserError:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=source,
                symbol_name=None,
                parent_symbol=None,
            )

        if parse_result.has_error:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=source,
                symbol_name=None,
                parent_symbol=None,
            )

        return self.chunk_symbols(
            parse_result=parse_result,
            source=source,
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=file_path,
            language=language,
        )

    def chunk_symbols(
        self,
        *,
        parse_result,
        source: str,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
    ) -> list[CodeChunk]:
        symbols = [
            symbol
            for symbol in parse_result.symbols
            if symbol.symbol_type in {"function", "method", "class"}
        ]
        if not symbols:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=source,
                symbol_name=None,
                parent_symbol=None,
            )

        chunks: list[CodeChunk] = []
        for symbol in symbols:
            if self._has_parent_symbol(symbol, symbols):
                continue
            chunks.extend(
                self._chunk_symbol(
                    symbol,
                    symbols=symbols,
                    parse_result=parse_result,
                    source=source,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                )
            )
        return _deduplicate(chunks)

    def _chunk_symbol(
        self,
        symbol: Symbol,
        *,
        symbols: list[Symbol],
        parse_result,
        source: str,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
    ) -> list[CodeChunk]:
        if not self._is_too_large(symbol.source):
            parent_context = _parent_context(symbol)
            return [
                self._make_chunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                    chunk_type=symbol.symbol_type,
                    symbol_name=symbol.symbol_name,
                    parent_symbol=symbol.parent_symbol,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=symbol.source,
                    chunk_strategy="syntax",
                    complete=True,
                    partial=False,
                    parent_context=parent_context,
                )
            ]

        if symbol.symbol_type == "class":
            return self._split_class(
                symbol,
                symbols=symbols,
                parse_result=parse_result,
                source=source,
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
            )

        return self._split_function(
            symbol,
            symbols=symbols,
            parse_result=parse_result,
            source=source,
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=file_path,
            language=language,
        )

    def _split_class(
        self,
        symbol: Symbol,
        *,
        symbols: list[Symbol],
        parse_result,
        source: str,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
    ) -> list[CodeChunk]:
        children = self._children(symbol, symbols)
        if not children:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=symbol.source,
                symbol_name=symbol.symbol_name,
                parent_symbol=symbol.parent_symbol,
                chunk_type="class",
                start_line=symbol.start_line,
                strategy="syntax_split",
            )

        chunks: list[CodeChunk] = []
        first_child_line = min(child.start_line for child in children)
        preamble_end = max(symbol.start_line, first_child_line - 1)
        preamble = slice_lines(source, symbol.start_line, preamble_end)
        if preamble.strip():
            chunks.append(
                self._make_chunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                    chunk_type="class",
                    symbol_name=symbol.symbol_name,
                    parent_symbol=symbol.parent_symbol,
                    start_line=symbol.start_line,
                    end_line=preamble_end,
                    content=preamble,
                    chunk_strategy="class_summary",
                    complete=False,
                    partial=True,
                    parent_context=None,
                )
            )

        for child in children:
            chunks.extend(
                self._chunk_symbol(
                    child,
                    symbols=symbols,
                    parse_result=parse_result,
                    source=source,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                )
            )
        return chunks

    def _split_function(
        self,
        symbol: Symbol,
        *,
        symbols: list[Symbol],
        parse_result,
        source: str,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
    ) -> list[CodeChunk]:
        children = self._children(symbol, symbols)
        body_children = self._body_children(parse_result, symbol)
        if not body_children:
            return self._fallback_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                language=language,
                source=symbol.source,
                symbol_name=symbol.symbol_name,
                parent_symbol=symbol.parent_symbol,
                chunk_type=symbol.symbol_type,
                start_line=symbol.start_line,
                strategy="syntax_split",
            )

        statement_chunks: list[tuple[int, int, str]] = []
        chunks: list[CodeChunk] = []
        group_start: int | None = None
        group_end: int | None = None
        group_text = ""

        def flush_group() -> None:
            nonlocal group_start, group_end, group_text
            if group_start is not None and group_end is not None and group_text.strip():
                statement_chunks.append((group_start, group_end, group_text))
            group_start = None
            group_end = None
            group_text = ""

        for node in body_children:
            node_start = node.start_point[0] + 1
            node_end = node.end_point[0] + 1
            child_symbol = self._symbol_at(node_start, node_end, children)
            if child_symbol is not None:
                flush_group()
                chunks.extend(
                    self._chunk_symbol(
                        child_symbol,
                        symbols=symbols,
                        parse_result=parse_result,
                        source=source,
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        language=language,
                    )
                )
                continue

            node_text = slice_lines(source, node_start, node_end)
            if group_start is None:
                group_start = node_start
                group_end = node_end
                group_text = node_text
            elif self._is_too_large(group_text) or self._is_too_large(
                group_text + "\n" + node_text
            ):
                flush_group()
                group_start = node_start
                group_end = node_end
                group_text = node_text
            else:
                group_end = node_end
                group_text = slice_lines(source, group_start, group_end)

        flush_group()

        total_parts = len(statement_chunks)
        for index, (start, end, text) in enumerate(statement_chunks, start=1):
            chunks.append(
                self._make_chunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                    chunk_type=symbol.symbol_type,
                    symbol_name=symbol.symbol_name,
                    parent_symbol=symbol.parent_symbol,
                    start_line=start,
                    end_line=end,
                    content=text,
                    chunk_strategy="syntax_split",
                    complete=False,
                    partial=True,
                    parent_context=_parent_context(symbol),
                    part_index=index,
                    part_count=total_parts,
                )
            )
        return chunks

    def _fallback_chunks(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
        source: str,
        symbol_name: str | None,
        parent_symbol: str | None,
        chunk_type: str = "module",
        start_line: int = 1,
        strategy: str = "fallback",
    ) -> list[CodeChunk]:
        windows = _line_windows(source, self.max_chars, self.overlap_lines)
        if not windows:
            return []
        output: list[CodeChunk] = []
        for index, (relative_start, relative_end, text) in enumerate(
            windows, start=1
        ):
            output.append(
                self._make_chunk(
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    language=language,
                    chunk_type=chunk_type,
                    symbol_name=symbol_name,
                    parent_symbol=parent_symbol,
                    start_line=start_line + relative_start - 1,
                    end_line=start_line + relative_end - 1,
                    content=text,
                    chunk_strategy=strategy,
                    complete=False,
                    partial=True,
                    parent_context=None,
                    part_index=index,
                    part_count=len(windows),
                )
            )
        return output

    def _make_chunk(
        self,
        *,
        repository_id: UUID,
        commit_sha: str,
        file_path: str,
        language: str,
        chunk_type: str,
        symbol_name: str | None,
        parent_symbol: str | None,
        start_line: int,
        end_line: int,
        content: str,
        chunk_strategy: str,
        complete: bool,
        partial: bool,
        parent_context: str | None,
        part_index: int | None = None,
        part_count: int | None = None,
    ) -> CodeChunk:
        content = content.rstrip("\r\n")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        material = "\n".join(
            [
                str(repository_id),
                commit_sha,
                file_path,
                chunk_type,
                symbol_name or "",
                parent_symbol or "",
                str(start_line),
                str(end_line),
                content_hash,
                chunk_strategy,
                str(part_index or ""),
            ]
        )
        return CodeChunk(
            chunk_id=str(uuid.uuid5(_CHUNK_NAMESPACE, material)),
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=file_path,
            language=language,
            chunk_type=chunk_type,
            symbol_name=symbol_name,
            parent_symbol=parent_symbol,
            start_line=start_line,
            end_line=end_line,
            content=content,
            content_hash=content_hash,
            chunk_strategy=chunk_strategy,
            complete=complete,
            partial=partial,
            parent_context=parent_context,
            part_index=part_index,
            part_count=part_count,
        )

    def _is_too_large(self, text: str) -> bool:
        return (
            len(text) > self.max_chars
            or count_estimated_tokens(text) > self.max_tokens
        )

    @staticmethod
    def _children(symbol: Symbol, symbols: list[Symbol]) -> list[Symbol]:
        return [
            child
            for child in symbols
            if child is not symbol
            and child.parent_symbol == symbol.symbol_name
            and child.start_line >= symbol.start_line
            and child.end_line <= symbol.end_line
            and (
                child.start_line != symbol.start_line
                or child.end_line != symbol.end_line
            )
        ]

    @staticmethod
    def _has_parent_symbol(symbol: Symbol, symbols: list[Symbol]) -> bool:
        return any(
            parent is not symbol
            and parent.symbol_name == symbol.parent_symbol
            and symbol.start_line >= parent.start_line
            and symbol.end_line <= parent.end_line
            and (
                symbol.start_line != parent.start_line
                or symbol.end_line != parent.end_line
            )
            for parent in symbols
        )

    @staticmethod
    def _symbol_at(start: int, end: int, symbols: list[Symbol]) -> Symbol | None:
        for symbol in symbols:
            if symbol.start_line == start and symbol.end_line == end:
                return symbol
        return None

    def _body_children(self, parse_result, symbol: Symbol):
        node = self._find_node(parse_result.tree.root_node, symbol)
        if node is None:
            return []
        block = None
        for child in node.children:
            if child.type in {"block", "statement_block"}:
                block = child
                break
        if block is None:
            return []
        return [
            child
            for child in block.children
            if child.type not in {"{", "}", ":", "(", ")"}
        ]

    def _find_node(self, node, symbol: Symbol):
        node_start = node.start_point[0] + 1
        node_end = node.end_point[0] + 1
        if node_start == symbol.start_line and node_end == symbol.end_line:
            return node
        for child in node.children:
            found = self._find_node(child, symbol)
            if found is not None:
                return found
        return None


def _parent_context(symbol: Symbol) -> str | None:
    parent = symbol.parent_symbol
    if not parent:
        return None
    if symbol.symbol_type == "method":
        return f"class {parent}:"
    if symbol.symbol_type == "function":
        return f"def {parent}():"
    return parent


def _deduplicate(chunks: list[CodeChunk]) -> list[CodeChunk]:
    seen: set[tuple] = set()
    output: list[CodeChunk] = []
    for chunk in chunks:
        key = (
            chunk.file_path,
            chunk.start_line,
            chunk.end_line,
            chunk.chunk_type,
            chunk.symbol_name,
            chunk.content_hash,
            chunk.chunk_strategy,
            chunk.complete,
            chunk.partial,
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(chunk)
    return output


def _line_windows(
    source: str,
    max_chars: int,
    overlap_lines: int,
) -> list[tuple[int, int, str]]:
    lines = source.splitlines(keepends=True)
    if not lines:
        return []

    windows: list[tuple[int, int, str]] = []
    index = 0
    while index < len(lines):
        start = index
        characters = 0
        while index < len(lines):
            line = lines[index]
            if index > start and characters + len(line) > max_chars:
                break
            characters += len(line)
            index += 1
            if characters >= max_chars:
                break
        end = max(start + 1, index)
        text = "".join(lines[start:end]).rstrip("\r\n")
        windows.append((start + 1, end, text))
        if index >= len(lines):
            break
        index = max(start + 1, end - max(0, overlap_lines))
    return windows
