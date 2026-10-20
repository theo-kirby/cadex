"""The hind hock's angle in stance against the clip's heel-down ankle angle (orun12 P1, O2a).

usage: python3 docs/probes/orun12/hock_stance.py EVALUATION_DIR [EVALUATION_DIR ...]

For each evaluation that ``docs/probes/orun11/judge.py`` wrote, reads the
seed traces and the judged bundle (``judged-task.json``) and prints, per
hind leg, the 10th / 50th / 90th percentile of the hock drive's angle (deg)
over the frames where that hind paw sits lowest (its lowest quarter of
frames after the first second, a stance proxy that needs no contact flag),
beside the clip's ankle-pin angle over the samples where the clip holds the
heel down. The hock drives the ankle pin 1:1 through the push-rod
parallelogram (``track_pose`` reads ``q_hock - q_ankle_ref``), so the two
compare directly. The right leg's sign is folded onto the left's.

Superseded (orun12 iteration 9, ``heel5-pitch.md``): only 29-67% of the
lowest-quarter frames are the engine's stance frames, and on those the
hock sits past the clip's angle, not short of it. Use ``stance_pose.py``.

A trace's ``joint_positions`` are the actuated joints, in degrees, in the
order of its ``actuator_channels``. Standard library only.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

LEGS = (("LH", "l", 1.0), ("RH", "r", -1.0))


def clip_heel_angles(task: dict, side: str, sign: float) -> list[float]:
    ref = task["reference"]
    joint = ref["joints"].index("j_ankle_" + side)
    down = ref["heels"]["LH" if side == "l" else "RH"]["down"]
    return [sign * math.degrees(a[joint]) for a, d in zip(ref["joint_angles_rad"], down) if d]


def stance_hock(out: Path, side: str, sign: float) -> list[float]:
    values = []
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        names = [c["joint"] if isinstance(c, dict) else c for c in trace["actuator_channels"]]
        hock = names.index("j_hock_" + side)
        frames = [f for f in trace["frames"] if (f.get("nominal_time_s") or 0.0) >= 1.0 and f.get("joint_positions")]
        z = [f["component_placements"]["c_paw_h" + side]["position_mm"][2] for f in frames]
        low = sorted(z)[len(z) // 4]
        values += [sign * f["joint_positions"][hock] for f, zi in zip(frames, z) if zi <= low]
    return values


def main(argv: list[str]) -> None:
    print("| evaluation | leg | hock in stance p10 / p50 / p90 deg | clip ankle, heel down, min / max deg | median gap deg |")
    print("|---|---|---|---|---|")
    for arg in argv:
        out = Path(arg)
        task = json.loads((out / "judged-task.json").read_text())
        for leg, side, sign in LEGS:
            q = stance_hock(out, side, sign)
            p10, _, _, _, p50, _, _, _, p90 = statistics.quantiles(q, n=10)
            clip = clip_heel_angles(task, side, sign)
            gap = p50 - statistics.median(clip)
            print(f"| {out.name} | {leg} | {p10:.0f} / {p50:.0f} / {p90:.0f} | {min(clip):.0f} / {max(clip):.0f} | {gap:+.0f} |")


if __name__ == "__main__":
    main(sys.argv[1:])
