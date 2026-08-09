# SPDX-License-Identifier: LGPL-2.1-or-later

"""Declared dimensions: ``part.measurement`` and what it publishes (ADR-139).

Two halves, and the second one is the feature.

The first half is the API surface, headless: what a measurement refuses, and
the fact that it refuses by naming the thing that is wrong rather than by
raising something generic.

The second half drives a real cadexd child. It builds a parametric plate with
a bore, declares one measurement of each kind, and asserts the numbers against
arithmetic anybody can do on paper. Then it **moves a parameter and asserts
the measurements moved with it**, which is the entire justification for
putting measurements in the script rather than in the shell: a dimension that
did not follow its part would be a decoration.

The client, the spawn and the response validation are
``test_cadexd_lifecycle``'s, so every frame here is checked against the engine
under test's own ``OP_RESPONSE_SPECS`` — and this file therefore also gates
the ``display.<output>.measurement`` record against a packaged payload when
``CADEX_ENGINE_ROOT`` is set.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

import pytest

from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api

from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]

#: A plate with a bore through it, and one measurement of each kind. The
#: width is the parameter that moves; the thickness and the bore are fixed,
#: so a rebuild that moved *those* would be a bug this test would see.
MEASURED_SCRIPT = """
p = params(width=num(60, unit="mm", min=20, max=120, step=1))
plate = part.box(p.width, 40, 10)
bored = part.cut(plate, part.cylinder(3, 30, origin=[15, 20, -10]))

height = part.measurement(bored, kind="extent", axis="z",
                          label="overall height")
span = part.measurement(bored, kind="extent", axis="x")
thickness = part.measurement(
    bored,
    kind="distance",
    start={"geometry_type": "Plane", "normal": [0, 0, -1]},
    end={"geometry_type": "Plane", "normal": [0, 0, 1]},
)
bore = part.measurement(
    bored, kind="diameter", at={"geometry_type": "Cylinder", "radius": 3.0}
)
result = {"bored": bored, "height": height, "span": span,
          "thickness": thickness, "bore": bore}
"""


def _part():
    return create_domain_api(
        PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types
    )


def _box():
    return _part().box(60.0, 40.0, 10.0, label="plate")


# -- the API surface, headless ---------------------------------------------


def test_a_measurement_is_a_declared_output_with_no_geometry() -> None:
    value = _part().measurement(_box(), kind="extent", axis="z", label="tall")

    assert value.domain == "part"
    assert value.output_type == "measurement"
    # It is not a shape class, and that is the point: it is the one part
    # output the pack publishes that nothing can be built from.
    assert "measurement" not in {"solid", "shell", "face", "wire", "compound"}
    assert value.properties["kind"] == "extent"
    assert value.properties["axis"] == "z"
    assert value.properties["label"] == "tall"
    assert value.properties["places"] == 2


def test_a_measurement_names_what_is_wrong_rather_than_failing_generically() -> None:
    part = _part()
    plate = _box()

    with pytest.raises(ValueError) as bad_kind:
        part.measurement(plate, kind="gap")
    assert "kind" in str(bad_kind.value)
    assert "['diameter', 'distance', 'extent']" in str(bad_kind.value)

    with pytest.raises(ValueError) as half_a_distance:
        part.measurement(plate, kind="distance", start={"geometry_type": "Plane"})
    assert "start= and end=" in str(half_a_distance.value)

    with pytest.raises(ValueError) as no_target:
        part.measurement(plate, kind="diameter")
    assert "at=" in str(no_target.value)

    with pytest.raises(ValueError) as bad_axis:
        part.measurement(plate, kind="extent", axis="w")
    assert "axis" in str(bad_axis.value)

    with pytest.raises(ValueError) as bad_elements:
        part.measurement(plate, kind="extent", axis="z", element_type="vertex")
    assert "element_type" in str(bad_elements.value)

    # The selector vocabulary is the shared one, closed on purpose: a typo
    # that widened a match would put a number on the wrong feature.
    with pytest.raises(ValueError) as typo:
        part.measurement(
            plate,
            kind="diameter",
            at={"geometry_type": "Cylinder", "radius_tolerence": 0.1},
        )
    assert "unrecognised selector keys" in str(typo.value)

    with pytest.raises(ValueError) as not_a_part:
        part.measurement("plate", kind="extent", axis="z")
    assert "returned by this Part api" in str(not_a_part.value)


def test_a_measurement_selector_is_pinned_to_exactly_one_subshape() -> None:
    part = _part()

    # A dimension has two ends, so each end names one thing. Left free, a
    # selector matching four faces would silently measure whichever one the
    # kernel enumerated first.
    value = part.measurement(
        _box(),
        kind="distance",
        start={"geometry_type": "Plane", "normal": [0, 0, -1]},
        end={"geometry_type": "Plane", "normal": [0, 0, 1]},
    )
    assert value.properties["start"]["expected_count"] == 1
    assert value.properties["end"]["expected_count"] == 1

    with pytest.raises(ValueError) as several:
        part.measurement(
            _box(),
            kind="diameter",
            at={"geometry_type": "Cylinder", "expected_count": 4},
        )
    assert "expected_count" in str(several.value)


def test_the_number_is_formatted_engine_side_within_bounds() -> None:
    part = _part()

    assert part.measurement(
        _box(), kind="extent", axis="z", places=0
    ).properties["places"] == 0

    for refused in (-1, 7, 2.5, True):
        with pytest.raises(ValueError) as bad:
            part.measurement(_box(), kind="extent", axis="z", places=refused)
        assert "places" in str(bad.value)


def test_the_part_pack_publishes_measurement_and_the_api_declares_it() -> None:
    # Two hand-written ordered tuples that must agree: the pack's exports and
    # the API's own names. They are checked against each other at runtime, so
    # a mismatch is a hard failure at worker start rather than a missing verb.
    assert "measurement" in PART_PACK.api_exports
    assert "measurement" in _part().exported_names
    assert "measurement" in PART_PACK.output_types


# -- against a real engine, which is where the numbers become real ----------


def _display(reply: dict) -> dict:
    return dict(reply.get("display") or {})


def _measurement(reply: dict, name: str) -> dict:
    entry = _display(reply).get(name) or {}
    assert isinstance(entry.get("measurement"), dict), (name, entry)
    return dict(entry["measurement"])


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the measurement CI."
)
def test_measurements_are_published_and_follow_the_part_they_measure() -> None:
    root = Path(tempfile.mkdtemp(prefix="cadex-measure-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        built = client.request(
            "write_script", {"source": MEASURED_SCRIPT, "expected_revision": ""}
        )
        assert built["ok"] is True, built

        # A measurement entry carries no geometry at all -- no artifact, no
        # tessellation, no placement of its own. A client that keys on
        # "has a tessellation" skips it and loses nothing it knew how to draw.
        entry = _display(built)["height"]
        assert entry["artifact_kind"] is None, entry
        assert entry["tessellation"] is None, entry
        assert entry["placement"] is None, entry
        assert "measurement" in entry, entry
        assert "measurement" not in _display(built)["bored"], built

        # ...and the shape it measures is a normal output, unchanged.
        assert _display(built)["bored"]["artifact_kind"] == "brep", built

        height = _measurement(built, "height")
        assert height["kind"] == "extent"
        assert height["subject"] == "bored", height
        assert height["label"] == "overall height"
        assert height["value_mm"] == pytest.approx(10.0), height
        assert height["text"] == "10.00 mm", height
        assert height["places"] == 2
        # The anchors run down the centre line of the part rather than off a
        # corner, so the dimension reads through the solid.
        near, far = height["anchors_mm"]
        assert near == pytest.approx([30.0, 20.0, 0.0]), height
        assert far == pytest.approx([30.0, 20.0, 10.0]), height
        assert height["center_mm"] is None and height["radius_mm"] is None, height

        # A distance is the kernel's own closest approach, which is why it
        # needs no special case per geometry: two parallel planes give the
        # thickness, and the anchors come back from the same call.
        thickness = _measurement(built, "thickness")
        assert thickness["kind"] == "distance"
        assert thickness["value_mm"] == pytest.approx(10.0), thickness
        assert thickness["label"] == "", thickness
        first, second = thickness["anchors_mm"]
        assert abs(second[2] - first[2]) == pytest.approx(10.0), thickness

        # A diameter publishes the circle, not two points: which diameter is
        # legible depends on where the camera is, and that is per frame.
        bore = _measurement(built, "bore")
        assert bore["kind"] == "diameter"
        assert bore["value_mm"] == pytest.approx(6.0), bore
        assert bore["radius_mm"] == pytest.approx(3.0), bore
        assert bore["anchors_mm"] is None, bore
        assert bore["text"] == "Ø6.00 mm", bore
        assert bore["center_mm"][0] == pytest.approx(15.0), bore
        assert bore["center_mm"][1] == pytest.approx(20.0), bore
        assert bore["normal"] == pytest.approx([0.0, 0.0, 1.0]), bore

        span = _measurement(built, "span")
        assert span["value_mm"] == pytest.approx(60.0), span

        # -- move the part, and the measurements must move ----------------
        moved = client.request(
            "set_params",
            {
                "values": {"width": 90},
                "expected_revision": built["model_state"][
                    "next_write_expected_revision"
                ],
            },
        )
        assert moved["ok"] is True, moved
        assert moved["digest"] != built["digest"], moved

        # This is the whole reason a measurement lives in the script. The
        # span followed the parameter; the height and the bore did not move,
        # because nothing moved them.
        assert _measurement(moved, "span")["value_mm"] == pytest.approx(90.0)
        assert _measurement(moved, "span")["text"] == "90.00 mm"
        assert _measurement(moved, "height")["value_mm"] == pytest.approx(10.0)
        assert _measurement(moved, "bore")["value_mm"] == pytest.approx(6.0)
        # ...and the extent's anchors moved to the new centre line with it.
        assert _measurement(moved, "height")["anchors_mm"][0] == pytest.approx(
            [45.0, 20.0, 0.0]
        )

        # -- and the project still opens afterwards -----------------------
        # A measurement enters the digest through its own declaration, so
        # adding or moving one moves the digest. A digest-moving change that
        # a project cannot restore from locks it out at open
        # (`simple-willow-8989`), so this is checked rather than assumed.
        _stop(client)
        client = _spawn_cadexd()
        again = client.request("open_project", {"project_root": str(root)})
        assert again["ok"] is True, again
        assert again["restore"]["performed"] is True, again
        assert again["restore"]["matches_accepted"] is True, again
    finally:
        if client is not None:
            _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the measurement CI."
)
def test_a_measurement_that_cannot_be_taken_refuses_against_the_real_engine() -> None:
    root = Path(tempfile.mkdtemp(prefix="cadex-measure-refuse-"))
    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(root)})["ok"] is True

        # Two faces that touch have no distance between them, and a dimension
        # drawn on them would put both anchors in the same place.
        touching = client.request(
            "write_script",
            {
                "source": (
                    'plate = part.box(20, 20, 5)\n'
                    'zero = part.measurement(\n'
                    '    plate, kind="distance",\n'
                    '    start={"geometry_type": "Plane", "normal": [0, 0, 1]},\n'
                    '    end={"geometry_type": "Plane", "normal": [1, 0, 0]})\n'
                    'result = {"plate": plate, "zero": zero}\n'
                ),
                "expected_revision": "",
            },
        )
        assert touching["ok"] is False, touching
        assert "0 mm" in str(touching.get("error") or touching), touching

        # A selector that names nothing reports what *was* available, so the
        # agent can re-query rather than guess.
        missing = client.request(
            "write_script",
            {
                "source": (
                    'plate = part.box(20, 20, 5)\n'
                    'nope = part.measurement(\n'
                    '    plate, kind="diameter",\n'
                    '    at={"geometry_type": "Cylinder", "radius": 3.0})\n'
                    'result = {"plate": plate, "nope": nope}\n'
                ),
                "expected_revision": "",
            },
        )
        assert missing["ok"] is False, missing
        # It names the selector and lists what *was* there, which is the
        # difference between a refusal an agent can act on and one it can
        # only retry.
        observed = str(missing.get("observed") or "") + str(missing.get("error") or "")
        assert "Cylinder" in observed or "available" in observed, missing

        # Neither script was published: a measurement that cannot be taken
        # fails the whole rebuild rather than publishing a model with a hole
        # in it. The document was never mutated, so there is nothing to undo.
        for refusal in (touching, missing):
            change = dict(refusal.get("state_change") or {})
            assert change.get("changed") is not True, refusal
            assert change.get("commit_succeeded") is not True, refusal
    finally:
        if client is not None:
            _stop(client)
        shutil.rmtree(root, ignore_errors=True)
