"""Parser service: choose a language parser and return normalized symbols."""

from __future__ import annotations

from pathlib import Path

from app.parsers.base_parser import ParseResult
from app.parsers.parser_registry import get_parser_for_extension
from app.services.errors import ParserError


def parse_source(
    *,
    extension: str,
    file_path: str,
    source: str,
) -> ParseResult | None:
    """Parse source text, returning ``None`` for unsupported extensions."""
    parser = get_parser_for_extension(extension)
    if parser is None:
        return None
    return parser.parse_file(file_path, source)


def parse_file(path: str | Path, source: str) -> ParseResult | None:
    """Parse source text using the path's extension."""
    path = Path(path)
    return parse_source(
        extension=path.suffix.lower(),
        file_path=path.as_posix(),
        source=source,
    )
