"""orun13 O1/O2: can the hind leg reach a flat sole, or does the policy choose toes-up?

usage: pixi run python docs/probes/orun13/hind_reach.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

MODEL_XML is the run's ``train/cat_model-model.xml``; each EVALUATION_DIR is
``docs/probes/orun11/judge.py``'s output (``evaluation.json`` and
``seed-*-trace.json``). Frames from the engine's settle (1 s) on.

Each hind leg's frames are sorted by ``spine_foot.py``'s foot reading:
**flat** (heel and paw within the engine's stance height), **toes-up** (heel
down, paw up: the O2 fault) and **toe** (paw down, heel up). For each class
the probe gives the median hip, knee and hock angle, in the left leg's sign
(the right leg's joints are mirrored, so its readings are negated) with the
passive metatarsus joint ``j_ankle`` read from the placements, the
median margin of each to its nearer stop, the share of frames within 2 deg
of a stop, the hock's commanded-minus-measured angle (positive: the command
asks for more hock than the joint holds) and the hock drive's effort over
peak.

Above that, the clip's own median hip, knee and ankle over its heel-down
samples (from the evaluation's ``judged-task.json``), the targets the
tracking terms pull the stance towards.

What it answers: if a toes-up frame's hock sits at its stop, or its drive at
peak with the command past the measurement, the leg cannot reach a flat sole
there (a model or clip limit, O1). If the hock has margin and the command
matches the measurement, the policy chose the toes-up foot.

Writes nothing; prints a markdown table, left and right apart (O5).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from spine_foot import joint_reader, paw_capsules  # noqa: E402

STOP_DEG = 2.0
LEGS = (("LH", "c_paw_hl", "l", 1.0), ("RH", "c_paw_hr", "r", -1.0))
JOINTS = ("hip", "knee", "hock")


def med(values):
    return statistics.median(values) if values else None


def fmt(v, spec="%+.1f"):
    return "–" if v is None else spec % v


def collect(model, out: Path):
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    floor = rig["floor_mm"]
    paws = paw_capsules(model)
    ankles = {side: joint_reader(model, f"j_ankle_{side}")[0] for _, _, side, _ in LEGS}
    rows = {leg: {c: [] for c in ("flat", "toes-up", "toe")} for leg, *_ in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        channels = trace["actuator_channels"]
        index = {c["joint"]: i for i, c in enumerate(channels)}
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        for leg, paw, side, sign in LEGS:
            sole = E.foot_series(samples, paw, paws[paw], floor)["height"]
            heel_body = rig["heels"][paw]
            heel = E.foot_series(samples, heel_body["body"], heel_body["geoms"], floor)["height"]
            for k, f in enumerate(frames):
                if samples[k][0] < E.SETTLE_S - 1e-9:
                    continue
                h, p = heel[k] <= E.STANCE_MM, sole[k] <= E.STANCE_MM
                cls = "flat" if h and p else "toes-up" if h else "toe" if p else None
                if cls is None:
                    continue
                rec = {}
                for j in JOINTS:
                    c = channels[index[f"j_{j}_{side}"]]
                    q = f["joint_positions"][index[f"j_{j}_{side}"]]
                    lo, hi = c["low"], c["high"]
                    rec[j] = sign * q
                    rec[j + "_margin"] = min(q - lo, hi - q)
                    rec[j + "_stop"] = rec[j + "_margin"] <= STOP_DEG
                i = index[f"j_hock_{side}"]
                rec["hock_cmd_err"] = sign * (f["actuator_commands"][i] - f["joint_positions"][i])
                rec["hock_effort"] = abs(f["actuator_efforts"][i]) / channels[i]["effort_high"]
                rec["ankle"] = sign * ankles[side](samples[k][1])
                rec["tilt"] = sole[k] - heel[k]
                rows[leg][cls].append(rec)
    return rows


def clip_targets(task_path: Path):
    """The clip's hip, knee and ankle over its own heel-down samples, per hind leg, in the left sign."""

    import math

    ref = json.loads(task_path.read_text())["reference"]
    names, angles = ref["joints"], ref["joint_angles_rad"]
    out = {}
    for leg, _, side, sign in LEGS:
        down = [k for k, d in enumerate(ref["heels"][leg]["down"]) if d]
        out[leg] = {j: med([sign * math.degrees(angles[k][names.index(f"j_{j}_{side}")]) for k in down])
                    for j in ("hip", "knee", "ankle")}
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    for arg in argv[1:]:
        out = Path(arg)
        rows = collect(model, out)
        print(f"## {out.name}\n")
        task = out / "judged-task.json"
        if task.exists():
            print("| leg | clip heel-down hip / knee / ankle deg (left sign) |\n|---|---|")
            for leg, c in clip_targets(task).items():
                print(f"| {leg} | {fmt(c['hip'])} / {fmt(c['knee'])} / {fmt(c['ankle'])} |")
            print()
        print("| leg | class | frames | hip / knee / hock / ankle deg (left sign) | margin to stop hip / knee / hock deg "
              "| at a stop (≤2°) hip / knee / hock | hock cmd − meas deg | hock effort / peak med / p95 "
              "| tilt mm |")
        print("|---|---|---|---|---|---|---|---|---|")
        for leg, *_ in LEGS:
            for cls, recs in rows[leg].items():
                if not recs:
                    print(f"| {leg} | {cls} | 0 |" + " – |" * 6)
                    continue
                m = {k: med([r[k] for r in recs]) for k in recs[0] if not k.endswith("_stop")}
                stop = {j: sum(r[j + "_stop"] for r in recs) / len(recs) for j in JOINTS}
                eff = sorted(r["hock_effort"] for r in recs)
                p95 = eff[min(len(eff) - 1, int(0.95 * len(eff)))]
                print(f"| {leg} | {cls} | {len(recs)} | {fmt(m['hip'])} / {fmt(m['knee'])} / {fmt(m['hock'])} / {fmt(m['ankle'])} "
                      f"| {fmt(m['hip_margin'], '%.1f')} / {fmt(m['knee_margin'], '%.1f')} / {fmt(m['hock_margin'], '%.1f')} "
                      f"| {stop['hip']:.2f} / {stop['knee']:.2f} / {stop['hock']:.2f} | {fmt(m['hock_cmd_err'])} "
                      f"| {m['hock_effort']:.2f} / {p95:.2f} | {fmt(m['tilt'])} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
