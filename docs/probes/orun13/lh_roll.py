"""orun13 P1 (O2): the clip's late hind stance against the policy's roll to toe-off.

usage: pixi run python docs/probes/orun13/lh_roll.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

``hock_at_toeoff`` passes a stance only if the heel is within ``STANCE_MM``
in its last ``HEEL_TOEOFF_S`` (the lift frame and the two before it), so a
foot that rolls onto its toes for three frames or more before lifting fails.
``toeoff_term.py`` found LH does that (a 3-frame roll) while RH taps. This
asks whether the clip itself asks for the roll.

**The clip** (the evaluation's ``judged-task.json``): per hind leg, its
samples from two before the last heel-down sample to two after, with the
heel's and the paw's height (the paw's from ``foot_positions_m`` less its
stance value) and the hip, knee and ankle reference (left sign; the hock
tracks the ankle reference in ``track_pose``). ``heel_expr.py`` reads the
clip's sole pitch; this reads heights only. The clip's own roll is its
samples with the paw down
and the heel up before the paw lifts.

**The traces** (the engine's ``foot_series`` on paw and heel geoms, after
the 1 s settle): for each toe-off, frames aligned on the lift frame (the
last frame the paw is down): the roll length (frames from the last heel-down
frame to the lift), and, at offsets -4..0, the median heel and paw height,
hock and metatarsus angle (left sign; ``j_ankle`` read from placements),
the hock's command minus measurement and its effort over peak.

What it answers: if the clip lifts heel and paw within a frame and the
policy holds the paw down for three, the roll is the policy's, against the
clip, and a term or a clip change that ends the paw's stance with the heel
is the lever. If the clip itself rolls, the clip is. Writes nothing; left
and right apart (O5).

**The candidate term** (O7: scored per step before it trains),
``roll_brake``, charges the hock's heel-up speed while the paw is down and
the heel is up (the roll), in the left sign:

    chl_down * (1 - khl_down) * (dq_hock_l + abs(dq_hock_l)) / 2 / 500   (RH: -dq_hock_r)

``dq_*`` is deg/s; the trace's is the hock angle differenced over a frame.
Per leg it prints the term's mean per on-ground frame, its mean on the roll
frames (heel up, paw down, in the 40 ms that ``hock_at_toeoff`` reads) and
on the other toe-stance frames, and on the clip's own samples.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from spine_foot import joint_reader, paw_capsules  # noqa: E402

LEGS = (("LH", "c_paw_hl", "l", 1.0), ("RH", "c_paw_hr", "r", -1.0))
OFFSETS = (-4, -3, -2, -1, 0)
BRAKE_DEG_S = 500.0


def brake(heel_up_speed):
    return max(heel_up_speed, 0.0) / BRAKE_DEG_S


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(v, spec="%+.1f"):
    return "–" if v is None else spec % v


def clip_rows(task_path: Path):
    ref = json.loads(task_path.read_text())["reference"]
    names, angles = ref["joints"], ref["joint_angles_rad"]
    n = len(angles)
    out = {}
    for leg, _, side, sign in LEGS:
        heel_down = ref["heels"][leg]["down"]
        contact = ref["contact"][leg]
        paw_z = [p[2] for p in ref["foot_positions_m"][leg]]
        stance_z = min(paw_z)
        # The last heel-down sample of the stance: heel down here, not at the next.
        last = next(k for k in range(n) if heel_down[k] and not heel_down[(k + 1) % n])
        rows = []
        for d in range(-2, 4):
            k = (last + d) % n
            q = {j: sign * math.degrees(angles[k][names.index(f"j_{j}_{side}")]) for j in ("hip", "knee", "ankle")}
            k1 = (k - 1) % n
            speed = (q["ankle"] - sign * math.degrees(angles[k1][names.index(f"j_ankle_{side}")])) / ref["sample_dt_s"]
            paw_down = 1000 * (paw_z[k] - stance_z) <= E.STANCE_MM
            heel_up = 1000 * ref["heels"][leg]["height_m"][k] > E.STANCE_MM
            rows.append({"brake": brake(speed) if paw_down and heel_up else 0.0, "d": d, "k": k, "contact": contact[k], "heel_down": heel_down[k],
                         "heel_mm": 1000 * ref["heels"][leg]["height_m"][k],
                         "paw_mm": 1000 * (paw_z[k] - stance_z), **q})
        out[leg] = rows
    return out


def trace_rolls(model, out: Path):
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    floor = rig["floor_mm"]
    paws = paw_capsules(model)
    ankles = {side: joint_reader(model, f"j_ankle_{side}")[0] for _, _, side, _ in LEGS}
    rolls = {leg: [] for leg, *_ in LEGS}
    at = {leg: {d: [] for d in OFFSETS} for leg, *_ in LEGS}
    term = {leg: {"ground": [], "roll": [], "toe": []} for leg, *_ in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        channels = trace["actuator_channels"]
        index = {c["joint"]: i for i, c in enumerate(channels)}
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        start = next(i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9)
        for leg, paw, side, sign in LEGS:
            sole = E.foot_series(samples, paw, paws[paw], floor)["height"]
            hb = rig["heels"][paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], floor)["height"]
            down = [s <= E.STANCE_MM for s in sole]
            hdown = [h <= E.STANCE_MM for h in heel]
            i = index[f"j_hock_{side}"]
            in_roll = set()
            values = {}
            for k in range(start, len(frames)):
                if not (down[k] or hdown[k]):
                    continue
                dt = samples[k][0] - samples[k - 1][0]
                speed = sign * (frames[k]["joint_positions"][i] - frames[k - 1]["joint_positions"][i]) / dt
                values[k] = brake(speed) if down[k] and not hdown[k] else 0.0
            for k in range(start + 4, len(frames) - 1):
                if not (down[k] and not down[k + 1]):
                    continue
                # Stance start: walk back over frames with paw or heel down.
                s = k
                while s > start and (down[s - 1] or hdown[s - 1]):
                    s -= 1
                heel_frames = [m for m in range(s, k + 1) if hdown[m]]
                roll = k - heel_frames[-1] if heel_frames else None   # None: a tap
                rolls[leg].append(roll)
                in_roll.update(m for m in range(max(s, k - 2), k + 1) if down[m] and not hdown[m])
                for d in OFFSETS:
                    m = k + d
                    if m < s:
                        continue
                    f = frames[m]
                    at[leg][d].append({
                        "heel": heel[m], "paw": sole[m],
                        "hock": sign * f["joint_positions"][i],
                        "ankle": sign * ankles[side](samples[m][1]),
                        "cmd_err": sign * (f["actuator_commands"][i] - f["joint_positions"][i]),
                        "effort": abs(f["actuator_efforts"][i]) / channels[i]["effort_high"]})
            for k, v in values.items():
                term[leg]["ground"].append(v)
                if k in in_roll:
                    term[leg]["roll"].append(v)
                elif down[k] and not hdown[k]:
                    term[leg]["toe"].append(v)
    return rolls, at, term


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    first = True
    for arg in argv[1:]:
        out = Path(arg)
        if first:
            print("## The clip, around its last heel-down sample\n")
            print("| leg | sample (d) | paw down | heel down | heel mm | paw mm | hip / knee / ankle ° (left sign) | roll_brake |")
            print("|---|---|---|---|---|---|---|---|")
            for leg, rows in clip_rows(out / "judged-task.json").items():
                for r in rows:
                    print(f"| {leg} | {r['k']} ({r['d']:+d}) | {r['contact']} | {r['heel_down']} | {r['heel_mm']:.1f} | {r['paw_mm']:.1f} "
                          f"| {fmt(r['hip'])} / {fmt(r['knee'])} / {fmt(r['ankle'])} | {r['brake']:.2f} |")
            print()
            first = False
        rolls, at, term = trace_rolls(model, out)
        print(f"## {out.name}\n")
        print("| leg | toe-offs | taps (no heel down) | roll frames 0 / 1 / 2 / ≥3 | roll median (heel stances) |")
        print("|---|---|---|---|---|")
        for leg, rs in rolls.items():
            heel = [r for r in rs if r is not None]
            c = Counter(min(r, 3) for r in heel)
            tot = max(len(rs), 1)
            print(f"| {leg} | {len(rs)} | {(len(rs) - len(heel)) / tot:.2f} | "
                  + " / ".join(f"{c[v] / tot:.2f}" for v in (0, 1, 2, 3)) + f" | {fmt(med(heel), '%.0f')} |")
        print()
        print("| leg | frame vs lift | n | heel mm | paw mm | hock ° | metatarsus ° | hock cmd − meas ° | effort / peak |")
        print("|---|---|---|---|---|---|---|---|---|")
        for leg, by in at.items():
            for d in OFFSETS:
                recs = by[d]
                m = {key: med([r[key] for r in recs]) for key in ("heel", "paw", "hock", "ankle", "cmd_err", "effort")}
                print(f"| {leg} | {d:+d} | {len(recs)} | {fmt(m['heel'], '%.1f')} | {fmt(m['paw'], '%.1f')} | {fmt(m['hock'])} "
                      f"| {fmt(m['ankle'])} | {fmt(m['cmd_err'])} | {fmt(m['effort'], '%.2f')} |")
        print()
        print("| leg | roll_brake mean per on-ground frame | on roll frames (n) | on other toe frames (n) |")
        print("|---|---|---|---|")
        for leg, t in term.items():
            mean = lambda xs: sum(xs) / len(xs) if xs else 0.0  # noqa: E731
            print(f"| {leg} | {mean(t['ground']):.3f} | {mean(t['roll']):.2f} ({len(t['roll'])}) | {mean(t['toe']):.2f} ({len(t['toe'])}) |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
