# SPDX-License-Identifier: LGPL-2.1-or-later

"""The coupled-joint laws, measured against OndselSolver (M2, phase 9).

``CadexDynamics`` encodes three constants that cannot be derived from
anything in this repository: a gear pair counter-rotates at ``−r1/r2``, a
belt drives at ``+r1/r2``, and a screw advances ``pitch`` millimetres per
**revolution**. Each is a number FreeCAD's own solver decides, and each is
the kind of number that is wrong silently -- hazard 7: a gear train running
backwards looks exactly like a working mechanism, and a pitch out by 2π
looks like a coarse thread.

So they are not read off documentation. This drives the *kinematics* path --
real assemblies, real joints, OndselSolver -- through cadexd, measures what
FreeCAD actually did, and asserts the translator's coefficients match. If
FreeCAD changes its convention, this fails here rather than at a user
watching a mechanism run the wrong way.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx  # noqa: F401 - kept beside the fixtures it mirrors
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop
import test_dynamics_coupled as coupled

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: A nut on a slider and a shaft on a revolute, threaded together. The shaft
#: is driven one full turn; the nut's travel is the measurement.
SCREW_SCRIPT = """
frame = part.box(60, 60, 10)
nut = part.box(20, 20, 20)
shaft = part.cylinder(5, 80)
ground = assembly.component(frame, grounded=True)
jaw = assembly.component(nut, placement=[0, 0, 30])
rod = assembly.component(shaft)
guide = assembly.joint("slider",
                       assembly.connector(ground, "origin"),
                       assembly.connector(jaw, "origin"))
spin = assembly.joint("revolute",
                      assembly.connector(ground, "origin"),
                      assembly.connector(rod, "origin"))
thread = assembly.joint("screw",
                        assembly.connector(jaw, "origin"),
                        assembly.connector(rod, "origin"),
                        thread_pitch_mm=4.0)
asm = assembly.assembly([ground, jaw, rod], [guide, spin, thread])
diag = assembly.solve(asm)
drive = assembly.motion(spin, "2 * pi * time")
sim = assembly.simulation(asm, [drive], end_time_s=1.0, time_step_s=0.05)
result = {"frame": frame, "nut": nut, "shaft": shaft, "ground": ground,
          "jaw": jaw, "rod": rod, "guide": guide, "spin": spin,
          "thread": thread, "asm": asm, "diag": diag, "drive": drive,
          "sim": sim}
"""

#: Two wheels on parallel revolute joints, meshed. ``KIND`` is substituted
#: with gears or belt -- the same assembly, one word apart, which is what
#: makes the sign difference between them a measurement and not a story.
GEAR_SCRIPT = """
case = part.box(120, 60, 10)
first = part.cylinder(20, 10)
second = part.cylinder(10, 10)
housing = assembly.component(case, grounded=True)
pinion = assembly.component(first, placement=[0, 0, 20])
wheel = assembly.component(second, placement=[40, 0, 20])
axle1 = assembly.joint("revolute",
                       assembly.connector(housing, "origin", offset=[0, 0, 20]),
                       assembly.connector(pinion, "origin"))
axle2 = assembly.joint("revolute",
                       assembly.connector(housing, "origin", offset=[40, 0, 20]),
                       assembly.connector(wheel, "origin"))
mesh = assembly.joint("KIND",
                      assembly.connector(pinion, "origin"),
                      assembly.connector(wheel, "origin"),
                      radius1_mm=20.0, radius2_mm=10.0)
asm = assembly.assembly([housing, pinion, wheel], [axle1, axle2, mesh])
diag = assembly.solve(asm)
drive = assembly.motion(axle1, "2 * pi * time")
sim = assembly.simulation(asm, [drive], end_time_s=1.0, time_step_s=0.05)
result = {"case": case, "first": first, "second": second,
          "housing": housing, "pinion": pinion, "wheel": wheel,
          "axle1": axle1, "axle2": axle2, "mesh": mesh, "asm": asm,
          "diag": diag, "drive": drive, "sim": sim}
"""


def _ondsel_trace_bytes(source: str) -> bytes:
    """One kinematics run, through a cadexd of its own, as written bytes.

    A fresh project root and a fresh process each time: this is the harness
    both the coupling measurements and M3 phase 0's reproducibility
    question run on, and the latter is only a question at all if nothing is
    shared between the two runs being compared.
    """

    root = Path(tempfile.mkdtemp(prefix="ondsel-parity-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        entry = written["display"]["sim"]
        return Path(entry["artifact_path"]).read_bytes()
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _ondsel_trace(source: str) -> dict:
    return json.loads(_ondsel_trace_bytes(source).decode("utf-8"))


def _relative(frame: dict, first: str, second: str) -> tuple[list[float], list[float]]:
    """``second`` relative to ``first``, from one trace frame."""

    parent = frame["component_placements"][first]
    child = frame["component_placements"][second]
    inverse = dyn.quaternion_conjugate_wxyz(
        dyn.quaternion_wxyz_from_xyzw(parent["rotation_xyzw"])
    )
    offset = [
        child["position_mm"][index] - parent["position_mm"][index]
        for index in range(3)
    ]
    return (
        dyn.quaternion_rotate_wxyz(inverse, offset),
        dyn.quaternion_multiply_wxyz(
            inverse, dyn.quaternion_wxyz_from_xyzw(child["rotation_xyzw"])
        ),
    )


def _angle_about_z(quaternion_wxyz: list[float]) -> float:
    w, x, y, z = quaternion_wxyz
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def _unwrapped(values: list[float]) -> list[float]:
    """atan2 wraps at π; a driven revolution needs it not to."""

    result = [values[0]]
    for value in values[1:]:
        previous = result[-1]
        turns = round((previous - value) / (2.0 * math.pi))
        result.append(value + turns * 2.0 * math.pi)
    return result


def test_ondsel_turns_a_gear_pair_the_way_the_translator_says() -> None:
    trace = _ondsel_trace(GEAR_SCRIPT.replace("KIND", "gears"))
    frames = trace["frames"][1:]
    pinion = _unwrapped(
        [_angle_about_z(_relative(frame, "housing", "pinion")[1]) for frame in frames]
    )
    wheel = _unwrapped(
        [_angle_about_z(_relative(frame, "housing", "wheel")[1]) for frame in frames]
    )
    assert abs(pinion[-1] - pinion[0]) == pytest.approx(2.0 * math.pi, abs=1e-6)
    measured = (wheel[-1] - wheel[0]) / (pinion[-1] - pinion[0])
    assert measured == pytest.approx(-2.0, rel=1.0e-6)

    built = dyn.build_model(*coupled._gear_train("gears")[:2])
    assert built["couplings"][0]["slope"] == pytest.approx(measured, rel=1.0e-9)


def test_ondsel_turns_a_belt_the_other_way_and_so_does_the_translator() -> None:
    trace = _ondsel_trace(GEAR_SCRIPT.replace("KIND", "belt"))
    frames = trace["frames"][1:]
    pinion = _unwrapped(
        [_angle_about_z(_relative(frame, "housing", "pinion")[1]) for frame in frames]
    )
    wheel = _unwrapped(
        [_angle_about_z(_relative(frame, "housing", "wheel")[1]) for frame in frames]
    )
    measured = (wheel[-1] - wheel[0]) / (pinion[-1] - pinion[0])
    assert measured == pytest.approx(2.0, rel=1.0e-6)

    built = dyn.build_model(*coupled._gear_train("belt")[:2])
    assert built["couplings"][0]["slope"] == pytest.approx(measured, rel=1.0e-9)


def test_ondsel_advances_a_screw_one_pitch_per_revolution() -> None:
    """Hazard 7's 2π ambiguity, settled by experiment.

    ``joint.Distance`` is labelled only "Thread pitch" in the UI and could
    as easily have meant millimetres per radian. One driven revolution moved
    the nut 4.000 mm for a 4 mm pitch: it is per revolution.
    """

    trace = _ondsel_trace(SCREW_SCRIPT)
    frames = trace["frames"][1:]
    turns = _unwrapped(
        [_angle_about_z(_relative(frame, "ground", "rod")[1]) for frame in frames]
    )
    travel = [_relative(frame, "ground", "jaw")[0][2] for frame in frames]
    turned = turns[-1] - turns[0]
    moved = travel[-1] - travel[0]
    assert turned == pytest.approx(2.0 * math.pi, abs=1.0e-6)
    assert moved == pytest.approx(-4.0, abs=1.0e-6)
    # Linear throughout, not merely at the ends.
    middle = len(frames) // 2
    assert (travel[middle] - travel[0]) / (turns[middle] - turns[0]) == pytest.approx(
        moved / turned, rel=1.0e-6
    )

    built = dyn.build_model(*coupled._screw_stack(4.0)[:2])
    # The translator's slope is metres of slide per radian of shaft, with
    # the same sign Ondsel produced.
    assert built["couplings"][0]["slope"] == pytest.approx(
        dyn.length_m(moved / turned), rel=1.0e-9
    )


def test_ondsel_writes_byte_identical_traces_in_two_separate_processes() -> None:
    """M3 phase 0's fourth measurement, and it decides a later question.

    ADR-077 left the digest decision open on one precondition: a trace's
    ``artifact_sha256`` is in **no** project digest today, so a solver
    version bump changes every trace and moves nothing -- silent, which is
    strictly worse than loud. Putting it *in* a digest is only defensible
    if the solver already produces the same bytes twice, and that had never
    been measured for the solver we have shipped all along.

    So it is measured here, on OndselSolver rather than on MuJoCo, because
    the kinematics path is the one with users. Two cadexd processes, two
    project roots, nothing shared: the trace files compare equal byte for
    byte. Whatever the digest decision turns out to be, it is not blocked
    by the existing solver being irreproducible.
    """

    first = _ondsel_trace_bytes(SCREW_SCRIPT)
    second = _ondsel_trace_bytes(SCREW_SCRIPT)
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest(), (
        "OndselSolver produced different bytes for the same script in two "
        "processes; the digest decision in M3 phase 5 rests on this"
    )
    assert first == second
