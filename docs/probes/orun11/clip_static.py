"""orun11 M1: the static check, in the gait reference's own stance pose.

Usage: pixi run python docs/probes/orun11/clip_static.py MODEL.xml TASK.json

``foot_static.py`` stood the leg with the trunk level and the floor put under
the paw, which crouched the hip 70-84 mm below standing (ADR-776's evidence).
This reads the clip the task bundle trains on (ADR-777's plantigrade gallop)
and poses the exported model in it, sample by sample: the clip's ``qpos`` is
the whole pose, the base relative to the reset keyframe's. The floor is where
the generator put it, each foot's lowest collision point at the keyframe. For
each hind foot, at every stance sample and at push-off (the last stance
sample before toe-off), it reports:

* the sole's pitch from the floor (``foot_static.Leg.sole_pitch``: the common
  tangent under the pad and toe spheres, positive toes-down);
* the hock case's height over the floor (the bottom of its collision sphere);
* the rod's closure error, so the pose is the built linkage's.

M1 asks, at push-off, for the sole within 8 deg of the floor and the case
within 10 mm of it. No physics is stepped: this is the pose the clip asks the
policy to hold, standing on flat ground, not what a policy does.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from foot_static import Leg  # noqa: E402

FEET = {"LH": "l", "RH": "r"}


def clip_of(bundle):
    """The bundle's reference clip, wherever the task keeps it."""
    for path in (("reference",), ("task", "reference")):
        node = bundle
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and node.get("schema") == "cadex-gait-clip-v1":
            return node
    raise SystemExit("no cadex-gait-clip-v1 reference in the bundle")


def main(argv):
    model = mujoco.MjModel.from_xml_path(argv[0])
    clip = clip_of(json.loads(Path(argv[1]).read_text()))
    key = clip.get("reset_keyframe")
    k = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, key) if key else -1
    home = np.array(model.key_qpos[k] if k >= 0 else model.qpos0, dtype=float)
    print(f"clip {clip.get('label')!r}: {clip['samples']} samples, duty {clip['parameters']['duty_factor']}, "
          f"heels {sorted(clip.get('heels') or {})}, keyframe {key!r}")
    worst = {}
    for foot, side in FEET.items():
        leg = Leg(model, side)
        d = leg.d
        d.qpos[:] = home
        mujoco.mj_kinematics(model, d)
        ground = leg.floor_mm()          # the foot's lowest point standing at the keyframe
        contact = clip["contact"][foot]
        stance = [i for i, c in enumerate(contact) if c]
        push = [i for i in stance if not contact[(i + 1) % len(contact)]]
        rows = []
        for i in stance:
            q = np.array(clip["qpos"][i], dtype=float)
            q[:3] = home[:3] + q[:3]
            d.qpos[:] = q
            mujoco.mj_kinematics(model, d)
            closure = float(np.linalg.norm(leg.residual(d.qpos[leg.passive].copy())))
            c, r = leg.sphere(leg.case)
            case = (c[2] - r) * 1000.0 - ground
            # the floor is level, so the sole's pitch from it is its world pitch
            sole = leg.sole_pitch()
            heel = (clip.get("heels") or {}).get(foot, {}).get("down", [0] * len(contact))[i]
            rows.append((i, sole, case, closure, heel))
            print(f"  {foot} sample {i:2d}{' push-off' if i in push else '         '}: sole {sole:+6.1f} deg,"
                  f" hock case {case:6.1f} mm, closure {closure:.3f} mm, heel held {bool(heel)}")
        for i in push:
            row = next(r for r in rows if r[0] == i)
            ok = abs(row[1]) <= 8.0 and abs(row[2]) <= 10.0
            worst[foot] = (row, ok)
            print(f"  {foot} push-off (sample {i}): sole {row[1]:+.1f} deg (M1 within 8), "
                  f"hock case {row[2]:.1f} mm (M1 within 10): {'PASS' if ok else 'FAIL'}")
    return 0 if all(ok for _, ok in worst.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
