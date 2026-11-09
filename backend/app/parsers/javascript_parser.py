"""JavaScript parser implemented with the tree-sitter JavaScript grammar."""

from __future__ import annotations

import tree_sitter_javascript as _language_module
from tree_sitter import Node

from app.parsers.base_parser import BaseParser


class JavaScriptParser(BaseParser):
    language = "javascript"
    extensions = (".js", ".jsx")

    def __init__(self) -> None:
        super().__init__(_language_module)

    def extract_symbols(
        self,
        source: str,
        root: Node,
        *,
        file_path: str,
    ) -> list:
        if root.type != "program":
            return []

        symbols = []
        for node in root.children:
            if node.type == "import_statement":
                symbol_name = self._import_name(source, node)
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
            self._extract_statement(
                source, node, symbols, file_path, parent=None
            )
        return sorted(symbols, key=lambda item: (item.start_line, item.end_line))

    def _extract_statement(self, source, node, symbols, file_path, *, parent):
        if node.type == "export_statement":
            definition = self._exported_definition(node)
            if definition is None:
                return
            self._extract_definition(
                source,
                definition,
                symbols,
                file_path,
                parent=parent,
                symbol_node=node,
            )
            return

        if node.type in {
            "lexical_declaration",
            "variable_declaration",
        }:
            for declarator in self.iter_children(
                node, {"variable_declarator"}
            ):
                self._extract_variable_declarator(
                    source, declarator, symbols, file_path, parent=parent
                )
            return

        if node.type in {
            "function_declaration",
            "generator_function_declaration",
            "class_declaration",
            "class_abstract_declaration",
            "abstract_class_declaration",
        }:
            self._extract_definition(
                source, node, symbols, file_path, parent=parent
            )
            return

        if node.type == "expression_statement":
            assignment = self.first_child(node, "assignment_expression")
            if assignment is not None:
                name_node = assignment.children[0] if assignment.children else None
                name = self.text_of(source, name_node)
                if name:
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

    def _exported_definition(self, node):
        for child in node.children:
            if child.type in {
                "function_declaration",
                "generator_function_declaration",
                "class_declaration",
                "lexical_declaration",
                "variable_declaration",
            }:
                return child
        return None

    def _extract_definition(
        self,
        source,
        node,
        symbols,
        file_path,
        *,
        parent,
        symbol_node=None,
    ):
        symbol_node = symbol_node or node
        if node.type in {
            "function_declaration",
            "generator_function_declaration",
        }:
            name = self._child_text(source, node, "identifier") or "anonymous"
            symbols.append(
                self.create_symbol(
                    source,
                    symbol_node,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type="function",
                    parent_symbol=parent,
                    docstring=self._docstring(source, node),
                )
            )
            self._extract_nested_functions(
                source, node, symbols, file_path, parent=name
            )
            return

        if node.type in {
            "class_declaration",
            "class_abstract_declaration",
            "abstract_class_declaration",
        }:
            class_name = self._child_text(source, node, "identifier") or "class"
            symbols.append(
                self.create_symbol(
                    source,
                    symbol_node,
                    file_path=file_path,
                    symbol_name=class_name,
                    symbol_type="class",
                    parent_symbol=parent,
                )
            )
            class_body = self.first_child(node, "class_body")
            if class_body is not None:
                for child in class_body.children:
                    if child.type == "method_definition":
                        name = self._child_text(
                            source, child, "property_identifier"
                        )
                        symbols.append(
                            self.create_symbol(
                                source,
                                child,
                                file_path=file_path,
                                symbol_name=name or "method",
                                symbol_type="method",
                                parent_symbol=class_name,
                                docstring=self._docstring(source, child),
                            )
                        )
                        self._extract_nested_functions(
                            source, child, symbols, file_path, parent=name or "method"
                        )
                    elif child.type in {
                        "public_field_definition",
                        "field_definition",
                    }:
                        name = self._child_text(
                            source, child, "property_identifier"
                        )
                        if name:
                            symbols.append(
                                self.create_symbol(
                                    source,
                                    child,
                                    file_path=file_path,
                                    symbol_name=name,
                                    symbol_type="assignment",
                                    parent_symbol=class_name,
                                )
                            )
            return

        if node.type in {"lexical_declaration", "variable_declaration"}:
            for declarator in self.iter_children(
                node, {"variable_declarator"}
            ):
                self._extract_variable_declarator(
                    source, declarator, symbols, file_path, parent=parent
                )

    def _extract_variable_declarator(
        self,
        source,
        node,
        symbols,
        file_path,
        *,
        parent,
    ):
        name = self._child_text(source, node, "identifier") or "variable"
        value = None
        for child in node.children:
            if child.type in {
                "arrow_function",
                "function_expression",
                "generator_function",
            }:
                value = child
                break
        if value is not None:
            symbols.append(
                self.create_symbol(
                    source,
                    node,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type="function",
                    parent_symbol=parent,
                    docstring=self._docstring(source, value),
                )
            )
            self._extract_nested_functions(
                source, value, symbols, file_path, parent=name
            )
        else:
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

    def _extract_nested_functions(
        self,
        source,
        node,
        symbols,
        file_path,
        *,
        parent,
    ):
        body = (
            self.first_child(node, "statement_block")
            or self.first_child(node, "block")
        )
        if body is None:
            return
        for child in body.children:
            if child.type in {
                "function_declaration",
                "generator_function_declaration",
            }:
                self._extract_definition(
                    source,
                    child,
                    symbols,
                    file_path,
                    parent=parent,
                )
            elif child.type in {"lexical_declaration", "variable_declaration"}:
                self._extract_definition(
                    source,
                    child,
                    symbols,
                    file_path,
                    parent=parent,
                )
            elif child.type == "expression_statement":
                self._extract_statement(
                    source, child, symbols, file_path, parent=parent
                )

    def _child_text(self, source, node, node_type):
        child = self.first_child(node, node_type)
        return self.text_of(source, child) if child is not None else ""

    def _import_name(self, source, node):
        module = self.first_child(node, "string")
        if module is not None:
            return self.text_of(source, module).strip("'\"")
        return ""

    def _docstring(self, source, node):
        # Locate the body block and return its leading comment text if any.
        stack = [node]
        while stack:
            current = stack.pop(0)
            if current.type in {"statement_block", "block"} and current.children:
                first = current.children[0]
                if first.type == "comment":
                    value = self.text_of(source, first).strip()
                    if value.startswith("//"):
                        return value[2:].strip() or None
                    if value.startswith("/*"):
                        return value.strip("/*").strip() or None
                return None
            stack.extend(current.children)
        return None
