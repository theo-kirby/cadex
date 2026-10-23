"""orun19 S2: re-read judged speed evaluations under the owner's revised O3.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py EVAL_ROOT LABEL [LABEL ...]

O3 as revised (owner, 2026-10-23): a seed misses its command only when its
speed over the last 2 s (``b1_summary.last_window_speed``) is more than 10%
under the command; running over it is never a miss. A policy tracks a
command when every judged seed there makes at least 0.9 of it and none
falls. Its top is the highest command it tracks with every lower judged
command tracked too. Each LABEL reads ``EVAL_ROOT/LABEL-<cmd>`` for every
command evaluated; nothing is re-run.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun18"))

from b1_summary import last_window_speed  # noqa: E402

FLOOR = 0.9


def command_row(out: Path) -> dict:
    report = json.loads((out / "evaluation.json").read_text())
    cmd = float(report["judged_command_mm_s"]) / 1000.0
    speeds = [last_window_speed(report, s, out) for s in report["seeds"]]
    falls = sum(1 for s in report["seeds"] if s["metrics"]["falls"] or not s["metrics"]["completed"])
    made = sum(1 for v in speeds if v >= FLOOR * cmd)
    return {"cmd": cmd, "median": statistics.median(speeds), "min": min(speeds), "max": max(speeds),
            "min_ratio": min(speeds) / cmd, "made": made, "seeds": len(speeds), "falls": falls,
            "tracks": made == len(speeds) and falls == 0, "policy": report["policy_sha256"][:8]}


def main(argv: list[str]) -> int:
    root = Path(argv[0]).expanduser()
    for label in argv[1:]:
        rows = sorted((command_row(d) for d in root.glob(f"{label}-*")
                       if d.name[len(label) + 1:].isdigit()), key=lambda r: r["cmd"])
        top = None
        for r in rows:
            if not r["tracks"]:
                break
            top = r
        print(f"## {label} (policy {rows[0]['policy']})")
        print("| command m/s | median (min / max) | min / command | seeds >= 0.9 cmd | falls | tracks |")
        print("|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['cmd']:.1f} | {r['median']:.2f} ({r['min']:.2f} / {r['max']:.2f}) | {r['min_ratio']:.3f} "
                  f"| {r['made']}/{r['seeds']} | {r['falls']} | {'yes' if r['tracks'] else 'no'} |")
        if top is None:
            print("top: none (the lowest command is missed)\n")
        else:
            n = sum(1 for r in rows if r["cmd"] <= top["cmd"])
            print(f"top: {top['cmd']:.1f} m/s commanded, {n} commands tracked from {rows[0]['cmd']:.1f}; "
                  f"held {top['median']:.2f} m/s median ({top['min']:.2f} min)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
