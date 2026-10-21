"""orun15 ladder rung 4: what the gallop clip asks for, against what a policy does.

usage: python3 docs/probes/orun15/clip_read.py GALLOP_TASK_JSON [EVALUATION_DIR ...]

**The clip**, from the bundle's ``reference`` block (the engine's
``CadexGait.generate`` output): period, speed and stride; each foot's
touch-down time after LH's in ms (signed: negative lands before LH); each
pair's lag in ms, folded as ``CadexEvaluation.footfall_metrics`` folds it;
each hind heel's down share of its paw's stance; the spine joints'
range; and the speed ``track_speed`` pays up to.

**Each evaluation**, from ``evaluation.json`` (10 seeds, after the first
second): for every LH touchdown, the signed time to the nearest touchdown
of each other paw (within half a stride), median over touchdowns and
seeds, and the share of LH touchdowns RH lands in the same 20 ms frame
as (``together``); the engine's stride rate. Standard library only.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path

SETTLE_S = 1.0
PAW = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}


def clip(task: Path):
    t = json.loads(task.read_text())
    ref = t["reference"]
    p = ref["parameters"]
    period = p["period_s"]
    off = p["phase_offsets"]

    def signed(k):  # touch-down after LH's, folded into (-0.5, 0.5] of a cycle
        f = (off[k] - off["LH"]) % 1.0
        return f - 1.0 if f > 0.5 else f

    print(f"## The clip ({ref['label']})\n")
    print(f"- {p['stride_length_m']:.2f} m at {p['stride_frequency_hz']:.2f} Hz = {p['speed_m_s']:.2f} m/s, "
          f"period {period * 1000:.0f} ms, duty {p['duty_factor']}, {len(ref['contact']['LH'])} samples "
          f"of {ref['sample_dt_s'] * 1000:.1f} ms")
    print("- touch-down after LH's: " + ", ".join(
        f"{k} {signed(k) * period * 1000:+.0f} ms" for k in ("RH", "LF", "RF")))
    for pair, (a, b) in (("hind", ("LH", "RH")), ("fore", ("LF", "RF"))):
        lag = (off[b] - off[a]) % 1.0
        lag = min(lag, 1.0 - lag)
        print(f"- {pair} pair lag {lag:.3f} of the cycle = {lag * period * 1000:.1f} ms")
    for k, h in ref["heels"].items():
        stance = sum(ref["contact"][k])
        both = sum(1 for c, d in zip(ref["contact"][k], h["down"]) if c and d)
        print(f"- {k} heel down on {both} of {stance} stance samples ({both / stance:.2f}), "
              f"heel_from {h['from_stance_share']}")
    angles = ref["joint_angles_rad"]
    for j in ("j_spine", "j_spine2"):
        i = ref["joints"].index(j)
        v = [math.degrees(a[i]) for a in angles]
        print(f"- {j} {min(v):+.1f} .. {max(v):+.1f} deg ({max(v) - min(v):.1f} peak to peak)")
    for term in t["reward"]:
        if term["label"] == "track_speed":
            caps = sorted({float(x) for x in re.findall(r"comv_x - (\d+)", term["expression"])})
            print(f"- track_speed (w{term['weight']:g}) pays forward speed linearly up to "
                  + ", ".join(f"{c / 1000:.2f}" for c in caps) + " m/s")
    print()
    return {k: signed(k) * period for k in ("RH", "LF", "RF")}


def nearest(t0, times, half):
    best = None
    for t in times:
        d = t - t0
        if abs(d) <= half and (best is None or abs(d) < abs(best)):
            best = d
    return best


def evaluation(path: Path, asked):
    e = json.loads((path / "evaluation.json").read_text())
    rows, together, n_lh = {k: [] for k in asked}, 0, 0
    rates = []
    for s in e["seeds"]:
        d = s["detail"]
        feet = d["feet"]
        hz = d["footfall"]["stride_hz"]
        rates.append(hz)
        half = 0.5 / hz
        lh = [t for t in feet[PAW["LH"]]["touchdowns_s"] if t >= SETTLE_S]
        for t0 in lh:
            n_lh += 1
            for k in asked:
                dt = nearest(t0, feet[PAW[k]]["touchdowns_s"], half)
                if dt is not None:
                    rows[k].append(dt)
                    if k == "RH" and abs(dt) < 0.02 - 1e-9:
                        together += 1
    print(f"## {path.name}\n")
    print("| paw | clip ms after LH | policy median ms (q1 / q3) | LH touchdowns matched |")
    print("|---|---|---|---|")
    for k, v in rows.items():
        q = statistics.quantiles(v, n=4) if len(v) > 1 else [math.nan] * 3
        print(f"| {k} | {asked[k] * 1000:+.0f} | {statistics.median(v) * 1000:+.0f} ({q[0] * 1000:+.0f} / "
              f"{q[2] * 1000:+.0f}) | {len(v)} / {n_lh} |")
    print(f"\nRH in the same 20 ms frame as LH on {together} / {n_lh} LH touchdowns "
          f"({together / max(n_lh, 1):.2f}); stride rate median {statistics.median(rates):.2f} Hz\n")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    asked = clip(Path(argv[1]).expanduser())
    for p in argv[2:]:
        evaluation(Path(p).expanduser(), asked)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
