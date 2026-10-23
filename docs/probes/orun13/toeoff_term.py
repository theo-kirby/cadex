"""orun13 P1 (O2, O7): score a heel-through-toe-off term per step before training on it.

usage: ~/cadex-train-venv/bin/python docs/probes/orun13/toeoff_term.py \
           BUNDLE EVALUATION_DIR [EVALUATION_DIR ...]

``hock_at_toeoff`` (the engine's ``heel_down_at_toeoff_share``) passes a
stance only if the heel is within ``STANCE_MM`` in one of its last
``HEEL_TOEOFF_S`` (40 ms: the lift frame and the two before it). A stance
that rolls onto its toes for three or more frames before lifting fails,
and so does a toe tap that never puts the heel down. Both are toe-stance
frames: paw down, heel up. The candidate term pays against them:

    toe_stance = (chl_down * (1 - khl_down) + chr_down * (1 - khr_down)) / 2

with a negative weight. Before it goes into a task, this scores it two ways:

- **On the clip** (``reward_terms.py``'s kinematic ``clip`` replay from
  every sample, contacts from ``mj_forward``): the share of steps the
  clip itself is in a toe stance, so the term's cost to perfect tracking.
  A kinematic pose seldom presses the floor, so this reads contact terms
  low (the bundle's ``plantigrade`` reads 0 there); it bounds, not measures.
- **On judged traces** (the engine's ``foot_series`` on the paw and heel
  geoms, after the 1 s settle): per leg, the share of on-ground frames in
  a toe stance (the term's mean per step, over steps on the ground); where
  those frames sit: before the stance's first heel-down frame (landing),
  after its last (the roll to toe-off), or in a stance with no heel down
  (a tap); and each toe-off as the engine's ``hock_at_toeoff`` reads it:
  through the heel, rolled off the toes (with the roll's median frames),
  or a tap.

The bundle's own terms are printed beside it on the clip, so the weight can
be set against them. Writes nothing. Left and right are given apart (O5).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
import reward_terms as R  # noqa: E402
from spine_foot import LEGS, paw_capsules  # noqa: E402

TERM = {"label": "toe_stance", "weight": 1.0,
        "expression": "(chl_down * (1 - khl_down) + chr_down * (1 - khr_down)) / 2"}
PER_LEG = {"LH": "chl_down * (1 - khl_down)", "RH": "chr_down * (1 - khr_down)"}


def on_clip(bundle: Path):
    task, model = R.load(bundle)
    task = dict(task)
    task["reward"] = list(task["reward"]) + [TERM] + [
        {"label": f"toe_{leg}", "weight": 1.0, "expression": e} for leg, e in PER_LEG.items()]
    comp = R.compiled(task)
    skip = int(round(0.5 / float(task["episode"]["control_interval_s"])))
    rows = []
    for origin in range(int(task["tracking"]["samples"])):
        got, _ = R.run(task, model, comp, "clip", origin, 2.0)
        rows += got[skip:]
    labels = [str(t["label"]) for t in task["reward"]]
    return {l: float(np.mean([r[l] for r in rows])) for l in labels}, model


def on_trace(out: Path, model):
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    geoms = paw_capsules(model)
    acc = {leg: {"ground": 0, "toe": 0, "land": 0, "tail": 0, "tap": 0, "pushes": 0, "through": 0,
                  "rolled": 0, "tapped": 0, "roll_frames": []} for leg, _ in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        times = [t for t, _ in samples]
        for leg, paw in LEGS:
            sole = E.foot_series(samples, paw, geoms[paw], rig["floor_mm"])["height"]
            h = rig["heels"][paw]
            heel = E.foot_series(samples, h["body"], h["geoms"], rig["floor_mm"])["height"]
            toes = [s <= E.STANCE_MM for s in sole]
            down = [x <= E.STANCE_MM for x in heel]
            ground = [a or b for a, b in zip(toes, down)]
            a = acc[leg]
            i = 0
            while i < len(ground):
                if not ground[i]:
                    i += 1
                    continue
                run = []
                while i < len(ground) and ground[i]:
                    run.append(i)
                    i += 1
                late = [k for k in run if times[k] >= E.SETTLE_S - 1e-9]
                if not late:
                    continue
                a["ground"] += len(late)
                toe = [k for k in late if toes[k] and not down[k]]
                a["toe"] += len(toe)
                heeled = [k for k in run if down[k]]
                if not heeled:
                    a["tap"] += len(toe)
                else:
                    a["land"] += sum(1 for k in toe if k < heeled[0])
                    a["tail"] += sum(1 for k in toe if k > heeled[-1])
                if i < len(ground) and times[run[-1]] >= E.SETTLE_S - 1e-9:
                    a["pushes"] += 1
                    e = run[-1]
                    if any(down[k] for k in run if times[e] - times[k] <= E.HEEL_TOEOFF_S + 1e-9):
                        a["through"] += 1
                    elif heeled:
                        a["rolled"] += 1
                        a["roll_frames"].append(sum(1 for k in run if k > heeled[-1]))
                    else:
                        a["tapped"] += 1
    return acc


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    means, model = on_clip(Path(argv[0]).expanduser())
    print("## On the clip (kinematic replay, every sample, mean per step, unweighted for the candidate)\n")
    print("| term | mean per step |\n|---|---|")
    for label, v in means.items():
        print(f"| {label} | {v:.3f} |")
    print("\n## On judged traces (after the 1 s settle)\n")
    print("| evaluation | leg | on-ground frames | toe-stance share | of which landing / tail / tap "
          "| toe-offs | through heel / rolled / tap | median roll frames |")
    print("|---|---|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg).expanduser()
        for leg, a in on_trace(out, model).items():
            n = max(a["ground"], 1)
            t = max(a["toe"], 1)
            p = max(a["pushes"], 1)
            roll = float(np.median(a["roll_frames"])) if a["roll_frames"] else float("nan")
            print(f"| {out.name} | {leg} | {a['ground']} | {a['toe'] / n:.2f} "
                  f"| {a['land'] / t:.2f} / {a['tail'] / t:.2f} / {a['tap'] / t:.2f} | {a['pushes']} "
                  f"| {a['through'] / p:.2f} / {a['rolled'] / p:.2f} / {a['tapped'] / p:.2f} | {roll:.0f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
