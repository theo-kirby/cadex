"""orun15 P1 (O7): where each hind paw stands in stance, and a placement term scored per step, before it is trained.

usage: pixi run python docs/probes/orun15/place_term.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

``hlk8-mirror.md``: on hlk8-sole-50 the hind that lands second folds (U
0.29 against 0.02) and lands ~340 mm past the fore prints. The clip cannot
stand it further back (``ss-sole.md``: every LH shift under 120 mm is
refused), so this asks whether a term on the paw's place can tell the
folded stance from the flat one.

Per hind leg, over frames from the settle (1 s) on, with ``paw_floor.py``'s
letters (F flat, R roll, T toes, U toes-up of the floor):

- **the place**: the paw's centre of mass (with its claws and spring, the
  trainer's ``phl``/``phr`` subtree) ahead of the whole model's,
  plus 311 mm, which is the trainer's ``p*_x - com_x + 311`` (the
  ``hind_reach`` term's standing place: 0 under the hip at the build pose);
  the COM is mass-weighted over every body's placement, all 31.5 kg;
- the place at touch-down (the first paw-down frame of a stance), and its
  median over U frames and over F/R frames;
- **the candidate** ``hind_place`` per leg, ``c_down * max(0, place - D) /
  S`` with D = ``REACH_MM`` (150) and S = ``SLOPE_MM`` (50): nothing at
  the first hind's +133 mm touch-down on hlk8-sole-50, about 1 at the
  second's +208, averaged over both hinds as the gallop terms
  are, a mean per settled step; and the share of it that falls on U frames
  (a term that charges the fold, not the flat stance, puts most there).

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
from paw_floor import E, LEGS, paw_capsules, seed_series  # noqa: E402

STAND_MM = 311.0
REACH_MM = 150.0
SLOPE_MM = 50.0


def com_x(model, placements, root=1):
    """The x of the centre of mass of ``root``'s subtree, mm: the trainer's ``centre_of_mass`` channel
    (``com`` is the chest frame's, the root, so the whole model; ``phl`` the paw's with its claws and spring)."""

    total = x = 0.0
    for b in range(1, model.nbody):
        a = b
        while a and a != root:
            a = int(model.body_parentid[a])
        if a != root:
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b)
        rot, pos = E._pose(placements, name)
        ip = [1000 * float(v) for v in model.body_ipos[b]]
        m = float(model.body_mass[b])
        x += m * (pos[0] + sum(rot[0][k] * ip[k] for k in range(3)))
        total += m
    return x / total


def body_com_x(model, placements, name):
    return com_x(model, placements, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name))


def med(v):
    return statistics.median(v) if v else float("nan")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = paw_capsules(model)
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        acc = {leg: {"td": [], "U": [], "FR": [], "term": [], "termU": 0.0, "n": 0} for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            frames = [f for f in trace["frames"] if f.get("component_placements")]
            series = seed_series(geoms, rig, trace)
            com = [com_x(model, f["component_placements"]) for f in frames]
            for leg, paw, *_ in LEGS:
                s, a = series[leg], acc[leg]
                place = [body_com_x(model, f["component_placements"], paw) - c + STAND_MM
                         for f, c in zip(frames, com)]
                for i, t in enumerate(s["t"]):
                    if t < E.SETTLE_S - 1e-9:
                        continue
                    down = s["sole"][i] <= E.STANCE_MM
                    mark = s["mark"][i]
                    if down and i and s["sole"][i - 1] > E.STANCE_MM:
                        a["td"].append(place[i])
                    if mark == "U":
                        a["U"].append(place[i])
                    elif mark in "FR":
                        a["FR"].append(place[i])
                    v = (1.0 if down else 0.0) * max(0.0, place[i] - REACH_MM) / SLOPE_MM
                    a["term"].append(v)
                    if mark == "U":
                        a["termU"] += v
                    a["n"] += 1
        print(f"\n## {out.name}\n")
        print("| leg | place at touch-down mm (median, p90) | place on U frames | on F/R frames "
              f"| hind_place a step (D {REACH_MM:.0f}, S {SLOPE_MM:.0f}) | its share on U frames |")
        print("|---|---|---|---|---|---|")
        both = []
        for leg, *_ in LEGS:
            a = acc[leg]
            td = sorted(a["td"])
            p90 = td[int(0.9 * (len(td) - 1))] if td else float("nan")
            total = sum(a["term"])
            both.append(statistics.fmean(a["term"]) if a["term"] else 0.0)
            print(f"| {leg} | {med(td):+.0f} ({p90:+.0f}) | {med(a['U']):+.0f} ({len(a['U'])}) "
                  f"| {med(a['FR']):+.0f} ({len(a['FR'])}) | {both[-1]:.3f} | {a['termU'] / total if total else 0:.2f} |")
        print(f"\nhind_place, both legs averaged: {statistics.fmean(both):.3f} a step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
