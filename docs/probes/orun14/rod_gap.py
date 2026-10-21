"""orun14 O9: the push-rod loops' gap frame by frame, not only its maximum.

usage: pixi run python docs/probes/orun14/rod_gap.py MODEL_XML EVAL_DIR [EVAL_DIR ...]

``orun11/judge.py``'s ``closure`` block gives each connect row's median and
maximum over every seed's window (from 1 s). O9 asks the loops closed within
2 mm. This reads the same gap per frame and gives, per row: p99, p99.9, the
maximum, the frames and seeds over 2 mm, and, on those frames, the median
share of peak torque the leg's wrist (front) or hock (hind) drive is using,
so a gap can be told apart as a drive pushing the rod or an impact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

LIMIT_MM = 2.0
DRIVE = {"j_frodbot_l": "j_wrist_l", "j_frodbot_r": "j_wrist_r",
         "j_rodbot_l": "j_hock_l", "j_rodbot_r": "j_hock_r"}


def gaps(model, trace: dict, warmup_s: float = 1.0):
    import mujoco

    body = lambda i: mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(i))

    def anchor(placements, b, local_m):
        p = placements[body(b)]
        x, y, z, w = p["rotation_xyzw"]
        m = np.zeros(9)
        mujoco.mju_quat2Mat(m, np.array([w, x, y, z], dtype=float))
        return np.asarray(p["position_mm"]) + m.reshape(3, 3) @ (1000.0 * np.asarray(local_m))

    channels = [c["joint"] for c in trace["actuator_channels"]]
    peaks = [c["effort_high"] for c in trace["actuator_channels"]]
    rows = {}
    for i in range(model.neq):
        if int(model.eq_type[i]) != int(mujoco.mjtEq.mjEQ_CONNECT):
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_EQUALITY, i) or f"eq{i}"
        rows[name] = (i, [], [])
    for frame in trace["frames"]:
        t = frame.get("nominal_time_s")
        if t is None or t < warmup_s:
            continue
        pl = frame["component_placements"]
        for name, (i, values, load) in rows.items():
            if int(model.eq_objtype[i]) == int(mujoco.mjtObj.mjOBJ_SITE):
                s1, s2 = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
                a = anchor(pl, model.site_bodyid[s1], model.site_pos[s1])
                b = anchor(pl, model.site_bodyid[s2], model.site_pos[s2])
            else:
                a = anchor(pl, model.eq_obj1id[i], model.eq_data[i][0:3])
                b = anchor(pl, model.eq_obj2id[i], model.eq_data[i][3:6])
            values.append(float(np.linalg.norm(a - b)))
            drive = DRIVE.get(name)
            if drive in channels:
                k = channels.index(drive)
                load.append(abs(frame["actuator_efforts"][k]) / peaks[k])
            else:
                load.append(float("nan"))
    return {name: (np.array(v), np.array(l)) for name, (_, v, l) in rows.items()}


def main(argv: list[str]) -> int:
    import mujoco

    model = mujoco.MjModel.from_xml_path(argv[1])
    for ev in argv[2:]:
        per = {}
        for path in sorted(Path(ev).glob("seed-*-trace.json")):
            seed = path.name.split("-")[1]
            for name, (v, l) in gaps(model, json.loads(path.read_text())).items():
                per.setdefault(name, []).append((seed, v, l))
        print(f"== {Path(ev).name}")
        print("row | frames | median | p99 | p99.9 | max mm | frames > 2 mm | seeds > 2 mm | drive load on those (median share of peak) | drive load all frames")
        for name, items in per.items():
            v = np.concatenate([x[1] for x in items])
            l = np.concatenate([x[2] for x in items])
            over = v > LIMIT_MM
            seeds = [s for s, x, _ in items if (x > LIMIT_MM).any()]
            lo = f"{np.nanmedian(l[over]):.2f}" if over.any() else "-"
            print(f"{name} | {v.size} | {np.median(v):.2f} | {np.percentile(v, 99):.2f} | "
                  f"{np.percentile(v, 99.9):.2f} | {v.max():.2f} | {int(over.sum())} | "
                  f"{','.join(seeds) or '-'} | {lo} | {np.nanmedian(l):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
