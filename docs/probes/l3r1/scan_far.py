"""ADR-821: ``height_scan_far`` resolves, states its grid and reads a hurdle, in the engine and the trainer alike.

usage: PYTHONPATH=training pixi run python docs/probes/l3r1/scan_far.py MJCF [BODY]

``MJCF`` is a built model (l3r1: leon III's ``cat_model-model.xml`` from any
of its run bundles), ``BODY`` the scanning body (default ``c_chest_frame``).
For both scan kinds it resolves the observation as a script declares it
(``_scan_observation``), writes the bundle's ``scans`` row
(``_scan_records``) and checks the row's grid against the kind's table and
the script API's suffixes. Then it stands the body on a course of one
200 mm hurdle, 100 mm deep, at each of several distances ahead, the body
turned 30 degrees, and reads both scans with the engine
(``height_scan_values``) and the trainer (``height_scan_vector`` in numpy).
The two must agree to 1e-6 mm and the hurdle must show at exactly the
points of each grid that lie on it. Prints one line per check and exits
non-zero on the first failure.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
import cadex_assembly_api as API  # noqa: E402
from cadex_train import height_scan_vector  # noqa: E402

HURDLE_MM = 200.0
DEPTH_MM = 100.0
HEIGHT_MM = 400.0
HEADING_DEG = 30.0


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def main() -> None:
    mjcf = Path(sys.argv[1])
    body = sys.argv[2] if len(sys.argv) > 2 else "c_chest_frame"
    mujoco = D._mujoco_module()
    model = mujoco.MjModel.from_xml_path(str(mjcf))
    bodies = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)]
    taken: dict[str, str] = {}
    records = [D._scan_observation({"kind": kind, "name": name, "component": body, "role": "policy"},
                                   bodies, taken)
               for kind, name in (("height_scan", "scan"), ("height_scan_far", "scan_far"))]
    rows = D._scan_records(records, model)
    for row in rows:
        grid = D.SCAN_OBSERVATION_KINDS[row["kind"]]["offsets_mm"]
        check([tuple(point) for point in row["offsets_mm"]] == [tuple(point) for point in grid]
              and len(row["channels"]) == len(grid),
              f"{row['kind']}: the bundle row states its own grid, {len(grid)} points")
        check(API._OBSERVATION_KINDS[row["kind"]] == "component_link"
              and API._OBSERVATION_SUFFIXES[row["kind"]] == D.SCAN_OBSERVATION_KINDS[row["kind"]]["suffixes"],
              f"{row['kind']}: the script API's suffixes are the engine's")
    far = D.HEIGHT_SCAN_FAR_OFFSETS_MM
    check(far[0] == (400.0, -150.0) and far[-1] == (1800.0, 150.0) and len(far) == 45,
          "height_scan_far: 400-1800 mm ahead by -150/0/+150 mm, 45 points")
    check(not set(far) & set(D.HEIGHT_SCAN_OFFSETS_MM), "the two grids share no point")

    turn = math.radians(HEADING_DEG)
    cos, sin = math.cos(turn), math.sin(turn)
    xmat = np.asarray([[cos, -sin, 0.0], [sin, cos, 0.0], [0.0, 0.0, 1.0]])
    for ahead in (250.0, 450.0, 1020.0, 1750.0, 2500.0):
        # The hurdle's near face is ``ahead`` mm along the heading, in the
        # body's frame; a wide box, so every lateral point sees it.
        box = {"shape": "block", "x_range_mm": [ahead, ahead + DEPTH_MM],
               "y_range_mm": [-1000.0, 1000.0], "top_mm": [HURDLE_MM, HURDLE_MM]}
        # The engine's box reader is axis-aligned, so the course is laid in
        # the body's frame and the body turned back by the same angle: the
        # world is rotated, the reading is not.
        terrain = {"kind": "boxes", "lowest_mm": 0.0, "boxes": [box], "domes": []}
        task = {"terrain": terrain, "scans": rows}
        xpos = np.zeros((model.nbody, 3))
        xpos[rows[0]["body_id"]] = [0.0, 0.0, HEIGHT_MM / 1000.0]
        mats = np.tile(np.eye(3).reshape(1, 9), (model.nbody, 1))
        mats[rows[0]["body_id"]] = np.eye(3).reshape(9)
        engine = D.height_scan_values(task, xpos, mats, None)
        trainer = height_scan_vector(np, task, xpos[None], mats[None])[0]
        channels = [channel for row in rows for channel in row["channels"]]
        check(np.allclose([engine[c] for c in channels], trainer, atol=1e-6),
              f"hurdle at {ahead:g} mm: engine and trainer agree on all {len(channels)} channels")
        for row in rows:
            want = [HEIGHT_MM - (HURDLE_MM if ahead <= a <= ahead + DEPTH_MM else 0.0)
                    for a, _left in row["offsets_mm"]]
            got = [engine[c] for c in row["channels"]]
            seen = sum(1 for value in got if value < HEIGHT_MM - 1.0)
            check(np.allclose(got, want, atol=1e-6),
                  f"hurdle at {ahead:g} mm: {row['name']} sees it at {seen} of {len(got)} points")
        # The same course turned with the body: the turned grid lands on the
        # turned box. A wide box turned is a stone, which the readers turn exactly.
        centre = [ahead + DEPTH_MM / 2.0, 0.0, HURDLE_MM / 2.0]
        stone = {"shape": "stone",
                 "centre_mm": [cos * centre[0], sin * centre[0], centre[2]],
                 "quat": [math.cos(turn / 2.0), 0.0, 0.0, math.sin(turn / 2.0)],
                 "half_mm": [DEPTH_MM / 2.0, 1000.0, HURDLE_MM / 2.0]}
        turned = {"terrain": {"kind": "boxes", "lowest_mm": 0.0, "boxes": [stone], "domes": []},
                  "scans": rows}
        mats[rows[0]["body_id"]] = xmat.reshape(9)
        engine_turned = D.height_scan_values(turned, xpos, mats, None)
        trainer_turned = height_scan_vector(np, turned, xpos[None], mats[None])[0]
        check(np.allclose([engine_turned[c] for c in channels], trainer_turned, atol=1e-6)
              and np.allclose([engine_turned[c] for c in channels],
                              [engine[c] for c in channels], atol=1e-6),
              f"hurdle at {ahead:g} mm, body and course turned {HEADING_DEG:g} deg: the same reading")


if __name__ == "__main__":
    main()
