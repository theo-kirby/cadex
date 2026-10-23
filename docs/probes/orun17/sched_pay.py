"""orun17 SG: what heel_sched would pay a judged policy's hind stance frames at another weight and tent width.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/sched_pay.py \
           RUN/train/gallop-task.json EVALUATION_DIR [...] [--variant W:HW ...]

O7: a term is evaluated per step on traces before it trains. heel_sched pays
``W * tent(_META, T, HW) / 2`` a leg on paw-down frames (as built W 6, HW 30;
T = 6 + 30 (2400 - cmd) / 1700). ``slow_heel.py`` showed the slow heel-down
frames at _META ~+5 against T +36: 31 deg off, past the half-width, so the
tent pays them nothing and gives them no slope. For each evaluation, leg and
variant (default 6:30, the build; 12:30; 12:40; 6:15), on settled paw-down
frames split heel down / heel up (``slow_heel.py``'s split and calibration):

- the pay a step on heel-down and on heel-up frames;
- the schedule's contrast: heel-up less heel-down pay when T > 20 (the
  schedule wants the heel up), heel-down less heel-up otherwise;
- the share of heel-down and heel-up frames the tent gives no slope
  (|_META - T| >= HW);
- the slope at the frame's own pitch, a step a degree, mean over all
  paw-down frames.

Writes nothing.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

import mujoco

_spec = importlib.util.spec_from_file_location("slow_heel", Path(__file__).resolve().parent / "slow_heel.py")
SH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SH)
H, E = SH.H, SH.E

VARIANTS = [(6.0, 30.0), (12.0, 30.0), (12.0, 40.0), (6.0, 15.0)]


def pitches(out, cal, paw_geoms):
    """{side: {True: [_META on heel-down paw-down frames], False: [... heel-up]}}, settled frames."""

    ev = json.loads((out / "evaluation.json").read_text())
    rig = ev["rig"]
    acc = {s: {True: [], False: []} for s in "lr"}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"])
                   for f in trace["frames"] if f.get("component_placements")]
        settled = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
        for side in "lr":
            paw = f"c_paw_h{side}"
            hb = rig["heels"][paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
            sole = E.foot_series(samples, paw, paw_geoms[paw], rig["floor_mm"])["height"]
            for i in settled:
                if sole[i] > E.STANCE_MM:
                    continue
                rot, _ = E._pose(samples[i][1], f"c_meta_h{side}")
                m = H.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0]
                acc[side][heel[i] <= E.STANCE_MM].append(m)
    return float(ev["judged_command_mm_s"]), acc


def main(argv):
    variants = list(VARIANTS)
    if "--variant" in argv:
        k = argv.index("--variant")
        variants = [tuple(float(x) for x in v.split(":")) for v in argv[k + 1:]]
        argv = argv[:k]
    if len(argv) < 2:
        print(__doc__)
        return 2
    cal = H.calibrate(Path(argv[0]))
    task = json.loads(Path(argv[0]).read_text())
    paw_geoms = H.paw_capsules(mujoco.MjModel.from_xml_path(
        str(Path(argv[0]).parent / Path(task["model"]["path"]).name)))
    print("| evaluation | leg | frames down / up | T | W:HW | pay down / up | contrast | no slope down / up | slope a deg |")
    print("|---|---|---|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg)
        cmd, acc = pitches(out, cal, paw_geoms)
        t = SH.target(cmd)
        for side, a in acc.items():
            for w, hw in variants:
                pay = {h: w * statistics.fmean(SH.HS.tent(m, t, hw) for m in a[h]) / 2 if a[h] else float("nan")
                       for h in (True, False)}
                flat = {h: sum(abs(m - t) >= hw for m in a[h]) / max(len(a[h]), 1) for h in (True, False)}
                every = a[True] + a[False]
                slope = w / hw / 2 * sum(abs(m - t) < hw for m in every) / max(len(every), 1)
                contrast = pay[False] - pay[True] if t > 20 else pay[True] - pay[False]
                print(f"| {out.name} | {side.upper()}H | {len(a[True])} / {len(a[False])} | {t:+.1f} | {w:g}:{hw:g} "
                      f"| {pay[True]:.2f} / {pay[False]:.2f} | {contrast:+.2f} | {flat[True]:.2f} / {flat[False]:.2f} "
                      f"| {slope:.3f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
