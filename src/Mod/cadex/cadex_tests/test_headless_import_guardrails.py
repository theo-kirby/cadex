# SPDX-FileCopyrightText: 2026 Cadex Authors
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
import os
from pathlib import Path
import re

import pytest

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
    recovery path, not a casualty of it (the deleted ``Show/ShowUtils.py``
    did exactly that, legitimately; ADR-632).
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


def test_the_payload_prunes_the_llvm_toolchain() -> None:
    """LLVM and clang go, and the leak gate refuses to let them back (ADR-531).

    Nothing in the payload links them except each other: they serve Qt's
    tools, PySide's generator and the compiler, never the running engine.
    The prune and the gate are both asserted, as for pivy above.
    """
    text = PAYLOAD_SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"-name 'libLLVM\*' -o -name 'libclang\*' \\\n\s+-o -name 'libLTO", text), (
        "the payload no longer prunes libLLVM/libclang/libLTO"
    )
    assert 'rm -rf "${payload}/lib/clang"' in text, (
        "the payload no longer prunes lib/clang"
    )
    gate = text[text.index('leaked="$(find'):text.index('if [ -n "${leaked}" ]')]
    assert "libLLVM*" in gate and "libclang*" in gate, (
        "the payload's leak gate no longer names libLLVM/libclang"
    )


def test_a_staged_payload_carries_no_llvm() -> None:
    """The packaged half: a staged payload has no LLVM or clang library."""
    root = os.environ.get("CADEX_ENGINE_ROOT")
    if not root:
        pytest.skip("CADEX_ENGINE_ROOT not set (packaged-gate test)")
    lib = Path(root) / "lib"
    found = sorted(
        p.name
        for pattern in ("libLLVM*", "libclang*", "libLTO.so*", "libRemarks.so*")
        for p in lib.glob(pattern)
    )
    assert not found, f"LLVM/clang back in the payload: {found}"
    assert not (lib / "clang").exists(), "lib/clang back in the payload"


def test_the_payload_prunes_opencv_pcl_node_and_perl() -> None:
    """OpenCV, PCL, Node and Perl go, and the gate refuses them (ADR-532).

    No payload ELF links them except each other and cv2, which nothing in
    the payload imports; Node and Perl arrive with pyright and git, and the
    payload carries neither interpreter.
    """
    text = PAYLOAD_SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"-name 'libopencv\*' -o -name 'libpcl\*' \\\n\s+-o -name 'libnode", text), (
        "the payload no longer prunes libopencv/libpcl/libnode"
    )
    for tree in ('"${payload}/lib/node_modules"', '"${payload}/lib/perl5"',
                 '"${payload}/share/opencv4"', 'site-packages/cv2'):
        assert tree in text, f"the payload no longer prunes {tree}"
    gate = text[text.index('leaked="$(find'):text.index('if [ -n "${leaked}" ]')]
    for name in ("libopencv*", "libpcl*", "libnode.*", "site-packages/cv2",
                 "lib/node_modules", "lib/perl5"):
        assert name in gate, f"the payload's leak gate no longer names {name}"


def test_a_staged_payload_carries_no_opencv_pcl_node_or_perl() -> None:
    """The packaged half: a staged payload has none of the four."""
    root = os.environ.get("CADEX_ENGINE_ROOT")
    if not root:
        pytest.skip("CADEX_ENGINE_ROOT not set (packaged-gate test)")
    lib = Path(root) / "lib"
    found = sorted(
        p.name
        for pattern in ("libopencv*", "libpcl*", "libnode.*")
        for p in lib.glob(pattern)
    )
    assert not found, f"OpenCV/PCL/Node back in the payload: {found}"
    for tree in ("node_modules", "perl5"):
        assert not (lib / tree).exists(), f"lib/{tree} back in the payload"
    assert not list(lib.glob("python*/site-packages/cv2")), "cv2 back in the payload"
