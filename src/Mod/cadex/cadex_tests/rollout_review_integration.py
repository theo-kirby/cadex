# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""M8's exit evidence, re-pointed at the UI that remains: the dashboard
reads a real rollout trace.

ADR-077 exists to prevent one failure -- *a trace the engine is happy with
and the UI declines to read*. A rollout is the third thing to produce an
``assembly_simulation_json``, so that failure is what M8 had to rule out.
Until ADR-495 the reader was the Blender shell's ``cadex_animate`` bake,
run inside the bundle. The shell is disabled, and the review dashboard
(``cli/cadex_cli/review_server.py``) is the one UI, so this file now hands
the engine's bytes to the dashboard's own trace reader instead.

Two halves, one process:

* it *writes* a rollout trace by driving a live ``cadexd`` through the whole
  chain -- mechanism, model, task, policy, rollout -- so the bytes being
  read are bytes the engine really produced;
* it *reads* that trace through ``review_server``'s real functions:
  ``_first_frame_placements`` (what the viewer places the model from) and
  ``_placement`` on every solver frame (what playback needs), and reports
  what it found.

Run it, after ``pixi run build-engine``::

    pixi run python src/Mod/cadex/cadex_tests/rollout_review_integration.py \\
        /tmp/rollout-trace.json
"""

from __future__ import annotations

import json
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
    dashboard has to be able to read is what the engine writes, and a fixture of
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

    root = Path(tempfile.mkdtemp(prefix="m8-review-"))
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
# The dashboard half: read it through the review server's own code.
# ---------------------------------------------------------------------------


def read_trace(path: Path) -> dict:
    """Read one rollout trace the way the dashboard does, and report it.

    If a rollout trace were a dialect the dashboard could not read -- a
    schema it does not accept, a placement block it rejects -- it would fail
    here, which is the whole reason this file exists.
    """

    repo = _HERE.parents[3]
    if str(repo / "cli") not in sys.path:
        sys.path.insert(0, str(repo / "cli"))
    from cadex_cli import review_server

    trace = json.loads(path.read_text(encoding="utf-8"))
    assert trace.get("schema") == review_server.TRACE_SCHEMA, trace.get("schema")
    placements, components = review_server._first_frame_placements(trace)
    assert components, "the dashboard found no components in the trace"
    missing = [name for name in components if name not in placements]
    assert not missing, f"no first-frame placement for {missing}"

    report = {"schema": str(trace["schema"]), "frames": len(trace["frames"]),
              "components": {}}
    for name in components:
        poses = []
        for index, frame in enumerate(trace["frames"]):
            entry = (frame.get("component_placements") or {}).get(name)
            if entry is None:
                continue
            block = review_server._placement(entry)
            assert block is not None, f"{name}: frame {index} is unreadable"
            poses.append(block["position_mm"] + block["rotation_xyzw"])
        assert poses, f"{name} has no readable pose in any frame"
        assert poses[0] == placements[name]["position_mm"] + placements[name]["rotation_xyzw"]
        report["components"][name] = {
            "poses": len(poses),
            "first": [round(value, 6) for value in poses[0]],
            "last": [round(value, 6) for value in poses[-1]],
            "moved": poses[0] != poses[-1],
        }

    # It moves. A trace whose every pose is the first would pass every check
    # above and play a still mechanism.
    assert any(entry["moved"] for entry in report["components"].values()), (
        "every component sat still, so this trace plays a photograph"
    )
    return report


def main(argv) -> int:
    destination = Path(argv[1] if len(argv) > 1
                       else "/tmp/cadex-rollout-trace.json").resolve()
    print("CADEX-ROLLOUT-WRITE " + json.dumps(write_trace(destination), sort_keys=True))
    print("CADEX-ROLLOUT-REVIEW "
          + json.dumps(read_trace(destination), sort_keys=True))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
