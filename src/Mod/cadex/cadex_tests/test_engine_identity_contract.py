# SPDX-License-Identifier: LGPL-2.1-or-later

"""Guardrails for the user-facing Cadex product identity."""

from __future__ import annotations

import runpy
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[4]

MODULE_DIR = ROOT / "src" / "Mod" / "cadex"

# The four workbenches Cadex authors CAD surfaces for.
SUPPORTED_WORKBENCHES = (
    "PartDesignWorkbench",
    "SketcherWorkbench",
    "PartWorkbench",
    "AssemblyWorkbench",
)

# "Vibe" residue that intentionally survives the rename (migration property
# names / a session-check method that carry "Vibe" but not "VibeCAD").
#: Migration residue from the VibeCAD fork that was allowed to keep its old
#: name. Empty since Phase 7 C6a reverted isVibeExperimentalModeSession to
#: stock (ADR-022): the "Vibe" identity has left the tree entirely, and the
#: sweep below is now unconditional.
_ALLOWLISTED_VIBE_RESIDUE: tuple[str, ...] = ()


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_module_ships_only_cadex_named_python_and_no_stale_identity() -> None:
    # Every production module carries the PascalCase Cadex/lowercase cadex_ stem.
    production = [
        path for path in MODULE_DIR.glob("*.py") if path.name != "Init.py"
    ]
    assert production, "expected production Cadex modules to exist"
    for path in production:
        # cadexd.py is the headless engine service entry (Phase 5, ADR-017);
        # the service's product name is exactly "cadexd".
        assert path.name == "cadexd.py" or path.name.startswith(
            ("Cadex", "cadex_")
        ), path.name

    # No production module retains a VibeCAD/vibescript identity token (the
    # allowlisted Vibe* migration residue is stripped before the check).
    for path in production + [MODULE_DIR / "Init.py"]:
        text = path.read_text(encoding="utf-8")
        for allowed in _ALLOWLISTED_VIBE_RESIDUE:
            text = text.replace(allowed, "")
        assert "VibeCAD" not in text, path.name
        assert "vibescript" not in text, path.name
        assert "VibeScript" not in text, path.name
        assert "vibecad" not in text, path.name


def test_core_modeling_modules_import_under_cadex_names() -> None:
    import CadexScriptedDomains  # noqa: F401
    import CadexScriptedRuntime  # noqa: F401
    from CadexModelingSurface import resolve_modeling_surface

    for workbench in SUPPORTED_WORKBENCHES:
        surface = resolve_modeling_surface(workbench, "xscript")
        assert surface.available, workbench



def test_module_directory_and_preference_group_are_lowercase_cadex() -> None:
    assert (ROOT / "src" / "Mod" / "cadex").is_dir()
    assert not (ROOT / "src" / "Mod" / "VibeCAD").exists()

    # The Mod subdirectory is registered lowercase.
    mod_cmake = _source("src/Mod/CMakeLists.txt")
    assert "add_subdirectory(cadex)" in mod_cmake

    # The engine owns its preference group, in the lowercase namespace.
    source = _source("src/Mod/cadex/CadexEngineSettings.py")
    assert "User parameter:BaseApp/Preferences/Mod/cadex" in source
    assert "Mod/VibeCAD" not in source

    # And the inherited GUI core reads nothing of ours. Phase 6 asserted the
    # opposite -- that MainWindow.cpp read the cadex group -- because
    # isVibeExperimentalModeSession lived there. C6a reverted that hook to
    # stock (ADR-022), so the fork's delta against upstream FreeCAD in this
    # file is now zero, and this assertion is what keeps it there.
    for inherited in ("src/Gui/MainWindow.cpp", "src/Gui/MainWindow.h",
                      "src/Gui/ToolBarManager.cpp",
                      "src/Gui/DockWindowManager.cpp",
                      "src/Gui/OverlayWidgets.cpp"):
        text = _source(inherited)
        assert "Preferences/Mod/cadex" not in text, inherited
        assert "Vibe" not in text, inherited



def test_every_runtime_entry_point_uses_only_the_cadex_config_namespace() -> None:
    """ExeName is not branding; it decides where the engine's data lives.

    ``App::Application::Config()["ExeName"]`` determines FreeCAD's per-user
    application-data directory. Since Phase 7 the only entry point the
    product runs is MainCmd (FreeCADCmd hosting cadexd, ADR-022), so that
    file is where this contract has to hold: change "cadex" there and every
    project store that fell back to the appdata path moves.
    """
    for relative_path in (
        "src/Main/MainCmd.cpp",   # the engine entry point; load-bearing
        "src/Main/MainGui.cpp",
        "src/Main/MainPy.cpp",
    ):
        source = _source(relative_path)
        assert 'Config()["ExeName"] = "cadex"' in source
        assert 'Config()["ExeVendor"] = "cadex"' in source
        assert 'Config()["AppDataSkipVendor"] = "true"' in source
        assert 'Config()["ExeName"] = "FreeCAD"' not in source
        assert 'Config()["ExeVendor"] = "FreeCAD"' not in source
        assert "VibeCAD" not in source
        assert "vibescript" not in source
















