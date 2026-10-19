"""Per-predicate and per-hind-leg tables for judged gallop_spec evaluations (orun12 B1, O3, O4).

usage: python3 docs/probes/orun12/legs.py EVALUATION_DIR [EVALUATION_DIR ...]

Reads each ``evaluation.json`` that ``docs/probes/orun11/judge.py`` wrote
and prints three markdown tables, one row per evaluation:

1. **Predicates**: each of the spec's predicates as passes/seeds and the
   median of its metric over the seeds.
2. **Hind legs, left / right**: the heel's down share of stance, its down
   share at toe-off, its median stance height (mm); the hind overreach
   (mm, median over landings); the touchdown rate (Hz); the stride length
   (mm, the median distance between that paw's consecutive settled
   touchdowns). Each is the median over seeds, and the left/right spread is
   ``|L - R| / max(|L|, |R|)`` (O3/Q1's 20% bar).
3. **Gait and torque**: the top 2 s speed (min / median / max over seeds),
   the share of strides with flight and the median flight time (s), the
   share of fully ordered strides whose footfall is rotary, the stride
   rate (Hz), the worst drive's RMS over rated (median of each seed's worst,
   with the drive that is worst most often), its peak margin (``1 -`` the
   median of each seed's highest peak ratio; 0 is a drive at its clamp),
   and the largest loop-closure gap of any connect row (mm, from judge.py's
   ``closure`` block).

A stride's footfall order is the four paws by first landing inside it
(``CadexEvaluation.flight_metrics``). Read cyclically and started at the
hind pair, it is **rotary** when the fore that follows the leading hind is
on the leading hind's side (LH RH RF LF) and **transverse** when it is on
the other side (LH RH LF RF). A stride where a paw did not land is not
counted. Stance and contact shares already exclude the first second (the
engine's settle). Standard library only.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

HIND = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))
SIDE = {"c_paw_fl": "L", "c_paw_hl": "L", "c_paw_fr": "R", "c_paw_hr": "R"}
SETTLE_S = 1.0


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(value, spec="%.2f"):
    return "–" if value is None else spec % value


def spread(left, right):
    if left is None or right is None or max(abs(left), abs(right)) == 0:
        return None
    return abs(left - right) / max(abs(left), abs(right))


def footfall_kind(order):
    """'rotary', 'transverse' or None, for one stride's paws by first landing."""

    if len(order) != 4 or len(set(order)) != 4:
        return None
    hind = [i for i, n in enumerate(order) if n.endswith(("hl", "hr"))]
    for i in hind:
        if order[(i + 1) % 4] in ("c_paw_hl", "c_paw_hr") and order[(i + 1) % 4] != order[i]:
            lead, fore = order[(i + 1) % 4], order[(i + 2) % 4]
            if fore not in ("c_paw_fl", "c_paw_fr"):
                return None
            return "rotary" if SIDE[fore] == SIDE[lead] else "transverse"
    return None


def stride_length(foot):
    points = [p for t, p in zip(foot.get("touchdowns_s", []), foot.get("touchdown_points_mm", []))
              if t >= SETTLE_S]
    steps = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(points, points[1:])]
    return med(steps)


def load(path: Path):
    report = json.loads((path / "evaluation.json").read_text())
    return report, report["seeds"]


def predicates_row(name, report, seeds):
    cells = []
    for p in report["summary"]["predicates"]:
        value = p["value"]["median"] if isinstance(p.get("value"), dict) else None
        cells.append(f"{p['passed']}/{report['summary']['seeds']} ({fmt(value, '%.3g')})")
    return [name, f"{len(report['summary']['passed'])}/{report['summary']['seeds']}"] + cells


def legs_row(name, seeds):
    values = collections.defaultdict(dict)
    for leg, paw in HIND:
        values["hock down"][leg] = med([s["detail"]["heels"][paw]["heel_down_share"] for s in seeds])
        values["hock at toe-off"][leg] = med([s["detail"]["heels"][paw]["heel_down_at_toeoff_share"]
                                             for s in seeds])
        values["heel stance height mm"][leg] = med([s["detail"]["heels"][paw]["heel_stance_height_mm"]
                                                   for s in seeds])
        values["overreach mm"][leg] = med([(s["detail"]["footfall"]["overreach_mm"].get(leg) or {}).get("median")
                                          for s in seeds])
        values["touchdown Hz"][leg] = med([s["detail"]["footfall"]["touchdown_hz"].get(leg) for s in seeds])
        values["stride mm"][leg] = med([stride_length(s["detail"]["feet"][paw]) for s in seeds])
    cells = [name]
    for key, spec in (("hock down", "%.2f"), ("hock at toe-off", "%.2f"), ("heel stance height mm", "%.0f"),
                      ("overreach mm", "%.0f"), ("touchdown Hz", "%.2f"), ("stride mm", "%.0f")):
        left, right = values[key]["LH"], values[key]["RH"]
        cells.append(f"{fmt(left, spec)} / {fmt(right, spec)} ({fmt(None if spread(left, right) is None else 100 * spread(left, right), '%.0f%%')})")
    return cells


def gait_row(name, report, seeds):
    speed = sorted(s["metrics"]["max_forward_speed_2s_mm_s"] / 1000.0 for s in seeds
                   if s["metrics"].get("max_forward_speed_2s_mm_s") is not None)
    strides = [st for s in seeds for st in s["detail"].get("flight", {}).get("strides", [])]
    kinds = collections.Counter(footfall_kind(st["order"]) for st in strides)
    ordered = kinds["rotary"] + kinds["transverse"]
    worst, names = [], collections.Counter()
    for s in seeds:
        rated = [c for c in s["detail"]["drives"]["channels"] if c.get("effort_rms_rated_ratio") is not None]
        channel = max(rated, key=lambda c: c["effort_rms_rated_ratio"])
        worst.append(channel["effort_rms_rated_ratio"])
        names[channel["joint"]] += 1
    peak = med([s["metrics"]["effort_peak_ratio_max"] for s in seeds])
    gaps = [r["max"] for r in report.get("closure", {}).get("rows", []) if r["kind"] == "connect"
            and r["max"] is not None]
    return [name,
            f"{speed[0]:.2f} / {statistics.median(speed):.2f} / {speed[-1]:.2f}" if speed else "–",
            fmt(med([s["metrics"].get("flight_stride_share") for s in seeds])),
            fmt(med([s["metrics"].get("flight_s_median") for s in seeds]), "%.3f"),
            f"{kinds['rotary']}/{ordered} ({len(strides) - ordered} unordered)" if strides else "–",
            fmt(med([s["metrics"].get("stride_hz_median") for s in seeds])),
            f"{fmt(med(worst))} ({names.most_common(1)[0][0]})",
            fmt(None if peak is None else 1.0 - peak),
            fmt(max(gaps) if gaps else None, "%.1f"),
            str(sum(1 for s in seeds if s["metrics"].get("falls")))]


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def main(argv):
    loaded = [(Path(a).name, *load(Path(a))) for a in argv]
    ids = [p["id"] for p in loaded[0][1]["summary"]["predicates"]]
    print(table(["evaluation", "pass"] + ids, [predicates_row(n, r, s) for n, r, s in loaded]))
    print()
    print(table(["evaluation", "hock down LH / RH (spread)", "hock at toe-off", "heel stance height mm",
                 "overreach mm", "touchdown Hz", "stride mm"], [legs_row(n, s) for n, _, s in loaded]))
    print()
    print(table(["evaluation", "top 2 s m/s min / med / max", "flight stride share", "flight s",
                 "rotary strides", "stride Hz", "worst RMS/rated", "peak margin", "loop gap max mm", "falls"],
                [gait_row(n, r, s) for n, r, s in loaded]))


if __name__ == "__main__":
    main(sys.argv[1:])
