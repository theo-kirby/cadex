"""The hind paw's sprung pin in the evaluation traces: its angle and how fast it snaps (orun12 P1, O9).

usage: python3 docs/probes/orun12/paw_pin.py EVALUATION_DIR [EVALUATION_DIR ...]

Each EVALUATION_DIR holds ``docs/probes/orun11/judge.py``'s
``seed-*-trace.json``. The pin (``j_pawpin_*``) is passive, so the traces'
``joint_positions`` (the drives only) do not carry it; it is read from the
placements as the paw's rotation relative to the metatarsus about the pin's
lateral (y) axis, zero at the build pose. ``off-axis`` is the largest part
of that relative rotation not about y. Above about 1 deg it means the
reading is not the hinge alone.

Over every frame after the first second, per hind leg, it prints the median
pin angle (deg); the 99th-percentile and largest pin rate (deg/s, a central
difference over ``nominal_time_s``); and the share of frame steps faster
than 900 deg/s, the flapping the owner saw on v06-g1. Standard library only.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402

LEGS = (("LH", "hl"), ("RH", "hr"))
SNAP_DEG_S = 900.0


def relative(placements, foot):
    """(pin angle about y, off-axis angle), deg, of the paw in the metatarsus's frame."""

    meta, _ = E._pose(placements, "c_meta_" + foot)
    paw, _ = E._pose(placements, "c_paw_" + foot)
    r = [[sum(meta[k][i] * paw[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    about_y = math.degrees(math.atan2(r[0][2] - r[2][0], r[0][0] + r[2][2]))
    total = math.degrees(math.acos(max(-1.0, min(1.0, (r[0][0] + r[1][1] + r[2][2] - 1) / 2))))
    return about_y, abs(total - abs(about_y))


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else float("nan")


def main(argv: list[str]) -> None:
    print("| evaluation | leg | frames | pin deg median (min..max) | rate deg/s p99 / max | steps > 900 deg/s | off-axis deg max |")
    print("|---|---|---|---|---|---|---|")
    for arg in argv:
        out = Path(arg)
        rows = {leg: {"angle": [], "rate": [], "off": 0.0} for leg, _ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            frames = [f for f in json.loads(path.read_text())["frames"] if f.get("component_placements")]
            times = [f.get("nominal_time_s") or 0.0 for f in frames]
            for leg, foot in LEGS:
                row = rows[leg]
                pairs = [relative(f["component_placements"], foot) for f in frames]
                angles = [a for a, _ in pairs]
                for i in range(1, len(frames) - 1):
                    if times[i] < E.SETTLE_S - 1e-9 or times[i + 1] <= times[i - 1]:
                        continue
                    row["angle"].append(angles[i])
                    row["rate"].append(abs(angles[i + 1] - angles[i - 1]) / (times[i + 1] - times[i - 1]))
                    row["off"] = max(row["off"], pairs[i][1])
        for leg, _ in LEGS:
            r = rows[leg]
            fast = sum(1 for v in r["rate"] if v > SNAP_DEG_S) / max(len(r["rate"]), 1)
            print(f"| {out.name} | {leg} | {len(r['angle'])} | {statistics.median(r['angle']):+.0f} "
                  f"({min(r['angle']):+.0f}..{max(r['angle']):+.0f}) | {pct(r['rate'], 0.99):.0f} / "
                  f"{max(r['rate']):.0f} | {fast:.3f} | {r['off']:.1f} |")


if __name__ == "__main__":
    main(sys.argv[1:])
