"""orun16 RL (O7): why the hinds at 1.0 m/s run on two rhythms, and a swing-contact term scored per step.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/hind_rhythm.py \
           RUN/train/gallop_sg-task.json MODEL_XML EVALUATION_DIR [...]

sg-s4-25 at 1000 mm/s lands LH at 3.33 Hz and RH at 2.11 (stride 357 / 653
mm, ``legs.py``) against the clip's 2.0 Hz. This reads each judged gallop_sg
evaluation at its own held command (``judged_command_mm_s``), every control
frame from the engine's settle on:

- **the clip's clock**, by the bundle's ``tracking.schedule`` rule at the
  held command: the blend weight between the two strides round it, the
  clock turning the blended ``turns_per_step`` a step, the origin sample
  recovered from the first solver frame against that stride's
  ``reset_qpos`` rows (``orun15/lag_term.py``'s fit), and each paw's
  ``ref_*_down`` from the blended table, held at one half;
- **each paw's contact**, by the evaluator's stance rule
  (``CadexEvaluation.STANCE_MM`` on the paw's collision geoms);
- **per hind leg:** touchdowns per clip stride; each touchdown's phase
  after the clip's own touchdown of that paw (0 on time, 0.9 a tenth of a
  stride early), binned in tenths, with the median contact time of the
  touchdowns in each bin; ``off`` (down in the clip's swing) and ``miss``
  (up in the clip's stance), as shares of steps;
- **two candidates**, per step and per leg at ``fore_tap``'s weight (-8):
  ``hind_tap``, ``fore_tap``'s form on the hinds, ``((1 - ref_lh_down) *
  chl_down + (1 - ref_rh_down) * chr_down) / 2``, and ``hind_scuff``, the
  same contact gated by the clip's swing height instead of its swing flag,
  ``(chl_down * g(ref_lh_lift) + chr_down * g(ref_rh_lift)) / 2`` with
  ``g = sat01((lift - 10) / 20)``: it charges a paw down where the clip
  has it 10-30 mm and more up, and nothing on an early or late landing
  near the floor. Beside them what ``track_contact`` (w 10 over four
  paws) already charges each hind for ``off`` and ``miss``, the taps (a
  touchdown in contact for at most 40 ms) a clip stride, and the share of
  ``hind_scuff``'s charge that falls on those taps;
- **the hind lag with and without the taps:** for each RH landing that is
  not a tap, the next LH touchdown within a clip stride, and the next LH
  touchdown that is not a tap, as shares of the clip's stride.

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
sys.path.insert(0, str(HERE.parents[1] / "orun15"))
from lag_term import PAWS, E, capsules, touchdowns  # noqa: E402

TAP_W = -8.0
SCUFF_FROM, SCUFF_SPAN = 10.0, 20.0
TAP_MS = 40.0


def blend(schedule, cmd):
    speeds = schedule["speeds_mm_s"]
    v = min(max(abs(cmd), speeds[0]), speeds[-1])
    i = max(k for k in range(len(speeds) - 1) if speeds[k] <= v)
    return i, (v - speeds[i]) / (speeds[i + 1] - speeds[i])


def origin(model, tracking, k, frame):
    rows = int(tracking["samples"])
    best = None
    for s in range(rows):
        row = tracking["reset_qpos"][k * rows + s]
        err = 0.0
        for joint, q in frame:
            j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
            err += (math.degrees(row[model.jnt_qposadr[j]]) - q) ** 2
        if best is None or err < best[0]:
            best = (err, s)
    return best


def ref_down(tracking, i, w, phase, kind="down"):
    rows = int(tracking["samples"])
    names = tracking["channels"][2:]
    at = (phase - math.floor(phase)) * rows
    low = int(math.floor(at)) % rows
    high = (low + 1) % rows
    f = at - math.floor(at)
    out = {}
    for k in PAWS:
        c = names.index("ref_%s_%s" % (k, kind))
        val = 0.0
        for table, share in ((tracking["schedule"]["tables"][i], 1 - w), (tracking["schedule"]["tables"][i + 1], w)):
            val += share * (table[low][c] + f * (table[high][c] - table[low][c]))
        out[k] = val if kind != "down" else (1.0 if val >= 0.5 else 0.0)
    return out


def scuff_gate(lift):
    """sat01((ref_lift - SCUFF_FROM) / SCUFF_SPAN): 0 below 10 mm of clip lift, 1 from 30 mm."""

    return min(1.0, max(0.0, (lift - SCUFF_FROM) / SCUFF_SPAN))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    tracking = json.loads(Path(argv[0]).read_text())["tracking"]
    schedule = tracking["schedule"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    geoms = capsules(model)
    print("| evaluation | cmd | clip Hz | touchdowns a clip stride LH / RH "
          "| LH: phase tenth after the clip's touchdown, share (contact ms) "
          "| RH: the same | off LH / RH | miss LH / RH "
          "| track_contact charge LH / RH (w10) | hind_tap a step LH / RH (w -8) "
          "| taps (<= 40 ms) a clip stride LH / RH | hind_scuff a step LH / RH (w -8); share on taps "
          "| LH after RH, share of the clip stride (median): next touchdown / next non-tap |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arg in argv[2:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd = float(ev["judged_command_mm_s"])
        floor = ev["rig"]["floor_mm"]
        i, w = blend(schedule, cmd)
        turns = (1 - w) * schedule["turns_per_step"][i] + w * schedule["turns_per_step"][i + 1]
        k0 = min(range(len(schedule["speeds_mm_s"])), key=lambda k: (abs(schedule["speeds_mm_s"][k] - cmd), k))
        hz = turns * 50.0
        acc = {side: {"td": 0, "taps": 0, "bins": {}, "off": [], "miss": [], "tap": [], "scuff": [],
                       "scuff_on_taps": 0.0, "lands": []} for side in ("lh", "rh")}
        lags = {"all": [], "real": []}
        strides = 0.0
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, s = origin(model, tracking, k0, list(zip(joints, solver[0]["joint_positions"])))
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            down = {k: [h <= E.STANCE_MM for h in E.foot_series(samples, body, geoms[body], floor)["height"]]
                    for k, body in PAWS.items()}
            settled = [n for n, t in enumerate(times) if t >= E.SETTLE_S - 1e-9]
            phase = {n: (times[n] * 50.0 * turns + s / float(tracking["samples"])) for n in settled}
            ref = {n: ref_down(tracking, i, w, phase[n]) for n in settled}
            lift = {n: ref_down(tracking, i, w, phase[n], "lift") for n in settled}
            strides += (times[settled[-1]] - times[settled[0]]) * hz
            for side in ("lh", "rh"):
                a = acc[side]
                clip_td = [times[n] for n in settled[1:] if ref[n][side] and not ref[n - 1][side]]
                for t in touchdowns(times, down[side]):
                    if t < E.SETTLE_S - 1e-9:
                        continue
                    a["td"] += 1
                    n = times.index(t)
                    m = n
                    while m + 1 < len(times) and down[side][m + 1]:
                        m += 1
                    a["lands"].append((t, 1000 * (times[m] - t + 0.02) <= TAP_MS + 1e-6))
                    if 1000 * (times[m] - t + 0.02) <= TAP_MS + 1e-6:
                        a["taps"] += 1
                        a["scuff_on_taps"] += sum(TAP_W * scuff_gate(lift[q][side]) / 2 for q in range(n, m + 1))
                    before = [c for c in clip_td if c <= t + 1e-9]
                    if before:
                        b = min(9, int(((t - before[-1]) * hz) % 1.0 * 10))
                        a["bins"].setdefault(b, []).append(1000 * (times[m] - t + 0.02))
                for n in settled:
                    c, r = (1.0 if down[side][n] else 0.0), ref[n][side]
                    a["off"].append(c * (1 - r))
                    a["miss"].append((1 - c) * r)
                    a["tap"].append(TAP_W * c * (1 - r) / 2)
                    a["scuff"].append(TAP_W * c * scuff_gate(lift[n][side]) / 2)

            rh = [t for t, tap in acc["rh"]["lands"] if not tap and t >= times[settled[0]]]
            lh = [(t, tap) for t, tap in acc["lh"]["lands"] if t >= times[settled[0]]]
            acc["rh"]["lands"], acc["lh"]["lands"] = [], []
            for r in rh:
                after = [(t, tap) for t, tap in lh if r < t <= r + 1.0 / hz]
                if after:
                    lags["all"].append((after[0][0] - r) * hz)
                    real = [t for t, tap in after if not tap]
                    if real:
                        lags["real"].append((real[0] - r) * hz)

        def pair(key, fn, spec="%.2f"):
            return " / ".join(spec % fn(acc[side][key]) for side in ("lh", "rh"))

        def bins(a):
            n = sum(len(v) for v in a["bins"].values())
            return ", ".join("%d: %.2f (%.0f)" % (b, len(v) / n, statistics.median(v))
                             for b, v in sorted(a["bins"].items()) if len(v) / n >= 0.05)

        mean = statistics.fmean
        print("| %s | %.0f | %.2f | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            out.name, cmd, hz,
            " / ".join("%.2f" % (acc[sd]["td"] / strides) for sd in ("lh", "rh")),
            bins(acc["lh"]), bins(acc["rh"]),
            pair("off", mean), pair("miss", mean),
            " / ".join("%.2f" % (10 * (mean(acc[sd]["off"]) + mean(acc[sd]["miss"])) / 4) for sd in ("lh", "rh")),
            pair("tap", mean, "%+.3f"),
            " / ".join("%.2f" % (acc[sd]["taps"] / strides) for sd in ("lh", "rh")),
            " / ".join("%+.3f; %s" % (mean(acc[sd]["scuff"]),
                                      ("%.2f" % (acc[sd]["scuff_on_taps"] / sum(acc[sd]["scuff"])))
                                      if sum(acc[sd]["scuff"]) else "–") for sd in ("lh", "rh")),
            "%.3f / %.3f" % (statistics.median(lags["all"]), statistics.median(lags["real"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
