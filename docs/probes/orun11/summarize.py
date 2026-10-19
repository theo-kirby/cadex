"""One table row per judged checkpoint, read from its evaluation.json (judge.py's output).

usage: python3 docs/probes/orun11/summarize.py EVALUATION_DIR [EVALUATION_DIR ...]

Medians over the seeds. Per hind leg: the hock case's down share of stance,
its down share at toe-off, its median stance height (mm) and the sole's
median stance pitch (deg, toes-down positive), from each seed's
``detail.heels``. Touchdown rates per paw (Hz) and the stride rate from
``detail.footfall``. The worst drive is each seed's highest RMS over rated,
then the median of those (drives with no rated torque skipped), with the drive that is worst most often; the peak
ratio is the median of each seed's highest peak ratio (1.00 is a drive at its clamp, a
peak margin of 0). The failing predicates are the ones under 10 seeds, with
their median and pass count. Standard library only.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

LEGS = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))
PAWS = ("LF", "RF", "LH", "RH")


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else float("nan")


def row(path: Path) -> str:
    report = json.loads((path / "evaluation.json").read_text())
    summary, seeds = report["summary"], report["seeds"]
    failing = [f"{p['id']} {p['value']['median']:.3g} ({p['passed']}/10)"
               for p in summary["predicates"] if p["passed"] < summary["seeds"]]
    # a seed that ends before 2 s of travel has no 2 s average; as the engine's predicate does, skip it
    speed = sorted(s["metrics"]["max_forward_speed_2s_mm_s"] / 1000.0 for s in seeds
                   if s["metrics"]["max_forward_speed_2s_mm_s"] is not None) or [float("nan")]
    heel = {leg: [s["detail"]["heels"][paw] for s in seeds] for leg, paw in LEGS}
    rates = {k: med([s["detail"]["footfall"]["touchdown_hz"].get(k) for s in seeds]) for k in PAWS}
    stride = med([s["detail"]["footfall"]["stride_hz"] for s in seeds])
    worst, names = [], collections.Counter()
    for s in seeds:
        rated = [c for c in s["detail"]["drives"]["channels"] if c.get("effort_rms_rated_ratio") is not None]
        channel = max(rated, key=lambda c: c["effort_rms_rated_ratio"])
        worst.append(channel["effort_rms_rated_ratio"])
        names[channel["joint"]] += 1
    peak = med([s["metrics"]["effort_peak_ratio_max"] for s in seeds])
    falls = sum(1 for s in seeds if s["metrics"].get("falls"))

    def per_leg(key, fmt):
        return " / ".join(fmt % med([h[key] for h in heel[leg]]) for leg, _ in LEGS)

    return " | ".join([
        path.name,
        f"{len(summary['passed'])}/{summary['seeds']}",
        "; ".join(failing) or "none",
        f"{speed[0]:.2f} / {statistics.median(speed):.2f} / {speed[-1]:.2f}",
        per_leg("heel_down_share", "%.2f"),
        per_leg("heel_down_at_toeoff_share", "%.2f"),
        per_leg("heel_stance_height_mm", "%.0f"),
        per_leg("sole_pitch_deg_median", "%.0f"),
        " ".join(f"{rates[k]:.2f}" for k in PAWS),
        f"{stride:.2f}",
        f"{med(worst):.2f} ({names.most_common(1)[0][0]})",
        f"{peak:.2f}",
        str(falls),
    ])


def main(argv):
    print("checkpoint | pass | failing (median, passes) | top 2 s m/s min / med / max | hock down LH / RH"
          " | hock at toe-off LH / RH | hock stance height LH / RH mm | sole LH / RH deg"
          " | touchdown Hz LF RF LH RH | stride Hz | worst RMS/rated | peak ratio | falls")
    for arg in argv:
        print(row(Path(arg)))


if __name__ == "__main__":
    main(sys.argv[1:])
