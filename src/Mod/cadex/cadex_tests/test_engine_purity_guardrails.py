# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine purity guardrails (Phase 7, ADR-021).

Successor to ``test_engine_shell_split_guardrails.py``. That test pinned a
boundary *inside* one repo — shell modules here, engine modules there. After
Phase 7 there is no shell in this repo at all, so the contract inverts: the
engine's transitive import closure must contain nothing shell-shaped, and it
must equal a list somebody declared on purpose.

The closure is computed by AST walk from the two engine entry points, so it
holds for the packaged payload (which ships modules, not an import graph)
and not merely for whatever the pytest process happened to import.

:data:`KNOWN_RESIDUE` is empty as of C5: the Qt shell is gone, so the
forbidden-import check applies to the whole of ``src/Mod/cadex/**`` and not
merely to the closure. The ledger stays in place because it is the shape a
future exception would have to take -- named, dated, and asserted still
true -- rather than a quiet import.

The op table cross-check is the one that matters most now. With the shell
in another repository, ``docs/INTEGRATION.md`` is the protocol contract two
codebases are written against, and nothing but this test notices when the
document and the code drift apart.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent

#: Everything the engine is: one service and one headless rebuild entry.
ENGINE_ENTRY_POINTS = ("cadexd", "cadex_rebuild")

#: Import roots that must never appear in the engine's closure. Qt and the
#: FreeCAD GUI layer because the engine runs under FreeCADCmd with no GUI
#: built at all (ADR-022); ``tool_impl`` and ``jsonschema`` because both
#: exist only to serve the provider tool surface that dies with the shell.
FORBIDDEN_ROOTS = frozenset(
    {"PySide", "PySide2", "PySide6", "FreeCADGui", "tool_impl", "jsonschema"}
)

#: Qt specifically has never been reachable from the engine and never may be
#: — this half of :data:`FORBIDDEN_ROOTS` admits no residue at any point.
NO_RESIDUE_EVER = frozenset({"PySide", "PySide2", "PySide6"})

#: (module, forbidden root) -> the Phase 7 commit that removes the edge.
KNOWN_RESIDUE: dict[tuple[str, str], str] = {
}

#: The engine, module by module. Not a summary of the closure — the closure
#: is asserted to equal it, so an accidental new engine dependency is a test
#: failure rather than a silent widening of the payload.
DECLARED_ENGINE_MODULES = frozenset(
    {
        # entry points
        "cadexd",
        "cadex_rebuild",
        # protocol + settings
        "CadexdProtocol",
        "CadexEngineSettings",
        # the project script store
        "CadexScriptStore",
        # the xscript pipeline
        "CadexScriptedRuntime",
        "CadexScriptedProcess",
        "CadexScriptedPublication",
        "CadexScriptedDomainPublication",
        "CadexScriptedDomains",
        "CadexScriptedOwnership",
        "CadexModelingSurface",
        "CadexReferenceContracts",
        "CadexTools",
        "CadexDigest",
        # inspection, pins, tessellation
        "CadexInspection",
        "CadexPinResolution",
        "cadex_tessellation",
        # the five domain APIs and the host-side workers they pull in
        "cadex_domain_api",
        "cadex_project_api",
        "cadex_part_api",
        "cadex_part_worker",
        "cadex_partdesign_api",
        "cadex_partdesign_worker",
        "cadex_sketcher_api",
        "cadex_sketcher_worker",
        "cadex_mesh_api",
        "cadex_assembly_api",
    }
)


def _import_roots(path: Path) -> set[str]:
    """Top-level names imported by one module, absolute imports only."""

    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _engine_closure() -> dict[str, set[str]]:
    """In-tree modules reachable from the entry points -> what each imports."""

    in_tree = {path.stem: path for path in MODULE_DIR.glob("*.py")}
    closure: dict[str, set[str]] = {}
    pending = list(ENGINE_ENTRY_POINTS)
    while pending:
        name = pending.pop()
        if name in closure or name not in in_tree:
            continue
        roots = _import_roots(in_tree[name])
        closure[name] = roots
        pending.extend(root for root in roots if root in in_tree)
    return closure


def test_engine_closure_never_reaches_qt() -> None:
    for module, roots in _engine_closure().items():
        leaked = NO_RESIDUE_EVER.intersection(roots)
        assert not leaked, (
            f"{module} imports {sorted(leaked)}; the engine runs under "
            "FreeCADCmd against a GUI-less build (ADR-022)."
        )


def test_engine_closure_carries_no_undeclared_shell_imports() -> None:
    """Whole-tree since C5: there is no shell in this repository to exempt."""

    undeclared: list[str] = []
    for path in sorted(MODULE_DIR.glob("*.py")):
        for root in sorted(FORBIDDEN_ROOTS.intersection(_import_roots(path))):
            if (path.stem, root) not in KNOWN_RESIDUE:
                undeclared.append(f"{path.stem} -> {root}")
    assert not undeclared, (
        f"New shell-shaped imports in the engine closure: {undeclared}. "
        "The engine may not gain Qt, GUI, tool_impl or jsonschema edges; "
        "widening KNOWN_RESIDUE needs an ADR (ADR-021)."
    )


def test_declared_residue_is_still_real() -> None:
    """The ledger may not outlive the edges it excuses."""

    stale = [
        f"{module} -> {root} (was to go in {commit})"
        for (module, root), commit in KNOWN_RESIDUE.items()
        if root not in _import_roots(MODULE_DIR / f"{module}.py")
    ]
    assert not stale, (
        f"KNOWN_RESIDUE excuses edges that no longer exist: {stale}. "
        "Delete those entries — the ledger is what proves the engine is "
        "still converging on purity."
    )


def test_engine_closure_is_the_declared_module_list() -> None:
    closure = set(_engine_closure())
    assert closure == DECLARED_ENGINE_MODULES, (
        "The engine's module closure drifted from its declaration.\n"
        f"  gained: {sorted(closure - DECLARED_ENGINE_MODULES)}\n"
        f"  lost:   {sorted(DECLARED_ENGINE_MODULES - closure)}\n"
        "This list is the packaged payload's contents (ADR-023): update it "
        "deliberately, in the commit that changes the engine's shape."
    )


def test_the_conversation_store_left_the_engine() -> None:
    """History lives in the .blend now (ADR-020, decision 4)."""

    assert "CadexProject" not in _engine_closure(), (
        "CadexProject carries the conversation store; the engine reaches "
        "THE project script through CadexScriptStore only."
    )


def _documented_ops() -> set[str]:
    """Ops named in the protocol table of ``docs/INTEGRATION.md``.

    The table's rows begin ``| `op` |`` or ``| `a` / `b` |``; op names are
    the backticked cells in the first column.
    """

    doc = (MODULE_DIR.parents[2] / "docs" / "INTEGRATION.md").read_text(
        encoding="utf-8")
    ops: set[str] = set()
    for line in doc.splitlines():
        if not line.startswith("| `"):
            continue
        first_cell = line.split("|")[1]
        ops.update(re.findall(r"`([a-z_]+)`", first_cell))
    return ops


def test_the_protocol_document_matches_the_op_table() -> None:
    """docs/INTEGRATION.md is the cross-repository contract, so it is tested.

    The Blender shell is written against that document, in another
    repository, under another licence. Nothing else in either tree notices
    when the prose and ``OP_ARG_SPECS`` disagree — and a shell that calls an
    op the engine does not serve fails at the user, not at a test.
    """

    from CadexdProtocol import OP_ARG_SPECS

    documented = _documented_ops()
    implemented = set(OP_ARG_SPECS)
    assert documented == implemented, (
        "docs/INTEGRATION.md and CadexdProtocol.OP_ARG_SPECS disagree.\n"
        f"  documented but not served: {sorted(documented - implemented)}\n"
        f"  served but not documented: {sorted(implemented - documented)}\n"
        "With the shell in another repository, the document IS the contract."
    )
