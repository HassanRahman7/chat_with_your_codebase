"""Python parser implemented with the tree-sitter Python grammar."""

from __future__ import annotations

import tree_sitter_python as _language_module
from tree_sitter import Node

from app.parsers.base_parser import BaseParser


class PythonParser(BaseParser):
    language = "python"
    extensions = (".py",)

    def __init__(self) -> None:
        super().__init__(_language_module)

    def extract_symbols(
        self,
        source: str,
        root: Node,
        *,
        file_path: str,
    ) -> list:
        if root.type != "module":
            return []

        symbols = []
        for node in root.children:
            if node.type in {"import_statement", "import_from_statement"}:
                symbol_name = self.text_of(source, node).split(" import ", 1)[0]
                symbol_name = symbol_name.replace("from ", "", 1).strip()
                symbols.append(
                    self.create_symbol(
                        source,
                        node,
                        file_path=file_path,
                        symbol_name=symbol_name or "import",
                        symbol_type="import",
                    )
                )
                continue
            self._extract_statement(source, node, symbols, file_path, parent=None)
        return sorted(symbols, key=lambda item: (item.start_line, item.end_line))

    def _extract_statement(self, source, node, symbols, file_path, *, parent):
        effective = node
        if node.type == "decorated_definition":
            # Decorators are part of the documented definition; slice the
            # whole decorated node so the chunk includes them.
            effective = node

        if effective.type == "class_definition":
            class_name = self._child_text(source, effective, "identifier")
            symbols.append(
                self.create_symbol(
                    source,
                    effective,
                    file_path=file_path,
                    symbol_name=class_name or "class",
                    symbol_type="class",
                    parent_symbol=parent,
                    docstring=self._docstring(source, effective),
                )
            )

            block = self.first_child(effective, "block")
            if block is not None:
                for child in block.children:
                    if child.type in {
                        "function_definition",
                        "decorated_definition",
                    }:
                        self._extract_function(
                            source,
                            child,
                            symbols,
                            file_path,
                            parent=class_name or None,
                            is_method=True,
                        )
                    elif child.type in {
                        "expression_statement",
                        "assignment",
                        "type_alias_statement",
                    }:
                        self._extract_declaration(
                            source,
                            child,
                            symbols,
                            file_path,
                            parent=class_name or None,
                        )
            return

        if effective.type == "function_definition":
            self._extract_function(
                source,
                effective,
                symbols,
                file_path,
                parent=parent,
                is_method=False,
            )
            return

        if effective.type in {
            "expression_statement",
            "assignment",
            "type_alias_statement",
        }:
            self._extract_declaration(
                source, effective, symbols, file_path, parent=parent
            )

    def _extract_function(self, source, node, symbols, file_path, *, parent, is_method):
        name_node = self.first_child(node, "identifier")
        name = self.text_of(source, name_node) or "anonymous"
        symbols.append(
            self.create_symbol(
                source,
                node,
                file_path=file_path,
                symbol_name=name,
                symbol_type="method" if is_method else "function",
                parent_symbol=parent,
                docstring=self._docstring(source, node),
            )
        )

        block = self.first_child(node, "block")
        if block is None:
            return
        for child in block.children:
            if child.type in {"function_definition", "decorated_definition"}:
                self._extract_function(
                    source,
                    child,
                    symbols,
                    file_path,
                    parent=name,
                    is_method=False,
                )
            elif child.type == "class_definition":
                self._extract_statement(source, child, symbols, file_path, parent=name)

    def _extract_declaration(self, source, node, symbols, file_path, *, parent):
        assignment = node
        if node.type == "expression_statement":
            assignment = self.first_child(node, "assignment") or node
        left = self.first_child(assignment, "identifier")
        if left is None and assignment.children:
            left = assignment.children[0]
        name = self.text_of(source, left)
        if not name or name in {"=", ":", ","}:
            return
        symbols.append(
            self.create_symbol(
                source,
                node,
                file_path=file_path,
                symbol_name=name,
                symbol_type="assignment",
                parent_symbol=parent,
            )
        )

    def _child_text(self, source, node, node_type):
        child = self.first_child(node, node_type)
        return self.text_of(source, child) if child is not None else ""

    def _docstring(self, source, node):
        block = self.first_child(node, "block")
        if block is None or not block.children:
            return None
        first = block.children[0]
        statement = first
        if first.type == "expression_statement":
            statement = self.first_child(first, "string") or first
        if statement.type != "string":
            return None
        value = self.text_of(source, statement).strip()
        for delimiter in ('"""', "'''", '"', "'"):
            if value.startswith(delimiter) and value.endswith(delimiter) and len(value) >= len(delimiter) * 2:
                return value[len(delimiter) : -len(delimiter)].strip() or None
        return value or None
