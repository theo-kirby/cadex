"""Settled speed, tilt and left/right drive RMS of speed_judge.py's evaluations.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py EVAL_DIR [EVAL_DIR ...]

``sg_tables.py`` gives the top 2 s window, footfall, heel, U and O9. This
adds what tracking a command needs: per seed, forward speed (along the start
heading, by the engine's ``base_series``) averaged over the episode's last
2 s; the engine's ``mean_forward_speed_mm_s`` and ``max_tilt_deg``; and the
seed-median ``effort_rms_rated_ratio`` of each drive, left against right.
Medians over seeds, with min and max where a spread matters.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexEvaluation as EV  # noqa: E402

WINDOW_S = 2.0
PAIRS = ("fhaa", "scap", "shoulder", "elbow", "wrist", "hhaa", "hip", "knee", "hock")


def last_window_speed(report: dict, seed: dict, out: Path) -> float:
    samples = EV.read_trace(json.loads((out / seed["trace"]["file"]).read_text()))["samples"]
    base = EV.base_series(samples, report["rig"])
    ahead = base["forward"][0]
    end = base["time"][-1]
    picked = [i for i, t in enumerate(base["time"]) if t >= end - WINDOW_S]
    first, last = base["point"][picked[0]], base["point"][picked[-1]]
    span = base["time"][picked[-1]] - base["time"][picked[0]]
    return ((last[0] - first[0]) * ahead[0] + (last[1] - first[1]) * ahead[1]) / span / 1000.0


def summary(out: Path) -> dict:
    report = json.loads((out / "evaluation.json").read_text())
    seeds = report["seeds"]
    settled = [last_window_speed(report, s, out) for s in seeds]
    tilt = [s["metrics"]["max_tilt_deg"] for s in seeds]
    rms: dict[str, list[float]] = {}
    for s in seeds:
        for channel in s["detail"]["drives"]["channels"]:
            if channel["effort_rms_rated_ratio"] is not None:  # a drive with no rating
                rms.setdefault(channel["joint"], []).append(channel["effort_rms_rated_ratio"])
    return {
        "command_mm_s": report["judged_command_mm_s"],
        "last_2s_m_s": (statistics.median(settled), min(settled), max(settled)),
        "mean_forward_m_s": statistics.median(s["metrics"]["mean_forward_speed_mm_s"] for s in seeds) / 1000.0,
        "max_tilt_deg": statistics.median(tilt),
        "upright_pass": sum(t <= 30.0 for t in tilt),
        "falls": sum(s["metrics"]["falls"] > 0 for s in seeds),
        "rms": {joint: statistics.median(values) for joint, values in rms.items()},
    }


def main() -> None:
    rows = [summary(Path(arg)) for arg in sys.argv[1:]]
    print("| command mm/s | " + " | ".join(str(int(r["command_mm_s"])) for r in rows) + " |")
    print("|---|" + "---|" * len(rows))
    print("| last 2 s m/s median (min / max) | " + " | ".join(
        f"{r['last_2s_m_s'][0]:.2f} ({r['last_2s_m_s'][1]:.2f} / {r['last_2s_m_s'][2]:.2f})" for r in rows) + " |")
    print("| mean forward m/s over the episode, median | " + " | ".join(
        f"{r['mean_forward_m_s']:.2f}" for r in rows) + " |")
    print("| max tilt ° median; upright ≤ 30 | " + " | ".join(
        f"{r['max_tilt_deg']:.1f}; {r['upright_pass']}/10" for r in rows) + " |")
    print("| falls | " + " | ".join(str(r["falls"]) for r in rows) + " |")
    print()
    print("RMS over rated, seed median, left / right")
    print()
    print("| drive | " + " | ".join(str(int(r["command_mm_s"])) for r in rows) + " |")
    print("|---|" + "---|" * len(rows))
    for name in PAIRS:
        print(f"| {name} | " + " | ".join(
            f"{r['rms'].get(f'j_{name}_l', float('nan')):.2f} / {r['rms'].get(f'j_{name}_r', float('nan')):.2f}"
            for r in rows) + " |")
    for joint in ("j_spine", "j_spine_yaw", "j_tail1", "j_tail2"):
        print(f"| `{joint}` | " + " | ".join(f"{r['rms'].get(joint, float('nan')):.2f}" for r in rows) + " |")


if __name__ == "__main__":
    main()
