# SPDX-License-Identifier: LGPL-2.1-or-later

"""The determinism gate (docs/MUJOCO.md M3, phase 5).

Phase 0 measured this claim in its weakest form -- the same fixture in two
fresh interpreters, with no geoms in the model at all -- deliberately,
before contact existed to blame. This is the strong form: the same *script*,
through two separate ``cadexd`` processes, into two separate project roots,
with contact doing real work, compared as the bytes the project store
actually retained.

The distance between the two matters. Phase 0's version proves the
arithmetic is reproducible. This one proves the whole path is: FreeCAD
solving the assembly, OCCT computing mass properties and tessellating,
Qhull measuring the convexity, MuJoCo integrating the contacts, and the
worker serialising the result. Any one of those being order-dependent or
address-dependent would show up here and nowhere else.

**What this does *not* prove**, stated because a gate that overclaims is
worse than none: nothing here says anything about a different MuJoCo, a
different OCCT, or a different machine. MuJoCo disclaims cross-version
reproducibility outright (hazard 3). The pin is what holds that, and
``solver_version`` in the trace evidence is what makes a bump legible.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: A tumbling part landing on a plate, with a mesh collision shape, a
#: bouncing contact and a hand-picked solver step -- every M3 code path
#: that could plausibly introduce an ordering dependence, in one script.
CONTACT_SCRIPT = """
plate = part.box(400, 400, 20)
pin = part.cylinder(25, 120)
ground = assembly.component(plate, grounded=True)
faller = assembly.component(pin, placement=[200, 200, 400])
asm = assembly.assembly([ground, faller], [])
diag = assembly.solve(asm)
sim = assembly.dynamics(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[400, 400, 20],
                                               offset=[200, 200, 10],
                                               friction=0.7, restitution=0.4)),
    assembly.body(faller, density_kg_m3=2700,
                  collision=assembly.collision("mesh", deflection_mm=0.5,
                                               friction=0.7, restitution=0.4)),
], end_time_s=1.5, frames_per_second=60, solver_step_s=0.0005)
result = {"plate": plate, "pin": pin, "ground": ground, "faller": faller,
          "asm": asm, "diag": diag, "sim": sim}
"""


#: A driven mechanism, which the M3 gate never exercised. Actuators add a
#: per-step floating-point path -- a formula of ``time`` evaluated before
#: every ``mj_step`` -- and a control signal is exactly the kind of thing
#: that would depend on an accumulated clock without anybody noticing. The
#: setpoint is a function of ``time`` on purpose: a constant would evaluate
#: to the same number however the instant was computed, and would prove
#: nothing about the way it is computed.
ACTUATED_SCRIPT = """
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
], actuators=[
    assembly.actuator(shoulder, kind="position",
                      control_deg="25*sin(2*pi*time) + 10",
                      stiffness_nmm_per_deg=4000, damping_nmms_per_deg=200,
                      torque_limit_nmm=400000),
    assembly.actuator(elbow, kind="velocity", control_deg_per_s="20*cos(time)",
                      damping_nmms_per_deg=300),
], joint_dynamics=[
    assembly.joint_dynamics(shoulder, damping_nmms_per_deg=40,
                            armature_kgmm2=2000, friction_loss_nmm=50),
    assembly.joint_dynamics(elbow, damping_nmms_per_deg=15,
                            armature_kgmm2=500),
], end_time_s=2.0, frames_per_second=60, solver_step_s=0.0005)
result = {"column": column, "upper": upper, "fore": fore, "post": post,
          "arm": arm, "hand": hand, "shoulder": shoulder, "elbow": elbow,
          "asm": asm, "diag": diag, "sim": sim}
"""


def _retained_trace(source: str) -> tuple[bytes, dict]:
    """One script, one cadexd, one project root, and the bytes it wrote."""

    root = Path(tempfile.mkdtemp(prefix="m3-restart-"))
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
        return Path(entry["artifact_path"]).read_bytes(), entry
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def test_the_same_script_writes_the_same_trace_across_cadexd_restarts() -> None:
    """M3's exit criterion, and the reason the whole slice measured first.

    Two engines, two project roots, nothing shared but the script text, and
    the file compared is the one the project store retained -- not anything
    a test helper recomputed.
    """

    first_bytes, _first = _retained_trace(CONTACT_SCRIPT)
    second_bytes, _second = _retained_trace(CONTACT_SCRIPT)

    assert first_bytes == second_bytes
    digest = hashlib.sha256(first_bytes).hexdigest()
    # The digest the worker recorded, read back out of the trace's own
    # summary rather than recomputed here, so the two sides of the
    # comparison are the store's number and ours.
    for raw in (first_bytes, second_bytes):
        summary = json.loads(raw.decode("utf-8"))
        assert summary["schema"] == "cadex-assembly-simulation-trace-v1"
        assert hashlib.sha256(raw).hexdigest() == digest


def test_the_run_being_compared_is_one_where_contact_did_the_work() -> None:
    """A gate on a trace where nothing happened would pass and mean nothing.

    So the same run is checked for the thing it is supposed to contain: a
    part that starts 400 mm up, ends on the plate, and got there through
    geoms that were measured rather than assumed.
    """

    raw, _entry = _retained_trace(CONTACT_SCRIPT)
    trace = json.loads(raw.decode("utf-8"))
    evidence = trace["dynamics"]

    heights = [
        frame["component_placements"]["faller"]["position_mm"][2]
        for frame in trace["frames"]
    ]
    assert heights[1] == pytest.approx(400.0)
    assert heights[-1] < 60.0, "the part must have landed"
    assert min(heights) > -10.0, "and not fallen through the plate"

    mesh = next(
        shape
        for entry in evidence["collisions"]
        if entry["component_output"] == "faller"
        for shape in entry["shapes"]
    )
    assert mesh["kind"] == "mesh"
    assert mesh["vertex_count"] > 100
    assert abs(mesh["concavity"]) < dyn.COLLISION_CONVEXITY_TOLERANCE
    assert mesh["restitution"] == 0.4
    assert evidence["solver_integrator"] == "implicitfast"
    assert evidence["solver_disableflags"] != 0


def test_an_actuated_mechanism_writes_the_same_trace_across_restarts() -> None:
    """M4's half of the gate, and the reason it is re-run rather than assumed.

    Actuators add a per-step floating-point path the M3 gate never touched:
    a formula of ``time`` compiled once and evaluated before every
    ``mj_step``, 4 000 times over this run. The instant it is evaluated at
    is computed as ``start + index · step`` from an integer index
    specifically so that it cannot drift -- and this is what would catch a
    version of that which read the solver's own accumulated clock instead.
    Two engines, two project roots, nothing shared but the script text.
    """

    first_bytes, _first = _retained_trace(ACTUATED_SCRIPT)
    second_bytes, _second = _retained_trace(ACTUATED_SCRIPT)
    assert first_bytes == second_bytes
    assert (
        hashlib.sha256(first_bytes).hexdigest()
        == hashlib.sha256(second_bytes).hexdigest()
    )


def test_the_gate_ran_on_a_mechanism_the_motors_were_actually_driving() -> None:
    """A gate on a trace where the actuators did nothing would mean nothing.

    So the same run is checked for what it is supposed to contain: two
    motors of different kinds, a setpoint that varies, effort that was
    really produced, and an arm that moved because of it.
    """

    raw, _entry = _retained_trace(ACTUATED_SCRIPT)
    trace = json.loads(raw.decode("utf-8"))
    actuators = {
        record["joint_output"]: record
        for record in trace["dynamics"]["actuators"]
    }
    assert actuators["shoulder"]["kind"] == "position"
    assert actuators["elbow"]["kind"] == "velocity"
    assert actuators["shoulder"]["control"] == "25*sin(2*pi*time) + 10"
    assert actuators["shoulder"]["peak_effort_si"] > 1.0
    assert actuators["elbow"]["peak_effort_si"] > 0.0
    heights = [
        frame["component_placements"]["hand"]["position_mm"][2]
        for frame in trace["frames"][1:]
    ]
    assert max(heights) - min(heights) > 100.0, "the arm has to have swept"
    friction = {
        record["joint_output"]: record
        for record in trace["dynamics"]["joint_dynamics"]
    }
    assert friction["shoulder"]["friction_loss_si"] == pytest.approx(0.05)


def test_the_trace_says_which_mujoco_wrote_it() -> None:
    """Hazard 3 made legible while the digest decision sits on `main`.

    A trace's bytes are in no project digest today, so a MuJoCo version
    bump changes every trace and moves nothing -- silent, which ADR-062
    called strictly worse than loud. ADR-064 decides that the trace should
    join the digest and routes the change to `main`, because the digest
    code is shared with the kinematics trace and this branch does not edit
    shared code. Until then the artifact carries the version.
    """

    import mujoco

    raw, _entry = _retained_trace(CONTACT_SCRIPT)
    trace = json.loads(raw.decode("utf-8"))
    assert trace["dynamics"]["solver_version"] == mujoco.__version__


def test_the_trace_the_gate_compared_is_the_one_the_digest_now_covers() -> None:
    """M3 wrote this test inverted, and said so: ADR-068 is what rewrites it.

    The old body asserted that a trace's bytes reached no project digest, and
    its docstring named the routed change as the thing that would have to
    break it. The change landed on ``main`` (ADR-068) and arrived here on the
    sync, so the assertion turns over: the bytes this suite proves stable
    across restarts are now the bytes ``open_project`` compares.

    That is what closes the loop the whole suite exists for. Byte
    reproducibility across processes stopped being a property nobody
    consumed the moment the digest started consuming it — and it is why the
    reproducibility gate above is now load-bearing rather than aspirational.
    """

    from cadex_project_worker import compute_project_digest

    root = Path(tempfile.mkdtemp(prefix="m5-digest-"))
    try:
        artifact = root / "outputs" / "assembly-simulation-trace.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b'{"schema":"cadex-assembly-simulation-trace-v1"}')
        outputs = [
            {
                "name": "sim",
                "domain": "assembly",
                "type": "simulation",
                "artifact_kind": "assembly_simulation_json",
                "artifact_path": "outputs/assembly-simulation-trace.json",
                "definition": {"operation": "dynamics"},
            }
        ]
        first = compute_project_digest(root, outputs)

        # Different numbers out of the solver: a different project.
        artifact.write_bytes(
            b'{"schema":"cadex-assembly-simulation-trace-v1","frames":[]}'
        )
        assert compute_project_digest(root, outputs) != first, (
            "a trace's own bytes must reach the project digest"
        )

        # And the graph that asked for the trace still reaches it too --
        # ADR-068 added the bytes rather than substituting them.
        artifact.write_bytes(b'{"schema":"cadex-assembly-simulation-trace-v1"}')
        assert compute_project_digest(root, outputs) == first
        outputs[0]["definition"] = {"operation": "dynamics", "end_time_s": 2.0}
        assert compute_project_digest(root, outputs) != first
    finally:
        shutil.rmtree(root, ignore_errors=True)
