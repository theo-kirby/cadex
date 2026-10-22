"""orun16 SG (O7): where each hind's heel-down frames fall against the clip's stance, and heel_sched gated on paw contact scored per step.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/heel_gate.py \
           SINGLE_SPEED_RUN/train/gallop-task.json SG_RUN/train/gallop_sg-task.json \
           MODEL_XML EVALUATION_DIR [...]

sg-s5-25 scheduled LH's heel (0.06 -> 0.26 from 1000 to 2400 mm/s) but not
RH's (0.39 -> 0.29), though ``heel_sched.py`` scored the same pay contrast on
both. That probe took paw-down frames for the clip's stance; the task gates
``heel_sched`` on ``ref_*_down``, and RH lands about 0.15 of a stride before
the clip's touchdown (``hind_rhythm.py``). This reads each judged gallop_sg
evaluation at its own command, every settled control frame, with
``hind_rhythm.py``'s clip clock and ``heel_sched.py``'s metatarsus pitch
(``_META``, calibrated on the first argument, a single-speed gallop bundle):

- per hind leg, the paw-down frames split heel down / heel up, and each split
  by the clip's flag: **in** the clip's stance, **early** (clip swing,
  nearer its next touchdown than its last lift) or **late** (clip swing,
  nearer its last lift);
- ``heel_sched`` (D 30, W 30, w 6) per step as built, gated on
  ``ref_*_down``, and the candidate gated on the paw's own contact
  (``chl_down`` / ``chr_down``, the ``c_paw_h*`` contact channels already in
  the bundle): the mean pay a step on heel-down and heel-up paw-down frames,
  and their contrast (heel-up minus heel-down; positive pushes the heel up).

Writes nothing.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import heel_sched as HS  # noqa: E402
import hind_rhythm as HR  # noqa: E402

D, W, WT = 30.0, 30.0, 6.0


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    cal = HS.H.calibrate(Path(argv[0]))
    tracking = json.loads(Path(argv[1]).read_text())["tracking"]
    schedule = tracking["schedule"]
    model = mujoco.MjModel.from_xml_path(argv[2])
    geoms = HR.capsules(model)
    E = HR.E
    print("| evaluation | cmd | leg | paw-down frames | heel-down share | heel-down frames in / early / late "
          "| heel-up frames in / early / late | heel_sched (ref gate) a step: heel down / heel up; contrast "
          "| contact gate: heel down / heel up; contrast |")
    print("|---|---|---|---|---|---|---|---|---|")
    for arg in argv[3:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd = float(ev["judged_command_mm_s"])
        floor = ev["rig"]["floor_mm"]
        heels = ev["rig"]["heels"]
        t_meta = HS.target(cmd, D)
        i, w = HR.blend(schedule, cmd)
        turns = (1 - w) * schedule["turns_per_step"][i] + w * schedule["turns_per_step"][i + 1]
        k0 = min(range(len(schedule["speeds_mm_s"])), key=lambda k: (abs(schedule["speeds_mm_s"][k] - cmd), k))
        acc = {side: {"heel": {"in": 0, "early": 0, "late": 0}, "up": {"in": 0, "early": 0, "late": 0},
                      "ref": {"heel": [], "up": []}, "con": {"heel": [], "up": []}} for side in "lr"}
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
            for side in "lr":
                key, paw = side + "h", "c_paw_h" + side
                a = acc[side]
                sole = E.foot_series(samples, paw, geoms[paw], floor)["height"]
                hb = heels[paw]
                heel = E.foot_series(samples, hb["body"], hb["geoms"], floor)["height"]
                flags = [ref[n][key] for n in settled]
                # Each settled frame's distance to the clip's last lift and next touchdown, in frames.
                last_lift, next_td = [None] * len(settled), [None] * len(settled)
                for j in range(1, len(settled)):
                    last_lift[j] = j if (flags[j - 1] and not flags[j]) else last_lift[j - 1]
                for j in range(len(settled) - 2, -1, -1):
                    next_td[j] = j + 1 if (flags[j + 1] and not flags[j]) else next_td[j + 1]
                for j, n in enumerate(settled):
                    if sole[n] > E.STANCE_MM:
                        continue
                    split = "heel" if heel[n] <= E.STANCE_MM else "up"
                    if flags[j]:
                        where = "in"
                    else:
                        d_lift = j - last_lift[j] if last_lift[j] is not None else 10 ** 6
                        d_td = next_td[j] - j if next_td[j] is not None else 10 ** 6
                        where = "early" if d_td < d_lift else "late"
                    a[split][where] += 1
                    rot, _ = HS.E._pose(samples[n][1], "c_meta_h" + side)
                    m = HS.H.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0]
                    pay = WT * HS.tent(m, t_meta, W) / 2
                    a["ref"][split].append(pay * flags[j])
                    a["con"][split].append(pay)

        def cell(d):
            hd = statistics.fmean(d["heel"]) if d["heel"] else 0.0
            hu = statistics.fmean(d["up"]) if d["up"] else 0.0
            return "%.2f / %.2f; %+.2f" % (hd, hu, hu - hd)

        for side, a in acc.items():
            nh, nu = sum(a["heel"].values()), sum(a["up"].values())
            print("| %s | %.0f | %sH | %d | %.2f | %s | %s | %s | %s |" % (
                out.name, cmd, side.upper(), nh + nu, nh / max(nh + nu, 1),
                " / ".join("%.2f" % (a["heel"][k] / max(nh, 1)) for k in ("in", "early", "late")),
                " / ".join("%.2f" % (a["up"][k] / max(nu, 1)) for k in ("in", "early", "late")),
                cell(a["ref"]), cell(a["con"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
