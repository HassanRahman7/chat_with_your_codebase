"""Parser registry and Tree-sitter symbol extraction tests."""

from __future__ import annotations

import pytest

from app.parsers.parser_registry import (
    get_parser_for_extension,
    is_supported_extension,
    language_for_extension,
    supported_extensions,
)
from app.services.parser_service import parse_file


def _symbols(result):
    return {
        (symbol.symbol_type, symbol.symbol_name): symbol
        for symbol in result.symbols
    }


def test_registry_maps_supported_extensions() -> None:
    assert supported_extensions() == (".js", ".jsx", ".py")
    assert language_for_extension(".py") == "python"
    assert language_for_extension(".jsx") == "javascript"
    assert is_supported_extension(".JS") is True
    assert is_supported_extension(".ts") is False
    assert get_parser_for_extension(".ts") is None


def test_python_parser_extracts_classes_methods_and_nested_functions() -> None:
    source = '''"""Module docs."""

import os
from pathlib import Path

TOKEN = "x"


class Service:
    """A service."""

    def authenticate(self, user):
        """Authenticate a user."""
        def verify(password):
            return password == user.password

        return verify("secret")


async def fetch(url):
    await request(url)


def top_level():
    pass
'''

    result = parse_file("src/service.py", source)

    assert result is not None
    assert result.has_error is False
    symbols = _symbols(result)
    assert ("import", "pathlib") in symbols
    assert ("assignment", "TOKEN") in symbols
    assert symbols[("class", "Service")].start_line == 9
    assert symbols[("method", "authenticate")].parent_symbol == "Service"
    assert symbols[("method", "authenticate")].docstring == "Authenticate a user."
    assert symbols[("function", "verify")].parent_symbol == "authenticate"
    assert symbols[("function", "verify")].source.startswith("def verify")
    assert symbols[("function", "fetch")].start_line == 20
    assert symbols[("function", "top_level")].end_line == 25


def test_python_parser_uses_one_based_line_ranges() -> None:
    source = "def first():\n    return 1\n\ndef second():\n    return 2\n"
    result = parse_file("example.py", source)

    assert result is not None
    symbols = _symbols(result)
    assert symbols[("function", "first")].start_line == 1
    assert symbols[("function", "first")].end_line == 2
    assert symbols[("function", "second")].start_line == 4
    assert symbols[("function", "second")].source == "def second():\n    return 2"


def test_javascript_parser_extracts_classes_methods_and_functions() -> None:
    source = '''import { request } from "./client.js";
export const TOKEN = "x";

class Service {
  authenticate(user) {
    return verify(user);
  }
}

function topLevel() {
  return 1;
}

const arrow = (value) => value * 2;

export async function fetchUser(id) {
  await request(id);
}

export const element = <section>{TOKEN}</section>;
'''

    result = parse_file("src/view.jsx", source)

    assert result is not None
    assert result.has_error is False
    symbols = _symbols(result)
    assert ("import", "./client.js") in symbols
    assert symbols[("assignment", "TOKEN")].start_line == 2
    assert symbols[("class", "Service")].symbol_type == "class"
    assert symbols[("method", "authenticate")].parent_symbol == "Service"
    assert symbols[("function", "topLevel")].start_line == 10
    assert symbols[("function", "arrow")].source.startswith("arrow =")
    assert symbols[("function", "fetchUser")].start_line == 16
    assert symbols[("assignment", "element")].symbol_type == "assignment"


def test_unsupported_extension_returns_none() -> None:
    assert parse_file("src/example.ts", "export const value = 1;") is None


def test_invalid_python_source_reports_error() -> None:
    result = parse_file("bad.py", "def broken(:\n    pass\n")

    assert result is not None
    assert result.has_error is True
