"""orun16 Q2: what the front push-rod loop fights when it opens past 2 mm, solver step by solver step.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/rod_fight.py \
           MODEL_XML JUDGED_TASK_JSON POLICY SEED [SEED ...]

``rod_solver.py`` showed neither stiffer carpus/wrist stops nor more solver
iterations close the front loops, and the loop's own regulariser
((1 - dmax)/dmax x the bodies' ``invweight0``) gives micrometres, not
millimetres, at the wrist drive's peak rod force. So this plays the engine's
own judge (``evaluate_success``) on the unpatched model with ``mj_step``
wrapped: after every solver step it reads each front loop's gap from the
site positions, and on every step over 2 mm it tallies the loop's own
constraint rows (force, separation speed, regulariser R, and the quasi-static
gap f.R/k those imply) and what else holds the fore leg then -- the wrist drive's force as a share of its range, the
carpus and wrist against their stops, every contact on the paw, claws, rod
or crank with what it touches, and the loop's own constraint force -- and
the share of those steps by fore stance (paw or claws on the floor).
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402

LIMIT_M = 0.002
SIDES = {"l": "fl", "r": "fr"}


def main(argv: list[str]) -> int:
    model_path, task_path, policy_path = map(Path, argv[1:4])
    seeds = [int(s) for s in argv[4:]]
    xml = model_path.read_text()
    task = json.loads(task_path.read_text())
    task["success"]["seeds"] = seeds
    container = D.decode_policy(policy_path.read_bytes(), context="rod_fight")
    components = re.findall(r'<body[^>]*name="([^"]+)"', xml)
    tally = {s: collections.Counter() for s in SIDES}
    gaps = {s: [] for s in SIDES}
    steps = collections.Counter()
    real_step = mujoco.mj_step

    def step(model, data, *args):
        real_step(model, data, *args)
        name = lambda kind, i: mujoco.mj_id2name(model, kind, int(i)) or str(i)
        if data.time < 1.0:
            return
        for side, leg in SIDES.items():
            eq = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, f"j_frodbot_{side}")
            s1, s2 = int(model.eq_obj1id[eq]), int(model.eq_obj2id[eq])
            gap = float(np.linalg.norm(data.site_xpos[s1] - data.site_xpos[s2]))
            steps[side] += 1
            if gap <= LIMIT_M:
                continue
            gaps[side].append(gap)
            t = tally[side]
            t["steps"] += 1
            act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"j_wrist_{side}/position")
            share = abs(float(data.actuator_force[act])) / float(model.actuator_forcerange[act][1])
            t["wrist drive >= 0.95 of range"] += share >= 0.95
            for joint in (f"j_carpus_{side}", f"j_wrist_{side}"):
                j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
                q = float(data.qpos[model.jnt_qposadr[j]])
                lo, hi = model.jnt_range[j]
                t[f"{joint} past a stop"] += q < lo or q > hi
            bodies = {f"c_paw_{leg}", f"c_claws_{leg}", f"c_rod_{leg}", f"c_crank_{leg}"}
            stance = False
            for c in data.contact[: data.ncon]:
                b1 = name(mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[c.geom1])
                b2 = name(mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[c.geom2])
                for mine, other in ((b1, b2), (b2, b1)):
                    if mine in bodies:
                        other = "floor" if other == "world" else other
                        t[f"contact {mine} x {other}"] += 1
                        stance |= other == "floor"
            t["fore stance"] += stance
            rows = [i for i in range(data.nefc)
                    if int(data.efc_type[i]) == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)
                    and int(data.efc_id[i]) == eq]
            t["loop force N (sum)"] += float(np.linalg.norm(data.efc_force[rows]))
            t["loop speed m/s (sum)"] += float(np.linalg.norm(data.efc_vel[rows]))
            t["loop R (sum)"] += float(np.mean(data.efc_R[rows]))
            t["loop static gap mm (sum)"] += float(
                np.linalg.norm(data.efc_force[rows] * data.efc_R[rows] / data.efc_KBIP[rows, 0])) * 1000.0

    mujoco.mj_step = step
    D.evaluate_success(xml.encode(), task, container, components=components,
                       context="rod_fight")
    mujoco.mj_step = real_step
    for side in SIDES:
        t = tally[side]
        n = max(t["steps"], 1)
        g = np.array(gaps[side]) * 1000.0 if gaps[side] else np.zeros(1)
        print(f"== j_frodbot_{side}: {t['steps']} of {steps[side]} solver steps over 2 mm "
              f"(max {g.max():.2f} mm, median over {np.median(g):.2f} mm)")
        print(f"  mean loop force on those steps: {t['loop force N (sum)'] / n:.0f} N; "
              f"separation speed {t['loop speed m/s (sum)'] / n:.3f} m/s; R {t['loop R (sum)'] / n:.2e}; "
              f"static gap f.R/k {t['loop static gap mm (sum)'] / n:.3f} mm")
        for key, value in sorted(t.items(), key=lambda kv: -kv[1]):
            if not key.startswith(("steps", "loop ")):
                print(f"  {key}: {value / n:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
