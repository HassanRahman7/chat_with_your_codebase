"""Common parser contract and normalized symbol representation."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tree_sitter import Language, Node, Parser, Tree

from app.services.errors import ParserError


@dataclass(frozen=True)
class Symbol:
    """One normalized syntax-aware symbol."""

    symbol_id: str
    symbol_name: str
    symbol_type: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    source: str
    parent_symbol: str | None = None
    docstring: str | None = None


@dataclass(frozen=True)
class ParseResult:
    tree: Tree
    symbols: list[Symbol] = field(default_factory=list)
    has_error: bool = False


class BaseParser(ABC):
    """Tree-sitter-backed parser shared by language implementations."""

    language: str
    extensions: tuple[str, ...] = ()

    def __init__(self, language_module) -> None:
        self._language_module = language_module
        self._language = Language(language_module.language())

    def parse(self, source: str, *, file_path: str = "") -> ParseResult:
        """Parse source text into a tree and extract normalized symbols."""
        if source.startswith("\ufeff"):
            source = source[1:]
        try:
            source_bytes = source.encode("utf-8")
            tree = Parser(self._language).parse(source_bytes)
        except Exception as exc:  # noqa: BLE001 - tree-sitter faults use fallback
            raise ParserError("Tree-sitter could not parse the source file.") from exc

        root = tree.root_node
        symbols = self.extract_symbols(source, root, file_path=file_path)
        return ParseResult(
            tree=tree,
            symbols=symbols,
            has_error=bool(root.has_error),
        )

    def parse_file(self, file_path: str, source: str) -> ParseResult:
        return self.parse(source, file_path=file_path)

    @abstractmethod
    def extract_symbols(
        self,
        source: str,
        root: Node,
        *,
        file_path: str,
    ) -> list[Symbol]:
        """Extract normalized symbols from a parsed tree."""

    def create_symbol(
        self,
        source: str,
        node: Node,
        *,
        file_path: str,
        symbol_name: str,
        symbol_type: str,
        parent_symbol: str | None = None,
        docstring: str | None = None,
    ) -> Symbol:
        """Build a symbol from a tree-sitter node.

        ``source`` is sliced by node line numbers so the returned text is the
        exact repository source for the symbol's one-based line range.
        """
        text = self.text_of(source, node)
        start_line = node.start_point[0] + 1
        end_line = max(start_line, node.end_point[0] + 1)
        return Symbol(
            symbol_id=_symbol_id(
                file_path,
                symbol_name,
                symbol_type,
                start_line,
                end_line,
                text,
            ),
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            parent_symbol=parent_symbol,
            file_path=file_path,
            language=self.language,
            start_line=start_line,
            end_line=end_line,
            source=text,
            docstring=docstring,
        )

    def iter_children(self, node: Node, types: set[str]):
        for child in node.children:
            if child.type in types:
                yield child

    def first_child(self, node: Node, node_type: str):
        for child in node.children:
            if child.type == node_type:
                return child
        return None

    def text_of(self, source: str, node: Node | None) -> str:
        if node is None:
            return ""
        source_bytes = source.encode("utf-8")
        return source_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )


def slice_lines(source: str, start_line: int, end_line: int) -> str:
    """Return exact source text for a one-based inclusive line range."""
    lines = source.splitlines(keepends=True)
    if not lines:
        return ""
    start_index = max(0, start_line - 1)
    end_index = min(len(lines), end_line)
    return "".join(lines[start_index:end_index]).rstrip("\r\n")


def count_estimated_tokens(text: str) -> int:
    """Conservative token estimate used for Phase 2 chunk-size decisions."""
    if not text:
        return 0
    # English/code averages roughly four characters per token. A cheap,
    # deterministic estimate is sufficient until Phase 3 uses the model
    # tokenizer for final embedding inputs.
    return max(1, (len(text) + 3) // 4)


def _symbol_id(
    file_path: str,
    symbol_name: str,
    symbol_type: str,
    start_line: int,
    end_line: int,
    source: str,
) -> str:
    material = "\n".join(
        [
            file_path,
            symbol_name,
            symbol_type,
            str(start_line),
            str(end_line),
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
