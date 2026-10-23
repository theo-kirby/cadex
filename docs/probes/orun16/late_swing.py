"""orun16 SG: the clip's heel through each hind's late swing and touchdown, against the policy's at the same clip phase.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/late_swing.py \
           SG_RUN/train/gallop_sg-task.json MODEL_XML EVALUATION_DIR [...]

sg-s7-25 at 1000 mm/s puts 0.97 of LH's and 0.79 of RH's heel-down frames in
early contact, before the clip's touchdown (``heel_gate.py``), where every
stance heel term pays nothing or pays the heel up. Is the heel down there
because the reference carries it down, or against it?

- **The clip**: for each stride of ``reference_schedule`` (sg0 slowest), per
  hind leg, at each sample from 6 before the clip's touchdown to 4 after it:
  the lowest point of the heel (``c_heel_h*``) and of the paw's collision
  geoms above the floor (the paw's lowest point in the home pose, which the
  generator takes as the ground), in mm, and the heel above the paw
  (heel minus paw: 0 is heel-flat, positive heel-up).
- **The policy**: each judged gallop_sg evaluation at its own command, every
  settled control frame binned by its offset in frames from the clip's
  touchdown of that paw (``hind_rhythm.py``'s clock and ``ref_*_down``):
  the share of frames the paw is down, the share of those with the heel
  down (``CadexEvaluation.STANCE_MM``), and the median heel and paw heights
  and heel minus paw, mm.

Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import hind_rhythm as HR  # noqa: E402
import sg_clip as SC  # noqa: E402

OFFSETS = range(-6, 5)
LEGS = (("LH", "l"), ("RH", "r"))


def clip_rows(model, stride):
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_kinematics(model, data)
    n = int(stride["samples"])
    out = {}
    for leg, side in LEGS:
        paw, heel = SC.body_geoms(model, "c_paw_h" + side), SC.body_geoms(model, "c_heel_h" + side)
        mujoco.mj_kinematics(model, data)
        contact = stride["contact"][leg]
        td = next(k for k in range(n) if contact[k] and not contact[k - 1])
        rows = {}
        for o in OFFSETS:
            data.qpos[:] = stride["qpos"][(td + o) % n]
            mujoco.mj_kinematics(model, data)
            rows[o] = (min(SC.lowest(model, data, g) for g in heel), min(SC.lowest(model, data, g) for g in paw))
        out[leg] = rows
    # Heights above the paw's lowest point at home.
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_kinematics(model, data)
    for leg, side in LEGS:
        floor = min(SC.lowest(model, data, g) for g in SC.body_geoms(model, "c_paw_h" + side))
        out[leg] = {o: (h - floor, p - floor) for o, (h, p) in out[leg].items()}
    return out


def policy_rows(model, tracking, out):
    E = HR.E
    geoms = HR.capsules(model)
    ev = json.loads((out / "evaluation.json").read_text())
    cmd, floor, heels = float(ev["judged_command_mm_s"]), ev["rig"]["floor_mm"], ev["rig"]["heels"]
    schedule = tracking["schedule"]
    i, w = HR.blend(schedule, cmd)
    turns = (1 - w) * schedule["turns_per_step"][i] + w * schedule["turns_per_step"][i + 1]
    k0 = min(range(len(schedule["speeds_mm_s"])), key=lambda k: (abs(schedule["speeds_mm_s"][k] - cmd), k))
    acc = {side: {o: [] for o in OFFSETS} for _, side in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        joints = [c["joint"] for c in trace["actuator_channels"]]
        solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
        _, s = HR.origin(model, tracking, k0, list(zip(joints, solver[0]["joint_positions"])))
        samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
        times = [t for t, _ in samples]
        settled = [n for n, t in enumerate(times) if t >= E.SETTLE_S - 1e-9]
        ref = {n: HR.ref_down(tracking, i, w, times[n] * 50.0 * turns + s / float(tracking["samples"]))
               for n in settled}
        for _, side in LEGS:
            paw = "c_paw_h" + side
            sole = E.foot_series(samples, paw, geoms[paw], floor)["height"]
            hb = heels[paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], floor)["height"]
            flags = [ref[n][side + "h"] for n in settled]
            tds = [j for j in range(1, len(settled)) if flags[j] and not flags[j - 1]]
            for td in tds:
                for o in OFFSETS:
                    j = td + o
                    if 0 <= j < len(settled):
                        n = settled[j]
                        acc[side][o].append((heel[n], sole[n]))
    return cmd, acc


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    task = json.loads(Path(argv[0]).read_text())
    model = mujoco.MjModel.from_xml_path(argv[1])
    print("## The clip: heel / paw / heel minus paw, mm, by samples from the clip's touchdown\n")
    print("| stride | leg | " + " | ".join("%+d" % o for o in OFFSETS) + " |")
    print("|---|---|" + "---|" * len(OFFSETS))
    for stride in task["reference_schedule"]:
        rows = clip_rows(model, stride)
        for leg, _ in LEGS:
            print("| %s | %s | " % (stride.get("label"), leg) + " | ".join(
                "%.0f / %.0f / %+.0f" % (h, p, h - p) for h, p in (rows[leg][o] for o in OFFSETS)) + " |")
    print("\n## The policy: paw-down share; heel-down share of paw-down; median heel / paw / heel minus paw mm\n")
    print("| evaluation | cmd | leg | " + " | ".join("%+d" % o for o in OFFSETS) + " |")
    print("|---|---|---|" + "---|" * len(OFFSETS))
    for arg in argv[2:]:
        cmd, acc = policy_rows(model, task["tracking"], Path(arg))
        for leg, side in LEGS:
            cells = []
            for o in OFFSETS:
                v = acc[side][o]
                down = [(h, p) for h, p in v if p <= HR.E.STANCE_MM]
                cells.append("%.2f; %.2f; %.0f / %.0f / %+.0f" % (
                    len(down) / max(len(v), 1), sum(1 for h, _ in down if h <= HR.E.STANCE_MM) / max(len(down), 1),
                    statistics.median(h for h, _ in v), statistics.median(p for _, p in v),
                    statistics.median(h - p for h, p in v)))
            print("| %s | %.0f | %s | " % (Path(arg).name, cmd, leg) + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
