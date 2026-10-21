"""orun14 P1 (O7): score candidate stance-fold penalties per step on judged traces, before any is trained.

usage: pixi run python docs/probes/orun14/fold_term.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

Reads each evaluation's seed traces with ``paw_floor.py``'s series (the
paw's floor pitch, the pin's toes-up angle, the paw's and heel's heights)
and, per hind leg, from the engine's settle (1 s) on:

- **where the fold is:** the U frames (``paw_floor.py``'s toes-up of the
  floor) split into paw down (``chX_down``) and heel down with the paw off
  (``khX_down`` alone), and the floor pitch's quartiles on them;
- **what ``paw_flat`` pays there:** its band is 15 deg wide, so a paw past
  15 deg toes-up is paid nothing and has no slope back to flat; the share
  of U frames past 15;
- **two candidates, both gated on contact the policy observes** (paw or
  heel down: ``max(chX_down, khX_down)``), not on the clip's stance, so a
  fold outside the clip's stance is charged too:
  - ``pin30``: ``max(0, pin - 30) / 30``, the pin toes-up of the
    metatarsus past 30 deg (``q_pawpin``, observed);
  - ``fold``: ``max(0, pitch - 5) / 30``, the paw toes-up of the floor
    past 5 deg, where pitch is ``paw_flat``'s observed-channel estimate
    (pin less the metatarsus's pitch, + 1.9), here read from placements.

Each candidate's mean per frame class (F, R, T, U, swing), and the share
of U frames it charges at all. A term earns a screen if it charges U and
leaves F and R (the flat foot and the pin's roll, O2) near zero.
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
from paw_floor import E, LEGS, paw_capsules, seed_series  # noqa: E402


def pin30(pin, pitch):
    return max(0.0, pin - 30.0) / 30.0


def fold(pin, pitch):
    return max(0.0, pitch - 5.0) / 30.0


TERMS = (("pin30", pin30), ("fold", fold))


def quartiles(values):
    if len(values) < 4:
        return "–"
    q = statistics.quantiles(values, n=4)
    return "%+.0f / %+.0f / %+.0f" % (q[0], q[1], q[2])


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    geoms = paw_capsules(mujoco.MjModel.from_xml_path(argv[0]))
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        acc = {leg: {"U_paw": 0, "U_heel": 0, "U_pitch": [], "frames": {c: [] for c in "FRTU."}} for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            series = seed_series(geoms, rig, json.loads(path.read_text()))
            for leg, *_ in LEGS:
                s, a = series[leg], acc[leg]
                for i, t in enumerate(s["t"]):
                    if t < E.SETTLE_S - 1e-9:
                        continue
                    m = s["mark"][i]
                    paw = s["sole"][i] <= E.STANCE_MM
                    heel = s["heel"][i] <= E.STANCE_MM
                    if m == "U":
                        a["U_paw" if paw else "U_heel"] += 1
                        a["U_pitch"].append(s["pitch"][i])
                    gate = 1.0 if (paw or heel) else 0.0
                    a["frames"][m].append({n: gate * f(s["pin"][i], s["pitch"][i]) for n, f in TERMS})
        print(f"## {out.name}\n")
        print("| leg | U frames: paw down / heel only | U floor pitch ° q1 / med / q3 | U past paw_flat's 15° "
              + "".join(f"| {n} on F / R / T / U / swing | {n} charges U " for n, _ in TERMS) + "|")
        print("|---|---|---|---|" + "---|---|" * len(TERMS))
        for leg, a in acc.items():
            nu = a["U_paw"] + a["U_heel"]
            row = (f"| {leg} | {a['U_paw']} / {a['U_heel']} | {quartiles(a['U_pitch'])} "
                   f"| {sum(1 for p in a['U_pitch'] if p > 15) / max(nu, 1):.2f} ")
            for n, _ in TERMS:
                means = [statistics.fmean([r[n] for r in a["frames"][c]]) if a["frames"][c] else 0.0 for c in "FRTU."]
                hit = sum(1 for r in a["frames"]["U"] if r[n] > 0) / max(len(a["frames"]["U"]), 1)
                row += "| " + " / ".join("%.3f" % v for v in means) + f" | {hit:.2f} "
            print(row + "|")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
