"""orun14: what a shorter toes-up stop on the hind paw pin would cut (O1 write-up for leo-v03.1).

Usage: pixi run python docs/probes/orun14/pin_cap.py MODEL.xml EVAL_DIR... [--cap DEG]

Reads each evaluation's traces with ``paw_floor.py``'s series (pin angle
toes-up of the metatarsus, paw pitch against the floor, heel and paw down),
and per hind leg over settled stance frames (paw down) gives: the pin's
p50 / p90 and the share of stance with the pin past ``--cap`` (default 30);
the metatarsus's own pitch against the floor (floor pitch less pin); and,
holding that metatarsus pitch, the floor pitch the paw would have with the
pin clamped at the cap, so the share of stance that would still read ``U``
(toes-up of the floor past ``FLAT_DEG``). It also gives the share of the
heel-up flat stance (``R``, the roll and the digitigrade stance) that uses
more than the cap, which a shorter stop would take away. A static bound,
not a prediction of a retrained policy. Writes nothing.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paw_floor as P  # noqa: E402


def main(argv):
    cap = 30.0
    if "--cap" in argv:
        k = argv.index("--cap")
        cap = float(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    geoms = P.paw_capsules(mujoco.MjModel.from_xml_path(argv[0]))
    print(f"| evaluation | leg | stance frames | pin p50 / p90 ° | stance pin > {cap:.0f}° | metatarsus ° of floor p50 "
          f"| U now | U with pin ≤ {cap:.0f}° | R frames pin > {cap:.0f}° |")
    print("|---|---|---|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        acc = {leg: {"pin": [], "meta": [], "u": 0, "u_cap": 0, "r": 0, "r_over": 0, "n": 0} for leg, *_ in P.LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            series = P.seed_series(geoms, rig, json.loads(path.read_text()))
            for leg, *_ in P.LEGS:
                s, a = series[leg], acc[leg]
                for i, t in enumerate(s["t"]):
                    if t < P.E.SETTLE_S - 1e-9 or s["sole"][i] > P.E.STANCE_MM:
                        continue
                    pin, pitch = s["pin"][i], s["pitch"][i]
                    a["n"] += 1
                    a["pin"].append(pin)
                    a["meta"].append(pitch - pin)
                    a["u"] += pitch > P.FLAT_DEG
                    a["u_cap"] += pitch - max(0.0, pin - cap) > P.FLAT_DEG
                    if s["mark"][i] == "R":
                        a["r"] += 1
                        a["r_over"] += pin > cap
        for leg, a in acc.items():
            n = max(a["n"], 1)
            q = statistics.quantiles(a["pin"], n=10) if len(a["pin"]) > 1 else [float("nan")] * 9
            print(f"| {out.name} | {leg} | {a['n']} | {statistics.median(a['pin']):+.1f} / {q[8]:+.1f} "
                  f"| {sum(p > cap for p in a['pin']) / n:.2f} | {statistics.median(a['meta']):+.1f} "
                  f"| {a['u'] / n:.2f} | {a['u_cap'] / n:.2f} | {a['r_over'] / max(a['r'], 1):.2f} of {a['r']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
