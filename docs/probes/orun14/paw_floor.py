"""orun14 P1/O2/O9: the hind paw on its free pin, against the floor and against the metatarsus, from a judged evaluation's traces.

usage: pixi run python docs/probes/orun14/paw_floor.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...] [--seed N [FROM_S TO_S]]

MODEL_XML is the run's ``train/cat_model-model.xml``; each EVALUATION_DIR
holds ``docs/probes/orun11/judge.py``'s ``evaluation.json`` and
``seed-*-trace.json``. Every reading is over frames from the engine's settle
(1 s) on. It adapts orun13's ``foot_frames.py`` and ``lh_roll.py`` to v03's
free paw pin, and orun12's ``paw_pin.py`` for the pin itself.

**The paw against the floor.** v03's hind paw (``c_paw_h*``) has two
collision capsules, both lateral, so each is a circle in the paw's sagittal
plane: the pad (the larger, behind the pin) and the toe bulbs. The paw's
**floor pitch** is the angle of the line from the pad's centre to the toes'
centre, in world, less that angle when the two capsules' lowest points are
level (``asin((r_toe - r_pad) / d)``). 0 is a flat paw, positive is toes up
of the floor (O2's fault), negative is on the toe bulbs. The engine's
``foot_series`` on the paw's geoms (sole) and on ``rig["heels"]`` (the heel,
welded to the metatarsus) say what is down, as the engine's predicates read
it.

**The paw against the metatarsus.** The pin angle, toes-up positive (minus
the rotation about world +y, on both legs: the left pin, axis +y, runs
-60..0, and the right, axis -y, 0..60; 0 is the flat stop and the build pose),
read from the placements as orun12's ``paw_pin.relative`` reads it. Its
rate is a central difference over the 20 ms trace frames, so it averages
over 40 ms and is a lower bound on the step-rate speed O9 bounds at 900
deg/s p95.

Per frame on the ground, one letter:

- ``F`` flat: heel and paw down;
- ``R`` roll: heel up, paw down and flat (floor pitch within ``FLAT_DEG``):
  the push-off the pin is for, and the digitigrade stance on the pad;
- ``T`` toe stance: heel up, paw down on its toe bulbs (pitch below
  ``-FLAT_DEG``);
- ``U`` toes-up of the floor: paw pitch above ``+FLAT_DEG`` with the paw
  down, or the heel down and the paw off the floor (the orun12 fault);
- ``.`` off the floor.

Per leg (left and right apart, O5): the letter shares of on-ground frames;
the heel's share of stance (frames with the paw down, against the engine's
``heel_down_share``); the median floor pitch and pin angle in stance; at
each toe-off (the last paw-down frame) the roll length (frames from the last
heel-down frame; ``tap`` when the stance had no heel), the pin angle and
the floor pitch at lift; and the pin rate p95 / max over all settled frames
and over swing frames, with the share of swing frames over 900 deg/s and
the swings whose pin rate reverses twice above ``FLAP_DEG_S`` (a flap).

``--seed N`` also prints that seed's letter timeline between FROM_S and
TO_S (default 1.0 to 2.5 s) and each stance's first ``F`` frame, the frame a
still is rendered from (``docs/probes/orun12/render_frame.py``). Writes
nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "orun13"))
sys.path.insert(0, str(HERE.parents[1] / "orun12"))
sys.path.insert(0, str(HERE.parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from paw_pin import relative  # noqa: E402
from spine_foot import paw_capsules  # noqa: E402

LEGS = (("LH", "c_paw_hl", "hl", -1.0), ("RH", "c_paw_hr", "hr", -1.0))
FLAT_DEG = 10.0
SNAP_DEG_S = 900.0
FLAP_DEG_S = 300.0


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else None


def fmt(v, spec="%+.1f"):
    return "–" if v is None else spec % v


def pad_toe(geoms):
    """(pad, toe) of a paw's capsules: the pad is the larger radius."""

    pad, toe = sorted(geoms, key=lambda g: -g["size_mm"][0])[:2]
    return pad, toe


def world(placements, body, local_mm):
    rot, pos = E._pose(placements, body)
    return [pos[i] + sum(rot[i][k] * local_mm[k] for k in range(3)) for i in range(3)]


def floor_pitch(placements, body, pad, toe):
    """The paw's pitch against the floor, deg, toes up positive (0 when both capsules' lowest points are level)."""

    a, b = world(placements, body, pad["pos_mm"]), world(placements, body, toe["pos_mm"])
    rot, _ = E._pose(placements, body)
    fwd = (rot[0][0], rot[1][0])
    norm = math.hypot(*fwd) or 1.0
    d = [b[i] - a[i] for i in range(3)]
    along = (d[0] * fwd[0] + d[1] * fwd[1]) / norm
    span = math.hypot(along, d[2])
    flat = math.degrees(math.asin((toe["size_mm"][0] - pad["size_mm"][0]) / span))
    return math.degrees(math.atan2(d[2], along)) - flat


def letter(paw_down, heel_down, pitch):
    if paw_down and pitch > FLAT_DEG:
        return "U"
    if paw_down and heel_down:
        return "F"
    if paw_down:
        return "R" if pitch >= -FLAT_DEG else "T"
    return "U" if heel_down else "."


def seed_series(model_geoms, rig, trace):
    frames = [f for f in trace["frames"] if f.get("component_placements")]
    samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
    out = {}
    for leg, paw, foot, sign in LEGS:
        pad, toe = pad_toe(model_geoms[paw])
        sole = E.foot_series(samples, paw, model_geoms[paw], rig["floor_mm"])["height"]
        hb = rig["heels"][paw]
        heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
        pitch = [floor_pitch(p, paw, pad, toe) for _, p in samples]
        pin = [sign * relative(p, foot)[0] for _, p in samples]
        rate = [None] * len(samples)
        for i in range(1, len(samples) - 1):
            dt = samples[i + 1][0] - samples[i - 1][0]
            if dt > 0:
                rate[i] = (pin[i + 1] - pin[i - 1]) / dt
        mark = [letter(s <= E.STANCE_MM, h <= E.STANCE_MM, a) for s, h, a in zip(sole, heel, pitch)]
        out[leg] = {"t": [t for t, _ in samples], "sole": sole, "heel": heel, "pitch": pitch, "pin": pin,
                    "rate": rate, "mark": mark}
    return out


def leg_stats(series, engine_share):
    t, mark = series["t"], series["mark"]
    late = [i for i in range(len(t)) if t[i] >= E.SETTLE_S - 1e-9]
    ground = [i for i in late if mark[i] != "."]
    stance = [i for i in late if series["sole"][i] <= E.STANCE_MM]
    swing = [i for i in late if mark[i] == "." and series["rate"][i] is not None]
    rates = [abs(series["rate"][i]) for i in late if series["rate"][i] is not None]
    swing_rates = [abs(series["rate"][i]) for i in swing]
    row = {"n": len(ground), **{c: sum(1 for i in ground if mark[i] == c) / max(len(ground), 1) for c in "FRTU"}}
    row["heel_share"] = sum(1 for i in stance if mark[i] == "F") / max(len(stance), 1)
    row["engine"] = engine_share
    row["pitch"] = med([series["pitch"][i] for i in stance])
    row["pin"] = med([series["pin"][i] for i in stance])
    row["p95"], row["max"] = pct(rates, 0.95), max(rates) if rates else None
    row["swing_p95"] = pct(swing_rates, 0.95)
    row["swing_fast"] = sum(1 for v in swing_rates if v > SNAP_DEG_S) / max(len(swing_rates), 1)
    # Toe-offs: the last paw-down frame before the paw lifts.
    down = [s <= E.STANCE_MM for s in series["sole"]]
    hdown = [h <= E.STANCE_MM for h in series["heel"]]
    rolls, lift_pin, lift_pitch = [], [], []
    start = late[0] if late else len(t)
    for k in range(start + 1, len(t) - 1):
        if not (down[k] and not down[k + 1]):
            continue
        s = k
        while s > start and (down[s - 1] or hdown[s - 1]):
            s -= 1
        heels = [m for m in range(s, k + 1) if hdown[m]]
        rolls.append(k - heels[-1] if heels else None)
        lift_pin.append(series["pin"][k])
        lift_pitch.append(series["pitch"][k])
    heel_rolls = [r for r in rolls if r is not None]
    row["toeoffs"] = len(rolls)
    row["taps"] = (len(rolls) - len(heel_rolls)) / max(len(rolls), 1)
    row["roll3"] = sum(1 for r in heel_rolls if r >= 3) / max(len(rolls), 1)
    row["roll"] = med(heel_rolls)
    row["lift_pin"], row["lift_pitch"] = med(lift_pin), med(lift_pitch)
    row["lift_up"] = sum(1 for a in lift_pitch if a > FLAT_DEG) / max(len(lift_pitch), 1)
    # Flaps: swing runs whose pin rate reverses at least twice above FLAP_DEG_S.
    flaps = runs = 0
    k = 0
    while k < len(late):
        if mark[late[k]] != ".":
            k += 1
            continue
        run = []
        while k < len(late) and mark[late[k]] == ".":
            run.append(late[k])
            k += 1
        fast = [series["rate"][i] for i in run if series["rate"][i] is not None and abs(series["rate"][i]) > FLAP_DEG_S]
        runs += 1
        flaps += sum(1 for a, b in zip(fast, fast[1:]) if a * b < 0) >= 2
    row["flaps"] = flaps / max(runs, 1)
    return row


def timeline(series, lo, hi):
    t, mark = series["t"], series["mark"]
    span = [i for i in range(len(t)) if lo <= t[i] <= hi and t[i] >= E.SETTLE_S - 1e-9]
    lines = [f"    {t[span[0]]:.2f}-{t[span[-1]]:.2f} s  " + "".join(mark[i] for i in span), ""] if span else []
    lines += ["| stance from s | letters | first F s | heel / paw mm, floor pitch °, pin ° there |", "|---|---|---|---|"]
    k = 0
    while k < len(span):
        if mark[span[k]] == ".":
            k += 1
            continue
        run = []
        while k < len(span) and mark[span[k]] != ".":
            run.append(span[k])
            k += 1
        flat = next((i for i in run if mark[i] == "F"), None)
        where = ("–", "–") if flat is None else (
            f"{t[flat]:.2f}", f"{series['heel'][flat]:.1f} / {series['sole'][flat]:.1f}, "
                              f"{series['pitch'][flat]:+.1f}, {series['pin'][flat]:+.1f}")
        lines.append(f"| {t[run[0]]:.2f} | {''.join(mark[i] for i in run)} | {where[0]} | {where[1]} |")
    return lines


def main(argv):
    seed_arg = None
    if "--seed" in argv:
        k = argv.index("--seed")
        rest = argv[k + 1:]
        seed_arg = (int(rest[0]), float(rest[1]) if len(rest) > 2 else 1.0, float(rest[2]) if len(rest) > 2 else 2.5)
        argv = argv[:k]
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = paw_capsules(model)
    for arg in argv[1:]:
        out = Path(arg)
        evaluation = json.loads((out / "evaluation.json").read_text())
        rig = evaluation["rig"]
        engine = {s["seed"]: s["detail"] for s in evaluation["seeds"]}
        rows = {leg: [] for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            seed = int(path.name.split("-")[1])
            series = seed_series(geoms, rig, json.loads(path.read_text()))
            for leg, paw, *_ in LEGS:
                rows[leg].append(leg_stats(series[leg], engine[seed]["heels"][paw]["heel_down_share"]))
            if seed_arg and seed == seed_arg[0]:
                for leg, *_ in LEGS:
                    print(f"### {out.name} seed {seed}, {leg}\n")
                    print("\n".join(timeline(series[leg], seed_arg[1], seed_arg[2])) + "\n")
        print(f"## {out.name}: the hind paws on their pins (medians over {len(rows['LH'])} seeds)\n")
        print("| leg | on-ground frames F / R / T / U | heel share of stance (engine) | floor pitch ° in stance "
              "| pin ° in stance | toe-offs | taps | roll ≥3 frames | roll median | pin ° / floor pitch ° at lift "
              "| lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | swing > 900 | flapping swings |")
        print("|---|" + "---|" * 14)
        for leg, rs in rows.items():
            m = {k: med([r[k] for r in rs]) for k in rs[0]}
            print(f"| {leg} | {m['F']:.2f} / {m['R']:.2f} / {m['T']:.2f} / {m['U']:.2f} | {m['heel_share']:.2f} "
                  f"({fmt(m['engine'], '%.2f')}) | {fmt(m['pitch'])} | {fmt(m['pin'])} | {m['toeoffs']:.0f} | {m['taps']:.2f} "
                  f"| {m['roll3']:.2f} | {fmt(m['roll'], '%.0f')} | {fmt(m['lift_pin'])} / {fmt(m['lift_pitch'])} "
                  f"| {m['lift_up']:.2f} | {fmt(m['p95'], '%.0f')} / {fmt(max(r['max'] or 0 for r in rs), '%.0f')} "
                  f"| {fmt(m['swing_p95'], '%.0f')} | {m['swing_fast']:.3f} | {m['flaps']:.2f} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
