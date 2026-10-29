# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""T2: the Go1 go-to-point actor given a height scan (ADR-859).

Run from ~/cadex-train-venv:

    python docs/probes/orun21/t2_scan.py bundle SOURCE OUT

``SOURCE`` is ``t2_around.py``'s bundle directory (``go1-levels-task.json``
and its model). ``OUT`` gets the same model and the same task with one
``scans`` row: a ``height_scan`` on the trunk, ``role: policy``, on the
engine's grid (``CadexDynamics.SCAN_OBSERVATION_KINDS``), in the form
``CadexDynamics._scan_records`` writes. Nothing else moves, so a policy
trained on SOURCE warm-starts it across ``--init-from-task-change``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

BODY = "trunk"


def bundle(source: Path, out: Path) -> None:
    import mujoco

    task = json.loads((source / "go1-levels-task.json").read_text())
    model_path = source / task["model"]["path"]
    model = mujoco.MjModel.from_xml_path(str(model_path))
    kind = CadexDynamics.SCAN_OBSERVATION_KINDS["height_scan"]
    task["scans"] = [{
        "name": "hs", "kind": "height_scan", "target": BODY, "body": BODY,
        "body_id": int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, BODY)),
        "offsets_mm": [[float(a), float(b)] for a, b in kind["offsets_mm"]],
        "channels": [f"hs{suffix}" for suffix in kind["suffixes"]],
        "unit": "mm", "scale": 1000.0, "role": "policy",
    }]
    task["label"] = "go1 go-to-point on the pool round the start, the actor reading a height scan (orun21 T2, ADR-859)"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(model_path, out / model_path.name)
    (out / "go1-scan-task.json").write_text(json.dumps(task, indent=1))
    print(json.dumps({"body_id": task["scans"][0]["body_id"],
                      "channels": len(task["scans"][0]["channels"])}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("verb", choices=("bundle",))
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    bundle(args.source, args.out)


if __name__ == "__main__":
    main()
