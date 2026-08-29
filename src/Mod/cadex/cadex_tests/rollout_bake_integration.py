# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""M8's exit evidence: the shell's own bake, on a real rollout trace.

ADR-077 exists to prevent one failure -- *a trace the engine is happy with
and* ``cadex_animate`` *declines to bake*. A rollout is the third thing to
produce an ``assembly_simulation_json``, so that failure is exactly what M8
has to rule out, and only the shell can rule it out.

**Two halves, one file, and no ``shell/`` diff anywhere** (ADR-078):

* under the engine's own interpreter it *writes* a rollout trace, by driving
  a live ``cadexd`` through the whole chain -- mechanism, model, task,
  policy, rollout -- so the bytes being baked are bytes the engine really
  produced;
* under the shipped bundle's Blender it *bakes* that trace, through
  ``mesh_agent.cadex_animate``'s real functions on real objects, and reports
  the keyframes.

The ``dynamics_trace_digest`` idiom -- importable and runnable -- applied
across the process boundary instead of across two interpreters of the same
kind.

Run it::

    pixi run python src/Mod/cadex/cadex_tests/rollout_bake_integration.py \\
        /tmp/rollout-trace.json
    CADEX_ROLLOUT_TRACE=/tmp/rollout-trace.json pixi run gate \\
        "$PWD/src/Mod/cadex/cadex_tests/rollout_bake_integration.py"

The second command runs this file inside ``Cadex.app``, through the gate's
own entry point, with every ``MESH_*`` override unset. Nothing under
``shell/`` is touched, read or modified; the add-on is imported from the
bundle the way the product imports it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (str(_HERE.parent), str(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


# ---------------------------------------------------------------------------
# The engine half: write a rollout trace by running the real chain.
# ---------------------------------------------------------------------------


def write_trace(destination: Path) -> dict:
    """Drive a live cadexd to a published rollout trace, and copy it out.

    Deliberately the *live* path rather than a hand-assembled dict: what the
    shell has to be able to bake is what the engine writes, and a fixture of
    what we believe it writes would prove nothing about the seam.
    """

    import hashlib
    import shutil
    import tempfile

    import dynamics_policy_fixtures as pf
    from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop
    from test_dynamics_policy_live import ROLLOUT_SCRIPT, TASK_SCRIPT

    if FREECADCMD is None:
        raise SystemExit(
            "no FreeCADCmd to drive; run pixi run build-engine first"
        )

    root = Path(tempfile.mkdtemp(prefix="m8-bake-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": TASK_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:2000]
        revision = str(written["revision"])
        bundle_path = Path(written["display"]["job"]["artifact_path"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        container = pf.policy_container(
            {"bundle": bundle,
             "task_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()},
            normalise=True,
        )
        weights = root.parent / "walk.cxpolicy"
        weights.write_bytes(container["blob"])
        stored = client.request(
            "put_asset", {"source_path": str(weights), "name": "walk.cxpolicy"}
        )
        assert stored["ok"] is True, stored

        written = client.request(
            "write_script",
            {"source": ROLLOUT_SCRIPT.replace("__SHA256__", container["sha256"]),
             "expected_revision": revision},
        )
        assert written["ok"] is True, json.dumps(written)[:2000]

        entry = written["display"]["play"]
        assert entry["artifact_kind"] == "assembly_simulation_json", entry
        shutil.copyfile(Path(entry["artifact_path"]), destination)
        trace = json.loads(destination.read_text(encoding="utf-8"))
        client.request("shutdown", timeout=60)
        return {
            "trace": str(destination),
            "schema": str(trace["schema"]),
            "frames": len(trace["frames"]),
            "components": list(trace["component_outputs"]),
            "policy_sha256": str(trace["policy"]["policy_sha256"]),
            "total_reward": float(trace["policy"]["total_reward"]),
        }
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# The shell half: bake it, in the bundle, through the add-on's own code.
# ---------------------------------------------------------------------------


def bake_trace(path: Path) -> dict:
    """Bake one rollout trace with ``cadex_animate`` and report keyframes.

    Uses the module's real functions -- ``read_trace`` validates the schema,
    ``curves_for_component`` does the millimetre and xyzw-to-wxyz work,
    ``_bake_object`` writes the F-Curves -- on real Blender objects. If a
    rollout trace were a dialect the shell could not read, it would fail
    here, which is the whole reason this file exists.
    """

    import bpy
    from mesh_agent import cadex_animate

    trace, sha = cadex_animate.read_trace(str(path))
    parameters = trace["parameters"]
    start = float(parameters["start_time_s"])
    fps = int(parameters["frames_per_second"])
    names = list(trace["component_outputs"])

    report = {"schema": str(trace["schema"]), "sha256": sha,
              "frames": len(trace["frames"]),
              "solver_frames": len(cadex_animate.solver_frames(trace["frames"])),
              "frame_range": list(cadex_animate.frame_range(trace)),
              "components": {}}

    for name in names:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
                         [], [(0, 1, 2)])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)

        curves = cadex_animate.curves_for_component(
            trace["frames"], name, start, fps
        )
        keyframes = cadex_animate._bake_object(obj, curves, sha)
        assert obj.rotation_mode == 'QUATERNION', name
        assert keyframes > 0, f"{name} baked no keyframes"
        assert len(cadex_animate.fcurves_of(obj)) == 7, name

        # It moves. A bake that produced seven flat curves would pass every
        # count above and play a still mechanism.
        sampled = []
        for frame in (1, report["frame_range"][1]):
            bpy.context.scene.frame_set(frame)
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            sampled.append(
                [round(float(value), 6) for value in evaluated.matrix_world.translation]
                + [round(float(value), 6) for value in
                   evaluated.matrix_world.to_quaternion()]
            )
        report["components"][name] = {
            "keyframes": keyframes,
            "first": sampled[0],
            "last": sampled[1],
            "moved": sampled[0] != sampled[1],
        }

    assert any(entry["moved"] for entry in report["components"].values()), (
        "every component sat still, so this trace bakes a photograph"
    )
    return report


def main(argv) -> int:
    try:
        import bpy  # noqa: F401
    except Exception:
        destination = Path(argv[1] if len(argv) > 1
                           else "/tmp/cadex-rollout-trace.json").resolve()
        print(json.dumps(write_trace(destination), sort_keys=True))
        return 0

    raw = os.environ.get("CADEX_ROLLOUT_TRACE", "").strip()
    if not raw:
        print("FAIL: set CADEX_ROLLOUT_TRACE to a trace this file wrote",
              file=sys.stderr)
        return 2
    print("CADEX-ROLLOUT-BAKE "
          + json.dumps(bake_trace(Path(raw)), sort_keys=True))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
