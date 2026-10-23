"""orun14 P1: where the gallop clip puts the hind paw's pad while it holds the heel down.

usage: pixi run python docs/probes/orun14/clip_pad.py RUN/train/gallop-task.json RUN/train/cat_model-model.xml

Sets the model to each of the bundle's clip samples and prints, for each hind
paw in the clip's stance: the lowest point of the heel's and the paw's
collision capsules above the ground (the ground is the height the generator
held the heel at, its first held sample), the metatarsus angle heel_pitch
reads (``_META``, world pitch + 63.9, flat at about +6 on v03), the pin's
toes-up angle, and the paw body's world pitch. A negative pad height is the
pad inside the floor: a stance no simulation can take.

Then the paw's level pitch: the paw body's world pitch at which its pad
(capsule 0) and toe (capsule 1) are at one height, interpolated over every
sample, against its pitch at the model's home keyframe. ADR-780's
``flat_feet`` holds the home pitch.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

LEGS = (("LH", 1, "c_heel_hl", "c_paw_hl", "c_meta_hl", "j_pawpin_l"),
        ("RH", -1, "c_heel_hr", "c_paw_hr", "c_meta_hr", "j_pawpin_r"))


def main(argv: list[str]) -> int:
    ref = json.loads(Path(argv[1]).read_text())["reference"]
    m = mujoco.MjModel.from_xml_path(argv[2])
    d = mujoco.MjData(m)
    bid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
    geoms = lambda n: [g for g in range(m.ngeom) if m.geom_bodyid[g] == bid(n)]

    def low(g):   # every hind paw and heel geom is a capsule
        r = d.geom_xmat[g].reshape(3, 3)
        return float(d.geom_xpos[g][2] - abs(r[2, 2]) * m.geom_size[g][1] - m.geom_size[g][0])

    def pitch(n):
        r = d.xmat[bid(n)].reshape(3, 3)
        return math.degrees(math.atan2(-r[2, 0], r[0, 0]))

    def pin(n):
        return math.degrees(d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)]])

    level = {leg: [] for leg, *_ in LEGS}
    print("sample | leg | heel held | heel / pad / toe mm above ground | _META | pin toes-up | paw pitch")
    for k, q in enumerate(ref["qpos"]):
        d.qpos[:] = q
        mujoco.mj_kinematics(m, d)
        for leg, s, heel, paw, meta, j in LEGS:
            pad, toe = (low(g) for g in geoms(paw)[:2])
            level[leg].append((pitch(paw), pad - toe))
            if not ref["contact"][leg][k]:
                continue
            held = ref["heels"][leg]["down"]
            k0 = held.index(1)
            d.qpos[:] = ref["qpos"][k0]
            mujoco.mj_kinematics(m, d)
            ground = min(low(g) for g in geoms(heel))
            d.qpos[:] = q
            mujoco.mj_kinematics(m, d)
            h = min(low(g) for g in geoms(heel))
            print(f"{k} | {leg} | {held[k]} | {1000 * (h - ground):+.1f} / {1000 * (pad - ground):+.1f} / "
                  f"{1000 * (toe - ground):+.1f} | {pitch(meta) + 63.9:+.1f} | {-s * pin(j):+.1f} | {pitch(paw):+.1f}")
    d.qpos[:] = m.key_qpos[0] if m.nkey else m.qpos0
    mujoco.mj_kinematics(m, d)
    for leg, _s, _h, paw, *_ in LEGS:
        pts = sorted(level[leg], key=lambda p: p[1])
        x = np.interp(0.0, [p[1] for p in pts], [p[0] for p in pts])
        print(f"{leg}: paw level (pad = toe) at world pitch {x:+.1f} deg; at home {pitch(paw):+.1f} deg")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
