"""orun17 B1: where the slow reference puts each hind paw, sample by sample, from late swing to toe-off.

usage: pixi run python docs/probes/orun17/slow_touchdown.py STRIDE.json MODEL_XML

STRIDE.json is a task copy whose ``reference`` is one stride, as
``docs/probes/orun16/sg_clip.py OUT_DIR`` writes it (``stride-K.json``). For
each hind leg, from two samples before the clip's touchdown to the sample
after its lift, it prints the clip's contact flag and held-heel flag and the
lowest point of the heel, the pad and the toe bulbs above the floor (mm, the
paw's lowest point at home, as ``sg_clip.py`` reads it), and the paw pin
(toes-up of the metatarsus, degrees). Writes nothing.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun16"))

import sg_clip  # noqa: E402
from sg_clip import body_geoms, lowest, mujoco  # noqa: E402


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    clip = json.loads(Path(argv[0]).read_text())["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_kinematics(model, data)
    floors = {paw: min(lowest(model, data, g) for g in body_geoms(model, paw)) for _, _, paw, _, _ in sg_clip.LEGS}
    n = clip["samples"]
    print(f"## {clip.get('label')}: {n} samples, {clip['parameters']['period_s'] * 1000 / n:.0f} ms a sample\n")
    for leg, side, paw, heel, sign in sg_clip.LEGS:
        if leg not in ("LH", "RH"):
            continue
        floor = floors[paw]
        geoms = sorted(body_geoms(model, paw), key=lambda g: model.geom_size[g][0])
        toe, pad, heel_g = geoms[0], geoms[-1], body_geoms(model, heel)
        pin = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "j_pawpin_" + side)]
        c = clip["contact"][leg]
        td = next(k for k in range(n) if c[k] and not c[k - 1])
        lift = next(k for k in range(td, td + n) if not c[k % n])
        print(f"### {leg}: touchdown at sample {td}, lift at {lift % n}\n")
        print("| sample | from touchdown | down | heel held | heel mm | pad mm | toe mm | pin deg |")
        print("|---|---|---|---|---|---|---|---|")
        for j in range(td - 2, lift + 1):
            k = j % n
            data.qpos[:] = clip["qpos"][k]
            mujoco.mj_kinematics(model, data)
            h = min(lowest(model, data, g) for g in heel_g) - floor
            print(f"| {k} | {j - td:+d} | {int(bool(c[k]))} | {int(bool(clip['heels'][leg]['down'][k]))} | {h:.1f} | "
                  f"{lowest(model, data, pad) - floor:.1f} | {lowest(model, data, toe) - floor:.1f} | "
                  f"{-sign * math.degrees(clip['qpos'][k][pin]):+.1f} |")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
