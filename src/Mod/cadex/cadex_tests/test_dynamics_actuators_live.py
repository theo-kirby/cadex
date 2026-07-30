# SPDX-License-Identifier: LGPL-2.1-or-later

"""M4's exit criterion, end to end (docs/MUJOCO.md M4, phase 6).

*A script can specify a motor and a setpoint, and the arm holds position
against gravity.*

Everything above this file runs on fixtures, which proves the arithmetic and
proves nothing about the path that fills its arguments. This runs the whole
of it: a script through a live ``cadexd``, FreeCAD solving the assembly,
OCCT computing the mass properties, the translator building the model,
MuJoCo closing the loop, and the trace the shell would play read back off
disk. ADR-023's rule generalises -- a passing pure module says nothing about
the code that feeds it.

The mechanism is a two-link arm on a grounded post, both links horizontal,
both hinges about world +Y. Horizontal is the worst case on purpose: gravity
has its full moment arm on the shoulder, and the forearm hangs off the upper
arm rather than off the post, so the shoulder carries a two-link subtree
whose inertia is not what a single-link intuition gives.

Three claims, and the second is what makes the first mean anything:

* with the motors, the arm reaches its setpoint and stays there;
* **without them, the same script's arm falls** -- so the first claim is
  about the actuator and not about a mechanism that was never going
  anywhere;
* a setpoint that is a function of ``time`` is tracked, which is the whole
  reason the control is a formula rather than a number.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: The arm, in one script. ``ACTUATORS`` and ``SETPOINT`` are substituted so
#: that the driven and undriven runs differ in exactly the motors and
#: nothing else -- same geometry, same solve, same densities, same duration.
ARM_SCRIPT = """
column = part.box(80, 80, 400)
upper = part.box(300, 40, 20)
fore = part.box(220, 30, 15)
post = assembly.component(column, grounded=True)
arm = assembly.component(upper, placement=[80, 20, 380])
hand = assembly.component(fore, placement=[380, 25, 382.5])
shoulder = assembly.joint("revolute",
                          assembly.connector(post, "origin",
                                             offset={"position": [80, 40, 390],
                                                     "axis": [1, 0, 0],
                                                     "angle_degrees": -90}),
                          assembly.connector(arm, "origin",
                                             offset={"position": [0, 20, 10],
                                                     "axis": [1, 0, 0],
                                                     "angle_degrees": -90}))
elbow = assembly.joint("revolute",
                       assembly.connector(arm, "origin",
                                          offset={"position": [300, 20, 10],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": -90}),
                       assembly.connector(hand, "origin",
                                          offset={"position": [0, 15, 7.5],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": -90}))
asm = assembly.assembly([post, arm, hand], [shoulder, elbow])
diag = assembly.solve(asm)
sim = assembly.dynamics(asm, [
    assembly.body(post, density_kg_m3=7850),
    assembly.body(arm, density_kg_m3=2700),
    assembly.body(hand, density_kg_m3=2700),
], actuators=[ACTUATORS], joint_dynamics=[
    assembly.joint_dynamics(shoulder, damping_nmms_per_deg=40,
                            armature_kgmm2=2000),
    assembly.joint_dynamics(elbow, damping_nmms_per_deg=15,
                            armature_kgmm2=500),
], end_time_s=2.5, frames_per_second=60)
result = {"column": column, "upper": upper, "fore": fore, "post": post,
          "arm": arm, "hand": hand, "shoulder": shoulder, "elbow": elbow,
          "asm": asm, "diag": diag, "sim": sim}
"""

#: A servo on each hinge. The shoulder holds SETPOINT and the elbow holds
#: the forearm straight out, which is the harder of the two loads.
SERVOS = """
    assembly.actuator(shoulder, kind="position", control_deg="SETPOINT",
                      stiffness_nmm_per_deg=4000, damping_nmms_per_deg=200,
                      torque_limit_nmm=400000),
    assembly.actuator(elbow, kind="position", control_deg="0",
                      stiffness_nmm_per_deg=1000, damping_nmms_per_deg=40,
                      torque_limit_nmm=100000),
"""


def _script(actuators: str, setpoint: str = "30") -> str:
    return ARM_SCRIPT.replace("ACTUATORS", actuators).replace("SETPOINT", setpoint)


def _run(source: str) -> dict:
    """One script through a cadexd of its own; the trace it retained."""

    root = Path(tempfile.mkdtemp(prefix="m4-arm-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:4000]
        entry = written["display"]["sim"]
        return json.loads(Path(entry["artifact_path"]).read_text(encoding="utf-8"))
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _turned_degrees(trace: dict, component: str, frame_index: int) -> float:
    """How far one component has rotated about +Y since the first solved frame.

    Read off the trace rather than out of the model, because the trace is
    what the shell plays: a servo that held ``qpos`` while the published
    poses said something else would be a working model and a broken
    product.

    **Signed**, and that matters here. Both hinges turn about world +Y and
    both links start along +X, so a positive angle is the arm going *down*
    -- which is the direction gravity pulls, and therefore the direction a
    proportional servo's steady-state error must lie in. An unsigned
    magnitude would report the sag and the overshoot as the same number.
    """

    def _quaternion(index: int) -> list[float]:
        placement = trace["frames"][index]["component_placements"][component]
        return dyn.quaternion_wxyz_from_xyzw(placement["rotation_xyzw"])

    relative = dyn.quaternion_multiply_wxyz(
        _quaternion(frame_index), dyn.quaternion_conjugate_wxyz(_quaternion(1))
    )
    return math.degrees(2.0 * math.atan2(relative[2], relative[0]))


@pytest.fixture(scope="module")
def held() -> dict:
    return _run(_script(SERVOS))


@pytest.fixture(scope="module")
def dropped() -> dict:
    return _run(_script(""))


# ---------------------------------------------------------------------------
# The criterion.
# ---------------------------------------------------------------------------


def test_the_arm_reaches_its_setpoint_and_holds_it(held: dict) -> None:
    """*A script can specify a motor and a setpoint, and the arm holds.*

    Thirty degrees asked for, and the steady-state error is bounded and
    measured rather than eyeballed: a proportional servo holding a load
    off-centre *must* sit past its setpoint, on gravity's side, by the
    load's torque divided by the gain. Here that is 0.44°, and asserting
    which side it falls on is most of what makes this a test of a servo
    rather than of a number.
    """

    settled = _turned_degrees(held, "arm", -1)
    assert settled == pytest.approx(30.0, abs=1.0)
    error = settled - 30.0
    assert 0.0 < error < 1.0, (
        "a proportional servo sits past its setpoint, downhill, by exactly "
        "this: the load's torque divided by the gain"
    )
    # And it is not still on its way there.
    assert abs(
        _turned_degrees(held, "arm", -1) - _turned_degrees(held, "arm", -20)
    ) < 0.01


def test_without_the_motors_the_same_arm_falls(dropped: dict) -> None:
    """The control, without which the test above proves nothing.

    Same geometry, same masses, same joint damping, same duration -- the
    actuators are the only difference, and this arm ends up hanging.
    """

    fallen = _turned_degrees(dropped, "arm", -1)
    assert fallen > 45.0, "gravity alone must take the arm well past its hold"
    tip = min(
        frame["component_placements"]["hand"]["position_mm"][2]
        for frame in dropped["frames"][1:]
    )
    held_tip = 380.0
    assert tip < held_tip - 100.0, "the forearm has to have actually dropped"


def test_the_elbow_holds_the_forearm_out_which_is_the_harder_load(
    held: dict, dropped: dict
) -> None:
    """Two actuators in one run, each on its own coordinate.

    The forearm is what makes the shoulder's job hard, so an elbow that
    quietly folded would make the shoulder's hold easy and the test above
    weaker than it looks.
    """

    assert abs(_turned_degrees(held, "hand", -1) - 30.0) < 2.0
    assert _turned_degrees(dropped, "hand", -1) > 45.0


# ---------------------------------------------------------------------------
# The evidence, which is where the run-level facts live.
# ---------------------------------------------------------------------------


def test_the_evidence_names_both_motors_and_what_they_had_to_do(held: dict) -> None:
    evidence = held["dynamics"]
    actuators = {record["joint_output"]: record for record in evidence["actuators"]}
    assert set(actuators) == {"shoulder", "elbow"}
    shoulder = actuators["shoulder"]
    assert shoulder["kind"] == "position"
    assert shoulder["motion_type"] == "angular"
    assert shoulder["control"] == "30"
    assert shoulder["declared"]["stiffness"] == 4000.0
    assert shoulder["stiffness_si"] == pytest.approx(dyn.stiffness_nm_per_rad(4000.0))
    # It had to hold a real load, and it did not run out of motor doing it.
    assert shoulder["peak_effort_si"] > 1.0
    assert shoulder["saturated"] is False
    damping = {
        record["joint_output"]: record for record in evidence["joint_dynamics"]
    }
    assert damping["shoulder"]["declared"]["armature"] == 2000.0
    assert damping["shoulder"]["armature_si"] == pytest.approx(2.0e-3)


def test_the_trace_is_the_schema_the_shell_already_plays(held: dict) -> None:
    """The claim this whole arc rests on, asserted rather than assumed."""

    assert held["schema"] == "cadex-assembly-simulation-trace-v1"
    assert held["motion_outputs"] == []
    for frame in held["frames"]:
        assert set(frame) == {
            "frame_index",
            "frame_kind",
            "nominal_time_s",
            "component_placements",
        }
        assert set(frame["component_placements"]) == {"post", "arm", "hand"}


# ---------------------------------------------------------------------------
# A setpoint that moves.
# ---------------------------------------------------------------------------


def test_the_arm_tracks_a_setpoint_that_is_a_function_of_time() -> None:
    """Which is why the control is a formula and not a number.

    ``25*sin(2*pi*time)`` at 1 Hz: the arm sweeps a full 50° peak to peak,
    passes through its start twice a second, and is back near zero at every
    whole second. A servo that ignored ``time`` would sit at one angle and
    every one of those checks would fail.
    """

    trace = _run(_script(SERVOS, setpoint="25*sin(2*pi*time)"))
    angles = {
        frame["nominal_time_s"]: _turned_degrees(trace, "arm", index)
        for index, frame in enumerate(trace["frames"])
        if frame["nominal_time_s"] is not None
    }
    swept = max(angles.values()) - min(angles.values())
    assert swept > 40.0, "the arm has to have followed the sweep"
    # A quarter period in, the command is at its positive peak; three
    # quarters in, at its negative one. The arm lags a real servo's lag, so
    # the check is that it is near the extremes rather than exactly on them.
    assert angles[0.25] > 15.0
    assert angles[0.75] < -15.0
    assert abs(angles[1.0]) < 10.0
    assert trace["dynamics"]["actuators"][0]["control"] == "25*sin(2*pi*time)"
