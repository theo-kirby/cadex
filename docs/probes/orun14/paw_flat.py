"""orun14 P1/O2/O7: the paw-flat term, read before it is trained: the hind paw's floor pitch from channels a reward can read.

usage: pixi run python docs/probes/orun14/paw_flat.py BUNDLE EVALUATION_DIR [EVALUATION_DIR ...]

BUNDLE is a run's ``train/gallop-task.json`` on leo v03 (its model sits beside
it); each EVALUATION_DIR holds ``docs/probes/orun11/judge.py``'s
``evaluation.json`` and ``seed-*-trace.json``.

**The reading.** heel_pitch's ``_META`` (chest pitch + 2 q_spine + hip - knee +
hock + 63.9, the right leg's joints sign-flipped) is the metatarsus's world
pitch plus a constant (``heel_meta.py``), heel up positive. The paw turns on
its pin toes-up of the metatarsus by ``up`` (``-q_pawpin_l``, ``+q_pawpin_r``:
the left pin's axis is +y and runs -60..0, the right's -y and 0..60). So the
paw's pitch against the floor, toes up positive, is

    F = up - _META + C

for one constant C. This finds C on the traces against ``paw_floor.py``'s
floor pitch (the pad-to-toe line, 0 when both capsules' lowest points are
level), and prints the fit's spread on paw-down frames: the formula is only a
reward if the spread is a few degrees.

**The term.** Paid in the clip's hind stance while the paw touches, falling
linearly to nothing ``HALF`` degrees either way of flat:

    pay_k = ref_k_down * c_k_down * max(0, 1 - |F_k| / HALF)

On each evaluation (frames from the 1 s settle on; the clip's stance flag is
not in a trace, so every paw-down frame stands in for it) it prints, per leg,
F's median and p10-p90 on paw-down frames, and the pay's mean on the paw-down
frames split as ``paw_floor.py`` letters them (F flat, R roll on a flat paw,
T on the toes, U toes-up of the floor). On the bundle's clip samples it prints
the same F and pay from ``reset_qpos`` (pin angles read off the joints): what
tracking the clip perfectly would earn. Finally it compiles the term's
expression with the trainer's compiler on the bundle's channels plus
``q_pawpin_l`` / ``q_pawpin_r`` and checks it against the Python above on the
clip samples. Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "orun13"))
sys.path.insert(0, str(HERE.parents[1] / "orun12"))
sys.path.insert(0, str(HERE.parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
import heel_meta as hm  # noqa: E402
import paw_floor as pf  # noqa: E402
import reward_terms as rt  # noqa: E402
from paw_pin import relative  # noqa: E402
from spine_foot import paw_capsules  # noqa: E402

HALF = 15.0
# The script's own expressions (leo script.py, orun14 p1-flat): kept equal by hand.
CHEST = "57.2958 * asin(2 * (imu_qw * imu_qy - imu_qx * imu_qz))"
META = {"l": "(%s + 2 * q_spine + q_hip_l - q_knee_l + q_hock_l + 63.9)" % CHEST,
        "r": "(%s + 2 * q_spine - q_hip_r + q_knee_r - q_hock_r + 63.9)" % CHEST}
UP = {"l": "(0 - q_pawpin_l)", "r": "q_pawpin_r"}


def expression(c):
    def flat(k):
        u_ = "(1 - abs(%s - %s + %.1f) / %g)" % (UP[k], META[k], c, HALF)
        return "c%s_down * (%s + abs(%s)) / 2" % ("h" + k, u_, u_)
    return "(ref_lh_down * %s + ref_rh_down * %s) / 2" % (flat("l"), flat("r"))


def pay(f):
    return max(0.0, 1.0 - abs(f) / HALF)


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else float("nan")


def med(values):
    return statistics.median(values) if values else float("nan")


def trace_rows(out, cal, paw_geoms):
    rig = json.loads((out / "evaluation.json").read_text())["rig"]
    acc = {s: [] for s in "lr"}   # (up - _META, floor pitch, heel down)
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        frames = [f for f in trace["frames"] if f.get("component_placements")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        for s in "lr":
            paw = f"c_paw_h{s}"
            pad, toe = pf.pad_toe(paw_geoms[paw])
            hb = rig["heels"][paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
            sole = E.foot_series(samples, paw, paw_geoms[paw], rig["floor_mm"])["height"]
            for i, (t, p) in enumerate(samples):
                if t < E.SETTLE_S - 1e-9 or sole[i] > E.STANCE_MM:
                    continue
                rot, _ = E._pose(p, f"c_meta_h{s}")
                meta = hm.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[s][0]
                up = -relative(p, f"h{s}")[0]
                acc[s].append((up - meta, pf.floor_pitch(p, paw, pad, toe), heel[i] <= E.STANCE_MM))
    return acc


def clip_rows(task, model, c):
    _, names, _, _ = rt.compiled(task)
    table = rt.ct.globals_for(np)
    plus = list(names) + ["q_pawpin_l", "q_pawpin_r"]
    fn = rt.ct.compile_expression(expression(c), plus, table)
    data = mujoco.MjData(model)
    tr = task["tracking"]
    adr = {s: model.jnt_qposadr[model.joint(f"j_pawpin_{s}").id] for s in "lr"}
    rows, worst = {s: [] for s in "lr"}, 0.0
    for k in range(int(tr["samples"])):
        data.qpos[:] = tr["reset_qpos"][k]
        data.qvel[:] = tr["reset_qvel"][k]
        mujoco.mj_forward(model, data)
        vec = rt.channel_vector(task, model, data, 0, k)
        v = {n: float(vec[i]) for i, n in enumerate(names)}
        q = {s: math.degrees(float(data.qpos[adr[s]])) for s in "lr"}
        up = {"l": -q["l"], "r": q["r"]}
        f = {s: up[s] - hm.meta_expr(v, s) + c for s in "lr"}
        down = {s: v[f"ref_{'lh' if s == 'l' else 'rh'}_down"] for s in "lr"}
        cdown = {s: v[f"ch{s}_down"] for s in "lr"}
        for s in "lr":
            if down[s] > 0.5:
                rows[s].append((f[s], up[s], cdown[s]))
        want = (down["l"] * cdown["l"] * pay(f["l"]) + down["r"] * cdown["r"] * pay(f["r"])) / 2
        got = float(eval(fn, table, {**v, "q_pawpin_l": q["l"], "q_pawpin_r": q["r"]}))
        worst = max(worst, abs(got - want))
    return rows, worst


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    bundle = Path(argv[0])
    cal = hm.calibrate(bundle)
    task, model = rt.load(bundle)
    paw_geoms = paw_capsules(model)
    traces = {Path(a).name: trace_rows(Path(a), cal, paw_geoms) for a in argv[1:]}
    allpts = [d - fp for acc in traces.values() for s in "lr" for d, fp, _ in acc[s]]
    c = -med(allpts)
    print("## The floor pitch from channels: F = up - _META + C\n")
    print(f"C = {c:+.2f} deg, the median over {len(allpts)} paw-down frames of {', '.join(traces)}.\n")
    print("| evaluation | leg | paw-down frames | F − floor pitch, p10 / median / p90 ° | floor pitch median (p10–p90) ° "
          "| pay mean: all / F / R / T / U | U share |")
    print("|---|---|---|---|---|---|---|")
    for name, acc in traces.items():
        for s in "lr":
            pts = acc[s]
            res = [d + c - fp for d, fp, _ in pts]
            fl = [fp for _, fp, _ in pts]

            def letter(fp, heel):
                return pf.letter(True, heel, fp)
            groups = {g: [pay(d + c) for d, fp, h in pts if letter(fp, h) == g] for g in "FRTU"}
            means = " / ".join("%.2f" % statistics.fmean(groups[g]) if groups[g] else "–" for g in "FRTU")
            print(f"| {name} | {s.upper()}H | {len(pts)} | {pct(res, 0.1):+.1f} / {med(res):+.1f} / {pct(res, 0.9):+.1f} "
                  f"| {med(fl):+.1f} ({pct(fl, 0.1):+.1f}–{pct(fl, 0.9):+.1f}) "
                  f"| {statistics.fmean(pay(d + c) for d, _, _ in pts):.2f} / {means} "
                  f"| {len(groups['U']) / max(len(pts), 1):.2f} |")
    print()
    rows, worst = clip_rows(task, model, round(c, 1))
    print(f"## The clip ({bundle.parent.parent.name}'s bundle), hind stance samples, C = {round(c, 1):+.1f}\n")
    print("| leg | stance samples | pin toes-up ° median (min–max) | F median (min–max) | pay mean (paw touching) |")
    print("|---|---|---|---|---|")
    for s in "lr":
        r = rows[s]
        fs, ups = [x[0] for x in r], [x[1] for x in r]
        touching = [pay(x[0]) * x[2] for x in r]
        print(f"| {s.upper()}H | {len(r)} | {med(ups):+.1f} ({min(ups):+.1f}–{max(ups):+.1f}) "
              f"| {med(fs):+.1f} ({min(fs):+.1f}–{max(fs):+.1f}) | {statistics.fmean(touching):.2f} |")
    print(f"\nThe trainer's compiled expression against the Python: worst |difference| {worst:.2e} over the clip.\n")
    print("```\n" + expression(round(c, 1)) + "\n```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
