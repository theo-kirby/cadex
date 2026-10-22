"""orun16 B1/O9: the hind paw pin's rate, split by stance and swing, and where its fast frames fall.

usage: pixi run python docs/probes/orun16/pin_rate.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

``orun14/paw_floor.py`` gives the pin rate p95 / max over all settled frames
and over swing; this reads the same series (its ``seed_series``: the pin
angle from the placements, a central difference over the 20 ms frames) and
splits it three ways per hind leg (O5):

- **all**, **stance** (any frame with paw or heel on the floor: a
  ``paw_floor`` letter other than ``.``) and **swing** (``.``);
- each as the median over seeds of the seed's p95 (``paw_floor``'s
  convention), the p95 of all seeds' frames pooled, and the max;
- where the frames over 900 deg/s fall: within two frames (40 ms) of a
  touch-down or a lift, against the rest of stance and of swing.

Frames from the engine's settle (1 s) on. Writes nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "orun14"))
import paw_floor as PF  # noqa: E402

FAST = PF.SNAP_DEG_S
EDGE = 2


def split(series):
    t, mark, rate = series["t"], series["mark"], series["rate"]
    late = [i for i in range(len(t)) if t[i] >= PF.E.SETTLE_S - 1e-9 and rate[i] is not None]
    edges = set()
    for i in range(1, len(mark)):
        if (mark[i] == ".") != (mark[i - 1] == "."):
            edges.update(range(i - EDGE, i + EDGE))
    groups = {"all": [], "stance": [], "swing": []}
    where = {"edge": 0, "stance": 0, "swing": 0}
    for i in late:
        v = abs(rate[i])
        groups["all"].append(v)
        groups["swing" if mark[i] == "." else "stance"].append(v)
        if v > FAST:
            where["edge" if i in edges else ("swing" if mark[i] == "." else "stance")] += 1
    return groups, where


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    geoms = PF.paw_capsules(mujoco.MjModel.from_xml_path(argv[0]))
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        per = {leg: {"seeds": [], "pooled": {"all": [], "stance": [], "swing": []},
                     "where": {"edge": 0, "stance": 0, "swing": 0}} for leg, *_ in PF.LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            series = PF.seed_series(geoms, rig, json.loads(path.read_text()))
            for leg, *_ in PF.LEGS:
                groups, where = split(series[leg])
                per[leg]["seeds"].append({k: PF.pct(v, 0.95) for k, v in groups.items()})
                for k, v in groups.items():
                    per[leg]["pooled"][k] += v
                for k, v in where.items():
                    per[leg]["where"][k] += v
        print(f"## {out.name}: hind pin rate, deg/s (seed-median p95 / pooled p95 / max)\n")
        print("| leg | all | stance | swing | frames > 900: at touch-down or lift ±40 ms / mid-stance / mid-swing |")
        print("|---|---|---|---|---|")
        for leg, *_ in PF.LEGS:
            p = per[leg]
            cells = []
            for k in ("all", "stance", "swing"):
                cells.append("%.0f / %.0f / %.0f" % (PF.med([s[k] for s in p["seeds"]]),
                                                     PF.pct(p["pooled"][k], 0.95), max(p["pooled"][k])))
            w = p["where"]
            print(f"| {leg} | " + " | ".join(cells) + f" | {w['edge']} / {w['stance']} / {w['swing']} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
