# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Phase 8 disables the inherited GUI before any GUI targets are registered."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("gui", [None, "OFF", "ON", "TRUE", "1"])
def test_build_options_are_headless(tmp_path, gui):
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("CMake unavailable")
    options = (Path(__file__).resolve().parents[4]
               / "cMake/FreeCAD_Helpers/InitializeFreeCADBuildOptions.cmake")
    script = tmp_path / "options.cmake"
    script.write_text(
        'cmake_minimum_required(VERSION 3.16)\n'
        f'include("{options.parent.as_posix()}/ChooseQtVersion.cmake")\n'
        'set(FREECAD_QT_VERSION 6)\n'
        f'include("{options.as_posix()}")\n'
        'InitializeFreeCADBuildOptions()\n'
        'if(BUILD_GUI)\n'
        '  message(FATAL_ERROR "GUI reached target registration")\n'
        'endif()\n'
    )
    result = subprocess.run(
        [cmake, *([] if gui is None else [f"-DBUILD_GUI:BOOL={gui}"]), "-P", str(script)],
        capture_output=True, text=True, timeout=30,
    )
    if gui in (None, "OFF"):
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
        assert "Cadex no longer supports BUILD_GUI=ON" in result.stderr


def test_every_public_preset_selects_headless_build():
    root = Path(__file__).resolve().parents[4]
    presets = json.loads((root / "CMakePresets.json").read_text())
    by_name = {p["name"]: p for p in presets["configurePresets"]}

    def gui_value(name):
        preset = by_name[name]
        if "BUILD_GUI" in preset.get("cacheVariables", {}):
            return preset["cacheVariables"]["BUILD_GUI"]["value"]
        parents = preset.get("inherits", [])
        if isinstance(parents, str):
            parents = [parents]
        for parent in parents:
            value = gui_value(parent)
            if value is not None:
                return value
        return None

    for name, preset in by_name.items():
        if not preset.get("hidden", False):
            assert gui_value(name) == "OFF", name
