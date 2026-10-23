"""The hind paw pins' share of time at their home stop, from judged evaluations' traces.

usage: pixi run python docs/probes/orun18/pin_stop.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

C3's bundle asks for the paw pin at its stop on 0.61-0.73 of the clip's
samples (``c3-task.md``), so ``track_pose`` may pay a policy to hold the paw
shut. This reads what the policy did: ``j_pawpin_l`` / ``j_pawpin_r``, by
``orun13/spine_foot.py``'s ``joint_reader`` (the angle about the joint's axis
from the placements), over frames from the engine's settle (1 s) on. Per leg,
the seed median of the share of frames within ``STOP_DEG`` (1 deg) of the pin's
home stop (0 deg; the spring's ``springref`` sits past it), of the frames in
stance (paw sole within the engine's ``STANCE_MM``), and of the pin's
5th-95th percentile range. Writes nothing.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
_spec = importlib.util.spec_from_file_location("spine_foot", HERE.parents[1] / "orun13" / "spine_foot.py")
SF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SF)
E = SF.E

PINS = {"LH": ("j_pawpin_l", "c_paw_hl"), "RH": ("j_pawpin_r", "c_paw_hr")}
STOP_DEG = 1.0


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * (len(values) - 1) + 0.5))]


def leg_rows(model, out: Path):
    evaluation = json.loads((out / "evaluation.json").read_text())
    geoms = SF.paw_capsules(model)
    rows = {leg: [] for leg in PINS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        frames = [f for f in trace["frames"] if f.get("component_placements")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        late = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
        if not late:
            continue
        for leg, (joint, paw) in PINS.items():
            read, (lo, hi) = SF.joint_reader(model, joint)
            home = 0.0
            q = [read(samples[i][1]) for i in late]
            sole = E.foot_series(samples, paw, geoms[paw], evaluation["rig"]["floor_mm"])["height"]
            stance = [k for k, i in enumerate(late) if sole[i] is not None and sole[i] <= E.STANCE_MM]
            stop = [abs(v - home) <= STOP_DEG for v in q]
            rows[leg].append({"stop": sum(stop) / len(q),
                              "stance_stop": sum(stop[k] for k in stance) / max(len(stance), 1),
                              "range": abs(pct(q, 0.95) - pct(q, 0.05)), "limits": (lo, hi)})
    return evaluation.get("judged_command_mm_s"), rows


def main(argv):
    model = mujoco.MjModel.from_xml_path(argv[0])
    print("| evaluation | command mm/s | pin at its stop LH / RH | in stance LH / RH | p5-p95 range ° LH / RH |")
    print("|---|---|---|---|---|")
    for arg in argv[1:]:
        cmd, rows = leg_rows(model, Path(arg))
        med = {leg: {k: statistics.median(r[k] for r in rows[leg]) for k in ("stop", "stance_stop", "range")}
               for leg in PINS}
        print(f"| {Path(arg).name} | {cmd} | {med['LH']['stop']:.2f} / {med['RH']['stop']:.2f} | "
              f"{med['LH']['stance_stop']:.2f} / {med['RH']['stance_stop']:.2f} | "
              f"{med['LH']['range']:.1f} / {med['RH']['range']:.1f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
