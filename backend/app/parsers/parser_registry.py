"""Parser registry mapping supported extensions to parser classes."""

from __future__ import annotations

from app.parsers.base_parser import BaseParser
from app.parsers.javascript_parser import JavaScriptParser
from app.parsers.python_parser import PythonParser

PARSER_CLASSES: tuple[type[BaseParser], ...] = (
    PythonParser,
    JavaScriptParser,
)

_EXTENSIONS = {
    extension: parser_class
    for parser_class in PARSER_CLASSES
    for extension in parser_class.extensions
}


def get_parser_class(extension: str):
    return _EXTENSIONS.get(extension.lower())


def get_parser_for_extension(extension: str) -> BaseParser | None:
    parser_class = get_parser_class(extension)
    return parser_class() if parser_class is not None else None


def supported_extensions() -> tuple[str, ...]:
    return tuple(sorted(_EXTENSIONS))


def is_supported_extension(extension: str) -> bool:
    return extension.lower() in _EXTENSIONS


def language_for_extension(extension: str) -> str | None:
    parser_class = get_parser_class(extension)
    return parser_class.language if parser_class is not None else None
