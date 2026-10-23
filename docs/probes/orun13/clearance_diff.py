"""orun13 O1: compare two builds' clearance reports pair by pair, so a model change shows it adds no failing pair.

usage: python3 docs/probes/orun13/clearance_diff.py BEFORE_DIR AFTER_DIR [JOINT_SUBSTRING ...]

Each DIR holds a copy of a revision's ``docs/clearance.md`` (``cadex
clearance``) and ``docs/clearance-sweep.md`` (``cadex clearance --sweep``).
A static pair fails on any verdict but ``clear``. A swept pair fails if, at any joint's sample, its
common volume is above the CLI's default 1e-6 mm³ (``--max-common-volume-mm3``).
Prints each build's failing static and swept pairs, the pairs only one of them fails, and, for
each joint whose name holds a JOINT_SUBSTRING, its range and the five nearest
moving pairs it sweeps.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VOLUME = 1e-6


def sweep(directory: Path) -> dict:
    text = (directory / "clearance-sweep.md").read_text()
    start = text.index("```json") + len("```json")
    return json.loads(text[start:text.index("```", start)])


def failing(report: dict) -> dict:
    out = {}
    for joint in report["joints"]:
        for pair in joint.get("pairs", []):
            if (pair.get("maximum_common_volume_mm3") or 0.0) > VOLUME:
                key = tuple(sorted((pair["first"], pair["second"])))
                out[key] = max(out.get(key, 0.0), pair["maximum_common_volume_mm3"])
    return out


def static(directory: Path) -> dict:
    out = {}
    for line in (directory / "clearance.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[4] not in ("clear", "verdict") and not set(cells[4]) <= set("-"):
            out[tuple(sorted(cells[:2]))] = cells[4]
    return out


def main(argv: list[str]) -> int:
    sb, sa = static(Path(argv[1])), static(Path(argv[2]))
    print(f"static pairs failing: before {len(sb)}, after {len(sa)}")
    for key in sorted(set(sa) - set(sb)):
        print(f"  new: {key[0]} / {key[1]}  {sa[key]}")
    for key in sorted(set(sb) - set(sa)):
        print(f"  gone: {key[0]} / {key[1]}  {sb[key]}")
    before, after = sweep(Path(argv[1])), sweep(Path(argv[2]))
    fb, fa = failing(before), failing(after)
    print(f"swept pairs failing: before {len(fb)}, after {len(fa)}")
    for name, only in (("only before", set(fb) - set(fa)), ("only after (new)", set(fa) - set(fb))):
        print(f"{name}: {len(only)}")
        for key in sorted(only):
            print(f"  {key[0]} / {key[1]}  {max(fb.get(key, 0.0), fa.get(key, 0.0)):.1f} mm3")
    for tag in argv[3:]:
        for label, report in (("before", before), ("after", after)):
            for joint in report["joints"]:
                if tag not in joint["joint"]:
                    continue
                pairs = sorted(joint.get("pairs", []), key=lambda p: p["minimum_distance_mm"])[:5]
                near = ", ".join(f"{p['first']}/{p['second']} {p['minimum_distance_mm']:.1f}" for p in pairs)
                print(f"{label} {joint['joint']} range {joint.get('reached_degrees')}: {near}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
