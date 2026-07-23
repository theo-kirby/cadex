# SPDX-License-Identifier: LGPL-2.1-or-later

"""Guardrail: every ``.connect(_handler)`` in the GUI resolves to a defined
module-level function.

CadexGui imports FreeCAD/PySide at module scope, so it cannot be imported in
the headless test environment. This test parses the source with ``ast`` instead
and asserts that any signal connected to a bare underscore-prefixed name has a
matching top-level ``def``. A dangling connection (e.g. a handler removed during
a refactor but still referenced by one panel builder) raises ``NameError`` only
when that widget is built at runtime, which previously slipped through into
experimental mode and crashed GUI bootstrap.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

CADEX_DIR = Path(__file__).resolve().parent.parent
GUI_SOURCE = CADEX_DIR / "CadexGui.py"


def _module_function_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            # Module-level ``_handler = something`` also counts as defined.
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _connect_handler_names(tree: ast.Module) -> list[tuple[str, int]]:
    """All ``<signal>.connect(<bare Name>)`` targets, with line numbers."""
    handlers: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "connect"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Name):
            handlers.append((first.id, node.lineno))
    return handlers


@pytest.fixture(scope="module")
def gui_tree() -> ast.Module:
    return ast.parse(GUI_SOURCE.read_text(encoding="utf-8"), filename=str(GUI_SOURCE))


def test_all_connect_handlers_are_defined(gui_tree: ast.Module) -> None:
    defined = _module_function_names(gui_tree)
    dangling = [
        (name, lineno)
        for name, lineno in _connect_handler_names(gui_tree)
        if name.startswith("_") and name not in defined
    ]
    assert not dangling, "signal .connect() targets with no module-level definition: " + ", ".join(
        f"{name} (line {lineno})" for name, lineno in dangling
    )


def test_modeling_engine_selectors_use_the_current_handler(gui_tree: ast.Module) -> None:
    # The merge renamed the PartDesign engine handler; both the full and experimental
    # panel builders must connect to the surviving _modeling_engine_changed.
    handlers = {name for name, _ in _connect_handler_names(gui_tree)}
    assert "_modeling_engine_changed" in handlers
    assert "_partdesign_engine_changed" not in handlers
