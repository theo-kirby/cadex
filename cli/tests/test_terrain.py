# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A declared course reaches the exported model through the engine (ADR-714).

The one real-engine test for terrain: the script's ``terrain=`` crosses the
worker into ``build_model``, the retained MJCF carries the heightfield, and a
course that moves the ground under the start is refused by name. The grid,
the refusals and the contact are covered headless in
``src/Mod/cadex/cadex_tests/test_dynamics_terrain.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK

from test_smoke import FREE_BASE_SCRIPT

COURSE = (
    'terrain={"x_range_mm": [-200, 600], "y_range_mm": [-200, 200], '
    '"features": [{"kind": "step", "x_mm": STEP, "height_mm": 40}]})'
)


def _script(step_mm: int) -> str:
    source = FREE_BASE_SCRIPT.format(z=0)
    closing = "    assembly.body(swing, density_kg_m3=7850),\n])"
    assert closing in source
    return source.replace(
        closing,
        "    assembly.body(swing, density_kg_m3=7850),\n], "
        + COURSE.replace("STEP", str(step_mm)),
    )


def _set(tmp_path: Path, capsys, source: str, name: str) -> tuple[int, dict]:
    script = tmp_path / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    code = main(["script", "--set", str(script), "--project", str(tmp_path / name), "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_a_course_is_in_the_exported_model_and_one_under_the_start_is_refused(
    engine, tmp_path, capsys
) -> None:
    code, envelope = _set(tmp_path, capsys, _script(200), "course")
    assert code == EXIT_OK, envelope
    models = list((tmp_path / "course").rglob("outputs/model-model.xml"))
    assert models, "the MJCF output was not retained"
    xml = models[0].read_text(encoding="utf-8")
    assert '<hfield name="environment/terrain"' in xml
    assert 'name="environment/floor"' not in xml

    code, envelope = _set(tmp_path, capsys, _script(-50), "buried")
    assert code != EXIT_OK
    assert "terrain puts the ground at the origin 40 mm from z = 0" in envelope["error"]
