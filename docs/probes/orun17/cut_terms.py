"""orun17 B1 (O7): the two cut terms that bear on LH, `paw_fold` and `hind_overreach`, scored per step on judged traces.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/cut_terms.py MODEL_XML EVALUATION_DIR [...]

sgt-1-50 (the trimmed task) lands LH reaching ahead of the fores on a paw
folded toes-up of the floor (U 0.36-0.60) while RH stands on its toe bulbs
(`sgt-1-50.md`). Two of the six cut terms bear on that leg. Before either
comes back (O8: one at a time, judged), this reads what each would pay on
the policy's own frames, per hind leg and per `paw_floor.py` frame class
(F flat, R roll, T toes, U toes-up of the floor, `.` swing), from the
engine's settle (1 s) on:

- ``paw_fold`` (w -10 in sg-s9's bundle), per leg
  ``gate * max(0, pitch - 5) / 30`` with gate = paw or heel down, and the
  task's two legs averaged. The task reads pitch from observed channels
  (pin less the metatarsus pitch, + 1.9); here it is `paw_floor.py`'s floor
  pitch from placements, as `orun14/fold_term.py` reads it;
- ``hind_overreach`` (w +3), per leg
  ``c_down * sat01(1 - (fore paws' mean x - hind paw x) / 450)``, x the
  paw subtree's centre of mass (the task's `centre_of_mass` channels, as
  `orun15/place_term.py` computes it from placements), c_down the paw on
  the floor (`paw_floor.py`'s sole within `STANCE_MM`; the task's is the
  contact force above 0).

Per leg: the term's mean a step (its share of the two-leg average is half
of it), the mean on each frame class, and the share of the leg's pay that
falls on U frames; and the weighted step value of each term, both legs.
A term that would pull LH's landing back charges LH's U frames and leaves
F/R alone (`paw_fold`); one that pays the reach itself would hand LH more
for what it already does (`hind_overreach` pays full at or past the fores).
Writes nothing.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "orun14"))
sys.path.insert(0, str(HERE.parents[1] / "orun15"))
from paw_floor import E, LEGS, paw_capsules, seed_series  # noqa: E402
from place_term import body_com_x  # noqa: E402

GAP_MM = 450.0
FOLD_W, OVER_W = -10.0, 3.0
CLASSES = "FRTU."


def sat01(x):
    return min(1.0, max(0.0, x))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = paw_capsules(model)
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        acc = {leg: {t: {c: [] for c in CLASSES} for t in ("fold", "over")} for leg, *_ in LEGS}
        gap = {leg: {c: [] for c in CLASSES} for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            frames = [f for f in trace["frames"] if f.get("component_placements")]
            series = seed_series(geoms, rig, trace)
            fore = [(body_com_x(model, f["component_placements"], "c_paw_fl")
                     + body_com_x(model, f["component_placements"], "c_paw_fr")) / 2 for f in frames]
            for leg, paw, *_ in LEGS:
                s = series[leg]
                for i, t in enumerate(s["t"]):
                    if t < E.SETTLE_S - 1e-9:
                        continue
                    c = s["mark"][i]
                    down = s["sole"][i] <= E.STANCE_MM
                    gate = 1.0 if c != "." else 0.0
                    acc[leg]["fold"][c].append(gate * max(0.0, s["pitch"][i] - 5.0) / 30.0)
                    d = fore[i] - body_com_x(model, frames[i]["component_placements"], paw)
                    acc[leg]["over"][c].append((1.0 if down else 0.0) * sat01(1.0 - d / GAP_MM))
                    if down:
                        gap[leg][c].append(-d)
        print(f"\n## {out.name}\n")
        print("| term | leg | a step | on F | on R | on T | on U | in swing | share of pay on U |")
        print("|---|---|---|---|---|---|---|---|---|")
        step = {}
        for term in ("fold", "over"):
            legs = []
            for leg, *_ in LEGS:
                by = acc[leg][term]
                every = [v for c in CLASSES for v in by[c]]
                mean = statistics.fmean(every) if every else 0.0
                legs.append(mean)
                total = sum(every)
                cells = " | ".join(f"{statistics.fmean(by[c]):.3f}" if by[c] else "–" for c in CLASSES)
                print(f"| {'paw_fold' if term == 'fold' else 'hind_overreach'} | {leg} | {mean:.3f} | {cells} "
                      f"| {sum(by['U']) / total if total else 0:.2f} |")
            step[term] = statistics.fmean(legs)
        print(f"\nweighted a step, both legs: paw_fold {FOLD_W * step['fold']:+.3f} (w {FOLD_W:g}), "
              f"hind_overreach {OVER_W * step['over']:+.3f} (w {OVER_W:g})")
        print("\nhind paw ahead of the fores' mean, mm, median on the floor, by class (frames):")
        for leg, *_ in LEGS:
            cells = ", ".join(f"{c} {statistics.median(gap[leg][c]):+.0f} ({len(gap[leg][c])})"
                              for c in "FRTU" if gap[leg][c])
            print(f"- {leg}: {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
