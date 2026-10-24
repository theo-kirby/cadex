"""What each judged seed drew at reset, beside how far it tilted (orun19 L1, seed 1007).

usage: python3 docs/probes/orun19/reset_draws.py EVAL_DIR [EVAL_DIR ...]

For every seed of each evaluation: the mass factor and the reset kick (linear
speed and angular-velocity norm) from ``evaluation.json``'s ``drawn``; the
chest's pitch and height at frame 0 of the seed's trace (the start pose, the
reference at the seed's drawn start phase); the chest's largest pitch in the
first 0.42 s; the whole episode's ``max_tilt_deg`` and its length. Reads only
the evaluation's own files, standard library only.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def pitch_deg(placement):
    x, y, z, w = placement["rotation_xyzw"]
    return math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))


def main(argv):
    for path in argv:
        root = Path(path).expanduser()
        report = json.loads((root / "evaluation.json").read_text(encoding="utf-8"))
        print(f"{root.name}  policy {str(report.get('policy_sha256'))[:8]}")
        print("  seed  mass   kick m/s  kick rad/s  start pitch°  start z mm  pitch max° (0.42 s)  max tilt°  s")
        for seed in report["seeds"]:
            drawn = seed["drawn"]
            kick = drawn["reset_variation"][0]
            mass = drawn["randomisation"][0]["factor"]
            spin = math.sqrt(sum(v * v for v in kick["angular_velocity_rad_s"]))
            trace = json.loads((root / f"seed-{seed['seed']}-trace.json").read_text(encoding="utf-8"))
            chest = [f["component_placements"]["c_chest_frame"] for f in trace["frames"][:22]]
            metrics = seed["metrics"]
            print(f"  {seed['seed']}  {mass:.3f}  {kick['linear_speed_m_s']:.3f}     {spin:.3f}       "
                  f"{pitch_deg(chest[0]):+6.1f}       {chest[0]['position_mm'][2]:+5.0f}       "
                  f"{max(pitch_deg(c) for c in chest):+6.1f}              "
                  f"{metrics['max_tilt_deg']:5.1f}    {metrics['duration_s']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
