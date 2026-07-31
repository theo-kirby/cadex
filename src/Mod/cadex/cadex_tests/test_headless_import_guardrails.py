# SPDX-License-Identifier: LGPL-2.1-or-later

"""Guardrail: a GUI import must not decide whether App-level code exists.

The engine builds ``BUILD_GUI=OFF`` (ADR-022) and the payload prunes every
widget toolkit, scene-graph renderer and binding for either. Workbench
modules cope with that through ``try: import <gui thing> / except
ImportError:`` guards, which is correct — right up until an App-level import
is sitting in the same ``try`` body. Then the GUI import's failure is not
contained: it takes the App-level name down with it, and the module keeps
running with that name bound to ``None``.

``Assembly/JointObject.py`` has broken the headless engine three times, once
per GUI dependency it touches:

1. It imported Qt at module scope, and the first payload the packaged gate
   ever ran could not model at all (``No module named 'PySide'``) while the
   whole source-tree suite passed. Fixed with the ``try: from PySide import
   QtCore`` guard the file still carries.
2. **ADR-047.** ``Preferences.py`` imported ``FreeCADGui`` at module scope,
   so ``import Preferences`` raised headless, ``JointObject``'s guard set
   ``Preferences = None``, and ``solveIfAllowed()`` died on ``'NoneType'
   object has no attribute 'preferences'``. Fixed in the importee.
3. **ADR-060.** The same block still imported ``pivy`` beside
   ``Preferences``. The payload carries pivy but deletes libCoin, so ``from
   pivy import coin`` raised ``ImportError`` and reproduced (2) symptom for
   symptom — every joint refusing at ``native_connector_frames``.

Each fix addressed whichever import failed that time. This test addresses the
shape they share: whatever a workbench guards behind ``ImportError``, it may
not guard App-level code along with it.

Static, so it costs nothing and needs no FreeCAD: the payload ships modules,
not an import graph, and the hazard is visible in the source.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re

MOD_DIR = Path(__file__).resolve().parent.parent.parent
PAYLOAD_SCRIPT = (
    MOD_DIR.parent.parent / "package" / "engine" / "build_engine_payload.sh"
)

#: Import roots that are GUI-only and therefore *expected* to be missing from
#: a headless engine. Anything else in the same ``try`` body is collateral.
GUI_ONLY_ROOTS = frozenset(
    {
        "pivy",
        "PySide",
        "PySide2",
        "PySide6",
        "PySideUic",
        "FreeCADGui",
        "SoSwitchMarker",
    }
)

#: Exception names whose handler makes a failed import non-fatal.
_SWALLOWING = frozenset({"ImportError", "ModuleNotFoundError", "Exception"})


def _payload_workbenches() -> tuple[str, ...]:
    """The ``keep_mods`` list the payload actually carries.

    Read from the packaging script rather than duplicated, so adding a
    workbench to the payload brings it under this guardrail automatically
    instead of silently escaping it.
    """
    text = PAYLOAD_SCRIPT.read_text(encoding="utf-8")
    match = re.search(r'^keep_mods="([^"]+)"', text, re.MULTILINE)
    assert match, f"no keep_mods= line in {PAYLOAD_SCRIPT}"
    return tuple(match.group(1).split())


def _swallows_import_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        exc = handler.type
        if exc is None:
            return True
        names: list[str] = []
        if isinstance(exc, ast.Name):
            names = [exc.id]
        elif isinstance(exc, ast.Tuple):
            names = [e.id for e in exc.elts if isinstance(e, ast.Name)]
        if any(name in _SWALLOWING for name in names):
            return True
    return False


def _imported_roots(body: list[ast.stmt]) -> set[str]:
    """Top-level package names imported anywhere in ``body``.

    The ``try`` body only — an import inside the ``except`` handler is the
    recovery path, not a casualty of it (``Show/ShowUtils.py`` does exactly
    that, legitimately).
    """
    roots: set[str] = set()
    for statement in (node for stmt in body for node in ast.walk(stmt)):
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(statement, ast.ImportFrom):
            if statement.module and statement.level == 0:
                roots.add(statement.module.split(".")[0])
    return roots


def _mixed_guard_blocks() -> list[str]:
    problems: list[str] = []
    for workbench in _payload_workbenches():
        base = MOD_DIR / workbench
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try) or not _swallows_import_error(node):
                    continue
                roots = _imported_roots(node.body)
                gui = roots & GUI_ONLY_ROOTS
                collateral = roots - GUI_ONLY_ROOTS
                if gui and collateral:
                    problems.append(
                        f"{path.relative_to(MOD_DIR)}:{node.lineno}: "
                        f"{sorted(gui)} guards {sorted(collateral)} in the same "
                        f"try body; a headless ImportError would bind "
                        f"{sorted(collateral)} to the except branch's fallback"
                    )
    return problems


def test_no_gui_guard_takes_app_level_imports_down_with_it() -> None:
    problems = _mixed_guard_blocks()
    assert not problems, "GUI import guards with App-level collateral:\n" + "\n".join(
        problems
    )


def test_the_payload_prunes_the_coin_binding() -> None:
    """pivy goes, and the leak gate refuses to let it back.

    Pruning alone would be a fix somebody re-breaks by editing one rm; the
    gate below it is what makes it stay fixed. Both are asserted because the
    hazard is not the disk space, it is that a binding without its library
    changes which imports succeed (ADR-060).
    """
    text = PAYLOAD_SCRIPT.read_text(encoding="utf-8")
    assert "site-packages/pivy" in text, "the payload no longer prunes pivy"
    assert re.search(r"-iname 'pivy'", text), (
        "the payload's GUI-leak gate no longer names pivy"
    )
