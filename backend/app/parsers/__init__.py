"""Tree-sitter parser package."""

from app.parsers.base_parser import BaseParser, ParseResult, Symbol
from app.parsers.javascript_parser import JavaScriptParser
from app.parsers.parser_registry import (
    get_parser_for_extension,
    is_supported_extension,
    language_for_extension,
    supported_extensions,
)
from app.parsers.python_parser import PythonParser

__all__ = [
    "BaseParser",
    "JavaScriptParser",
    "ParseResult",
    "PythonParser",
    "Symbol",
    "get_parser_for_extension",
    "is_supported_extension",
    "language_for_extension",
    "supported_extensions",
]
