"""orun16 SG (O7): the hock's error against the clip through each hind's late swing, and a slow-gated landing term scored per step.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/hock_land.py \
           SG_RUN/train/gallop_sg-task.json MODEL_XML EVALUATION_DIR [...]

``late_swing.py`` shows the clip carrying the slow heel 25-38 mm above the
paw through late swing and touchdown, and sg-s7-25 swinging it 9-22 mm
below the paw and landing heel-first. The only term on the hock in swing is
``track_pose``, one exp over 19 joints at 900 deg^2 each (a 30 deg hock miss
costs 0.05 of its w 1.5). This reads each judged gallop_sg evaluation at
its own command, with ``hind_rhythm.py``'s clip clock:

- per hind leg and offset in frames from the clip's touchdown (-6..+4): the
  median hock angle (``j_hock_*``, the trace's degrees, which the task's
  ``q_hock_*`` reads) minus the clip's blended ``q_ankle_*_ref``;
- the candidate ``hock_land``, per step:

      sat01((2400 - cmd) / 1400) * sum over hinds of
          (1 - ref_h_down) * sat01((30 - ref_h_lift) / 15) * tent(q_hock - q_ankle_ref, W) / 2

  which tracks the clip's hock where the clip has the paw in swing within
  30 mm of the floor (full under 15 mm), at the slow end of the command
  only (nothing at 2400, where the heel should come down); W is 60 deg
  (``HOCK_LAND_W`` to change it: at 20 it pays almost nothing on a 50 deg
  miss). Reported: its
  gate's mean a step, its mean pay a step, and what the clip's own hock
  would be paid (the gate), so the gap times the weight is what the term
  hands the policy for landing as the clip does.

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
import hind_rhythm as HR  # noqa: E402

OFFSETS = range(-6, 5)
W = float(__import__("os").environ.get("HOCK_LAND_W", "60"))


def channel(tracking, i, w, phase, name):
    rows = int(tracking["samples"])
    c = tracking["channels"][2:].index(name)
    at = (phase % 1.0) * rows
    low = int(at) % rows
    high, f = (low + 1) % rows, at - int(at)
    val = 0.0
    for table, share in ((tracking["schedule"]["tables"][i], 1 - w), (tracking["schedule"]["tables"][i + 1], w)):
        val += share * (table[low][c] + f * (table[high][c] - table[low][c]))
    return val


def sat01(x):
    return min(1.0, max(0.0, x))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    tracking = json.loads(Path(argv[0]).read_text())["tracking"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    E = HR.E
    print("| evaluation | cmd | leg | hock - clip deg, median by frames from the clip's touchdown "
          + " | ".join("%+d" % o for o in OFFSETS) + " | gate a step | hock_land a step | clip's own |")
    print("|---|---|---|" + "---|" * len(OFFSETS) + "---|---|---|")
    for arg in argv[2:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd = float(ev["judged_command_mm_s"])
        speed_gate = sat01((2400.0 - cmd) / 1400.0)
        schedule = tracking["schedule"]
        i, w = HR.blend(schedule, cmd)
        turns = (1 - w) * schedule["turns_per_step"][i] + w * schedule["turns_per_step"][i + 1]
        k0 = min(range(len(schedule["speeds_mm_s"])), key=lambda k: (abs(schedule["speeds_mm_s"][k] - cmd), k))
        err = {s: {o: [] for o in OFFSETS} for s in "lr"}
        gate_sum = {s: [] for s in "lr"}
        pay_sum = {s: [] for s in "lr"}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, s0 = HR.origin(model, tracking, k0, list(zip(joints, solver[0]["joint_positions"])))
            settled = [f for f in solver if f["nominal_time_s"] >= E.SETTLE_S - 1e-9]
            for side in "lr":
                hock = joints.index("j_hock_" + side)
                flags, e = [], []
                for f in settled:
                    phase = f["nominal_time_s"] * 50.0 * turns + s0 / float(tracking["samples"])
                    down = HR.ref_down(tracking, i, w, phase)[side + "h"]
                    lift = channel(tracking, i, w, phase, "ref_%sh_lift" % side)
                    d = f["joint_positions"][hock] - channel(tracking, i, w, phase, "q_ankle_%s_ref" % side)
                    g = speed_gate * (1.0 - down) * sat01((30.0 - lift) / 15.0)
                    gate_sum[side].append(g / 2)
                    pay_sum[side].append(g * max(0.0, 1.0 - abs(d) / W) / 2)
                    flags.append(down)
                    e.append(d)
                for td in (j for j in range(1, len(flags)) if flags[j] and not flags[j - 1]):
                    for o in OFFSETS:
                        if 0 <= td + o < len(e):
                            err[side][o].append(e[td + o])
        for side in "lr":
            print("| %s | %.0f | %sH | " % (out.name, cmd, side.upper()) + " | ".join(
                "%+.0f" % statistics.median(err[side][o]) for o in OFFSETS) + " | %.3f | %.3f | %.3f |" % (
                statistics.fmean(gate_sum[side]), statistics.fmean(pay_sum[side]), statistics.fmean(gate_sum[side])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
