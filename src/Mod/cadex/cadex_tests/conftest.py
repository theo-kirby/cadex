# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Test bootstrap: stub the FreeCAD runtime and put the module dir on sys.path.

The guardrail tests validate tool contracts and pack wiring, none of which
require a running FreeCAD. Tool modules defer their FreeCAD imports into
run() bodies, but a few top-level Cadex modules import FreeCAD at module
scope, so minimal stubs are installed before any Cadex import happens.
"""

from __future__ import annotations

from pathlib import Path
import sys
import types

CADEX_DIR = Path(__file__).resolve().parent.parent


def _install_freecad_stubs() -> None:
    for name in ("FreeCAD", "FreeCADGui"):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.GuiUp = False
            sys.modules[name] = module


_install_freecad_stubs()

if str(CADEX_DIR) not in sys.path:
    sys.path.insert(0, str(CADEX_DIR))

# The suite's own directory, so a test can reuse another's helpers rather
# than restating them (test_subshape_enumeration drives the cadexd client
# that test_cadexd_lifecycle already builds).
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))
