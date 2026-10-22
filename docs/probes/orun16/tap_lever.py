"""orun16 RL (O7): what a hind's mid-swing tap earns under sg-s7's terms, and two stronger levers scored on it.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/tap_lever.py \
           SINGLE_SPEED_RUN/train/gallop-task.json SG_RUN/train/gallop_sg-task.json \
           MODEL_XML EVALUATION_DIR [...]

sg-s6 (``hind_scuff`` w -8) cut LH's taps at 1.0 m/s from 0.88 to 0.64 a clip
stride in 25 iterations; the 1000 hind lag still reads 30 ms. sg-s7 gates
``heel_sched`` on the paw's own contact, so a tap on the toes at 1.0 m/s now
earns the slow end's heel-up pay. This reads each judged gallop_sg
evaluation at its own command, every settled control frame (``hind_rhythm.py``'s
clip clock, ``heel_gate.py``'s metatarsus pitch), finds each hind's taps (a
touchdown in contact for at most 40 ms) and, summed over each tap's frames,
what three of the task's terms make of it against the same frames in the air:

- ``track_contact`` (w 10, four paws): a paw down where the clip has it up
  costs 10 / 4 a step;
- ``heel_sched`` gated on contact (sg-s7: w 6, D 30, W 30): a paw down pays
  6 * tent(meta, T(cmd), 30) / 2 a step;
- ``hind_scuff`` (``(chl_down * g(ref_lh_lift) + ...) / 2``,
  ``g = sat01((lift - 10) / 20)``) at w -8 (sg-s6, sg-s7) and w -16;

and the net a tap, per leg, at each weight. Then a **tap reset**: a
termination on ``chl_down * g(ref_lh_lift) + chr_down * g(ref_rh_lift)``
above 0.99 (a paw down where the clip has it 30 mm or more up): on each
seed, the time it would first fire after the settle, the share of seeds it
would end, and the share of its firing frames that fall on taps (the rest
are landings or lifts it would also punish).

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

D, W = 30.0, 30.0
CONTACT_W, HEEL_W = 10.0, 6.0
SCUFF_WS = (-8.0, -16.0)
RESET_AT = 0.99


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
    print("| evaluation | cmd | leg | taps a clip stride | frames a tap | track_contact a tap | heel_sched (contact) a tap "
          "| hind_scuff a tap w -8 / w -16 | net a tap w -8 / w -16 "
          "| reset: seeds ended; median first fire s; share of firing frames on taps |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for arg in argv[3:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd = float(ev["judged_command_mm_s"])
        floor = ev["rig"]["floor_mm"]
        t_meta = HS.target(cmd, D)
        i, w = HR.blend(schedule, cmd)
        turns = (1 - w) * schedule["turns_per_step"][i] + w * schedule["turns_per_step"][i + 1]
        hz = turns * 50.0
        k0 = min(range(len(schedule["speeds_mm_s"])), key=lambda k: (abs(schedule["speeds_mm_s"][k] - cmd), k))
        acc = {side: {"taps": [], "frames": []} for side in "lr"}
        strides, fires, ended, fire_frames, fire_on_taps = 0.0, [], 0, 0, 0
        seeds = sorted(out.glob("seed-*-trace.json"))
        for path in seeds:
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, s = HR.origin(model, tracking, k0, list(zip(joints, solver[0]["joint_positions"])))
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            settled = [n for n, t in enumerate(times) if t >= E.SETTLE_S - 1e-9]
            phase = {n: times[n] * 50.0 * turns + s / float(tracking["samples"]) for n in settled}
            ref = {n: HR.ref_down(tracking, i, w, phase[n]) for n in settled}
            lift = {n: HR.ref_down(tracking, i, w, phase[n], "lift") for n in settled}
            strides += (times[settled[-1]] - times[settled[0]]) * hz
            gate = {n: 0.0 for n in settled}
            on_tap = set()
            for side in "lr":
                key, paw = side + "h", "c_paw_h" + side
                down = [h <= E.STANCE_MM for h in E.foot_series(samples, paw, geoms[paw], floor)["height"]]
                for n in settled:
                    if down[n]:
                        gate[n] += HR.scuff_gate(lift[n][key])
                n = settled[0]
                while n <= settled[-1]:
                    if not down[n] or (n > 0 and down[n - 1]):
                        n += 1
                        continue
                    m = n
                    while m + 1 < len(times) and down[m + 1]:
                        m += 1
                    if 1000 * (times[m] - times[n] + 0.02) <= HR.TAP_MS + 1e-6:
                        tc = hs = sc = 0.0
                        for q in range(n, m + 1):
                            on_tap.add(q)
                            tc += -CONTACT_W / 4 * (1 - 2 * ref[q][key]) if q in ref else 0.0
                            rot, _ = HS.E._pose(samples[q][1], "c_meta_h" + side)
                            meta = HS.H.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0]
                            hs += HEEL_W * HS.tent(meta, t_meta, W) / 2
                            sc += HR.scuff_gate(lift[q][key]) / 2
                        acc[side]["taps"].append((tc, hs, sc))
                        acc[side]["frames"].append(m - n + 1)
                    n = m + 1
            first = [n for n in settled if gate[n] >= RESET_AT]
            fire_frames += len(first)
            fire_on_taps += sum(1 for n in first if n in on_tap)
            if first:
                ended += 1
                fires.append(times[first[0]])
        for side in "lr":
            taps = acc[side]["taps"]
            if not taps:
                cells = ["0.00", "–", "–", "–", "–", "–"]
            else:
                tc = statistics.fmean(t[0] for t in taps)
                hs = statistics.fmean(t[1] for t in taps)
                sc = statistics.fmean(t[2] for t in taps)
                cells = ["%.2f" % (len(taps) / strides), "%.1f" % statistics.fmean(acc[side]["frames"]),
                         "%+.2f" % tc, "%+.2f" % hs,
                         " / ".join("%+.2f" % (wt * sc) for wt in SCUFF_WS),
                         " / ".join("%+.2f" % (tc + hs + wt * sc) for wt in SCUFF_WS)]
            reset = "%d/%d; %s; %s" % (ended, len(seeds), ("%.2f" % statistics.median(fires)) if fires else "–",
                                       ("%.2f" % (fire_on_taps / fire_frames)) if fire_frames else "–")
            print("| %s | %.0f | %sH | %s | %s |" % (out.name, cmd, side.upper(), " | ".join(cells),
                                                     reset if side == "l" else "″"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
