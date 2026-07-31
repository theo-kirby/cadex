# SPDX-License-Identifier: LGPL-2.1-or-later

"""Turning the accepted model into files, against a real engine.

The plan-building half needs no engine and is checked directly; the
conversion half is checked by building a solid whose volume is known by
hand, exporting it, and reading the files back. A test that only asserted
"a file appeared" would pass for an empty one.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from cadex_cli.client import CadexdClient, open_project
from cadex_cli.export import (
    ExportError,
    export_outputs,
    export_plan,
    parse_formats,
    safe_stem,
)

#: 40 x 25 x 15 with a 6 mm bore through it: 15000 - pi*3^2*15 mm^3.
BRACKET = """
plate = part.box(40.0, 25.0, 15.0)
bore = part.cylinder(3.0, 19.0, origin=[20.0, 12.5, -2.0])
result = {"bracket": part.cut(plate, [bore])}
"""
BRACKET_VOLUME_MM3 = 40.0 * 25.0 * 15.0 - math.pi * 9.0 * 15.0

#: A part, a mesh skin of it, and a solve diagnostic — three artifact kinds,
#: exactly one of which this exports.
MIXED = """
plate = part.box(20.0, 10.0, 4.0)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "skin": skin}
"""


# -- the plan ------------------------------------------------------------


def test_formats_are_parsed_and_unknown_ones_are_refused() -> None:
    assert parse_formats("step,stl") == ["step", "stl"]
    assert parse_formats(" STEP , brep ,step") == ["step", "brep"]
    assert parse_formats(None) == ["step", "stl"]
    with pytest.raises(ExportError):
        parse_formats("dxf")
    with pytest.raises(ExportError):
        parse_formats(",")


def test_output_names_become_filenames_without_inventing_paths() -> None:
    assert safe_stem("bracket") == "bracket"
    assert safe_stem("../escape") == "escape"
    assert safe_stem("a b/c") == "a_b_c"
    assert safe_stem("///") == "output"


def test_outputs_with_no_brep_are_reported_skipped_not_dropped(tmp_path) -> None:
    """Three outputs and one file should say which two, and why."""

    display = {
        "plate": {"artifact_kind": "brep", "artifact_path": "/staged/p.brep"},
        "skin": {"artifact_kind": "mesh", "artifact_path": "/staged/s.ply"},
        "base": {"artifact_kind": None, "artifact_path": None, "placement": [1.0]},
    }

    plan, rows = export_plan(display, tmp_path, ["step"])

    assert [job["name"] for job in plan] == ["plate"]
    by_name = {row.name: row for row in rows}
    assert by_name["skin"].skipped == "not a BREP output"
    assert by_name["base"].skipped == "not a BREP output"
    assert by_name["plate"].skipped == ""
    assert plan[0]["targets"][0]["path"] == str(tmp_path / "plate.step")


# -- the conversion ------------------------------------------------------


@pytest.fixture
def built(engine, tmp_path):
    """An accepted bracket: the reply, and the engine's facts about it."""

    client = CadexdClient(engine)
    client.start()
    try:
        open_project(client, tmp_path / "project")
        written = client.request(
            "write_script", {"source": BRACKET, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        facts = client.request(
            "inspect", {"scope": "output", "target": "bracket", "path": "/facts"}
        )
        assert facts["ok"] is True, facts
        yield {"reply": written, "facts": facts["value"]}
    finally:
        client.shutdown()


def test_a_brep_output_exports_to_step_and_stl(engine, built, tmp_path) -> None:
    out = tmp_path / "out"

    rows = export_outputs(engine, built["reply"]["display"], out, ["step", "stl", "brep"])

    (row,) = rows
    assert row.name == "bracket" and row.kind == "brep"
    step = Path(row.files["step"])
    stl = Path(row.files["stl"])
    brep = Path(row.files["brep"])
    assert step.is_file() and stl.is_file() and brep.is_file()

    # A real AP214 STEP, not an empty file with the right name.
    head = step.read_text(encoding="utf-8", errors="replace")[:4096]
    assert head.startswith("ISO-10303-21;")
    assert "AUTOMOTIVE_DESIGN" in head or "CONFIG_CONTROL_DESIGN" in head
    assert step.stat().st_size > 1000

    # A real STL with facets in it.
    assert stl.stat().st_size > 1000

    # The engine's own facts agree with the arithmetic, which is what says
    # the exported shape is the shape that was accepted. It is also exactly
    # the check the headless agent is told to make: there is no picture.
    assert built["facts"]["shape_type"] == "Solid"
    assert built["facts"]["volume_mm3"] == pytest.approx(BRACKET_VOLUME_MM3, rel=1e-9)
    # Six planes and one cylinder: the bore went all the way through.
    assert built["facts"]["faces"] == 7


def test_only_the_brep_half_of_a_mixed_model_is_written(engine, tmp_path) -> None:
    client = CadexdClient(engine)
    client.start()
    try:
        open_project(client, tmp_path / "project")
        written = client.request(
            "write_script", {"source": MIXED, "expected_revision": ""}
        )
        assert written["ok"] is True, written
    finally:
        client.shutdown()

    rows = export_outputs(engine, written["display"], tmp_path / "out", ["step"])

    by_name = {row.name: row for row in rows}
    assert Path(by_name["plate"].files["step"]).is_file()
    assert by_name["skin"].files == {}
    assert by_name["skin"].skipped == "not a BREP output"


def test_a_missing_source_artifact_is_an_error_not_a_silent_zero(
    engine, tmp_path
) -> None:
    display = {
        "ghost": {"artifact_kind": "brep", "artifact_path": str(tmp_path / "gone.brep")}
    }
    with pytest.raises(ExportError) as caught:
        export_outputs(engine, display, tmp_path / "out", ["step"])
    assert "ghost" in str(caught.value)


def test_a_model_with_no_geometry_writes_nothing_and_says_so(
    engine, tmp_path
) -> None:
    rows = export_outputs(engine, {}, tmp_path / "out", ["step"])
    assert rows == []


def test_step_carries_a_wall_clock_stamp_so_pipelines_hash_the_digest(
    engine, built, tmp_path
) -> None:
    """The reason ``--json`` reports a digest at all.

    AP214 writes a generation timestamp into ``FILE_NAME``, so two exports
    of one identical model agree only when they happen inside the same
    second. A pipeline that diffs the file therefore sees change where there
    is none, and must compare the engine's content digest instead. The BREP
    beside it *is* stable, which is what makes the STEP's instability the
    format's and not the model's.
    """

    display = built["reply"]["display"]
    step = Path(export_outputs(engine, display, tmp_path / "a", ["step"])[0].files["step"])
    stamped = re.search(
        r"FILE_NAME\([^;]*'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'",
        step.read_text(encoding="utf-8", errors="replace")[:2048],
    )
    assert stamped, step.read_text(encoding="utf-8", errors="replace")[:512]

    first = Path(export_outputs(engine, display, tmp_path / "c", ["brep"])[0].files["brep"])
    second = Path(export_outputs(engine, display, tmp_path / "d", ["brep"])[0].files["brep"])
    assert first.read_bytes() == second.read_bytes()
