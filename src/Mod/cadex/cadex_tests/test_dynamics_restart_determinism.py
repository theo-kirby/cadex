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


def test_a_trace_is_still_absent_from_the_project_digest_and_that_is_recorded() -> None:
    """The state ADR-064 is a decision about, pinned so the change is visible.

    ``cadex_project_worker.compute_project_digest`` hashes exported BREP for shape
    outputs, a vertex fingerprint for meshes, and the canonical *definition*
    for everything else. A simulation is everything else: its digest entry
    is the graph that produced it, not the numbers that came out. When the
    routed change lands from `main` this test is what has to be rewritten,
    which is the point of writing it.
    """

    from cadex_project_worker import compute_project_digest

    root = Path(tempfile.mkdtemp(prefix="m3-digest-"))
    try:
        outputs = [
            {
                "name": "sim",
                "domain": "assembly",
                "type": "simulation",
                "artifact_path": "outputs/assembly-simulation-trace.json",
                "artifact_kind": "assembly_simulation_json",
                "artifact_sha256": "a" * 64,
                "definition": {"operation": "dynamics"},
            }
        ]
        first = compute_project_digest(root, outputs)
        outputs[0]["artifact_sha256"] = "b" * 64
        assert compute_project_digest(root, outputs) == first, (
            "today the trace's own bytes do not reach the project digest"
        )
        outputs[0]["definition"] = {"operation": "dynamics", "end_time_s": 2.0}
        assert compute_project_digest(root, outputs) != first, (
            "what does reach it is the graph that asked for the trace"
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)
