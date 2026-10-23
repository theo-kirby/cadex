"""List the gallop strides of AI4Animation dog takes, with speed and footfall phases (orun18 C3).

usage: pixi run python docs/probes/orun18/stride_scan.py BVH [BVH ...]

Each stride runs from a left-hind touchdown to the next. A paw is down when it
is within ``retarget.CONTACT_M`` of the floor and moving at under
``retarget.CONTACT_SPEED`` of the pelvis's speed (no gap closing, so it is a
finder: the stride ``retarget.py`` takes is then measured there). Printed per
stride over 1.8 m/s: frames, the dog's speed, each foot's first touchdown
phase (``-`` when none was seen) and the share of frames with no paw down.
The takes are CC BY-NC 4.0 (SOURCES.md) and stay in ``~/mocap/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import retarget as R  # noqa: E402


def scan(path: Path) -> None:
    joints, motion, dt = R.read_bvh(path)
    pos, _ = R.forward_kinematics(joints, motion)
    pos = pos / 100.0
    ix = {j["name"]: n for n, j in enumerate(joints)}
    paw = {k: pos[:, ix[n]] for k, n in R.DOG_PAW.items()}
    floor = np.percentile(np.concatenate([v[:, 1] for v in paw.values()]), 2)
    hips = pos[:, ix["Hips"]]
    speed = np.linalg.norm(np.gradient(hips[:, [0, 2]], dt, axis=0), axis=1)
    down = {}
    for k, v in paw.items():
        paw_speed = np.linalg.norm(np.gradient(v[:, [0, 2]], dt, axis=0), axis=1)
        down[k] = (v[:, 1] - floor < R.CONTACT_M) & (paw_speed < R.CONTACT_SPEED * np.maximum(speed, 0.3))
    touch = {k: [f for f in range(1, len(motion)) if d[f] and not d[f - 1]] for k, d in down.items()}
    print(f"{path.name}: {len(motion)} frames")
    lh = touch["LH"]
    for a, b in zip(lh, lh[1:]):
        if not 10 <= b - a <= 60:
            continue
        v = np.linalg.norm(hips[b, [0, 2]] - hips[a, [0, 2]]) / ((b - a) * dt)
        if v <= 1.8:
            continue
        phases = []
        for k in ("LH", "LF", "RF", "RH"):
            seen = [(f - a) / (b - a) for f in touch[k] if a <= f < b]
            phases.append(f"{k} {min(seen):.2f}" if seen else f"{k} -")
        flight = np.mean([not any(down[k][f] for k in down) for f in range(a, b)])
        print(f"  {a}-{b}  {v:.2f} m/s  " + "  ".join(phases) + f"  flight {flight:.2f}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        scan(Path(arg))
