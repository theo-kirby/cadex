"""Footfall, flight, heel pad and O6 of speed_judge.py's evaluations on leo v06.

usage: python3 docs/probes/orun19/s1_tables.py EVAL_DIR [EVAL_DIR ...]

``orun17/sg_tables.py`` reads the hind paw on its pin (``orun14/paw_floor``),
and v06 has no pin, toes or second paw capsule, so it does not apply. This
reads only the engine's evaluation (``evaluation.json``), no trace:

* **footfall order**: for each left-hind stride (touchdown to touchdown,
  t >= 4 s) the phase of RH's, LF's and RF's first touchdown in it, pooled
  over seeds, median; with each foot's touchdown Hz and median step advance
  (left against right);
* **flight**: the engine's ``flight_stride_share`` and ``flight_s_median``;
* **the heel pad**: the engine's ``heel_down_share`` per hind leg, which on
  v06 reads ``c_heel_h*`` (the pad behind the hock, the task's ``heels``)
  within ``STANCE_MM`` over the ball's settled stance, and the pad's median
  stance height;
* **O6**: the worst drive's RMS over rated and the peak margin, the drives
  at their clamp on >= 0.05 of frames (seed median), falls, non-finite
  metrics, and the closure: the hind rod loops (``connect``, mm) and the
  spine and tail cables (``joint``, deg), each its max over seeds.
"""

from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from pathlib import Path

FROM_S = 4.0
AT_PEAK_SHARE = 0.05
FEET = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}
HEELS = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(v, spec="%.2f"):
    return "–" if v is None else spec % v


def finite(value):
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite(v) for v in value)
    return not (isinstance(value, float) and not math.isfinite(value))


def phases(seeds):
    pooled = {leg: [] for leg in ("RH", "LF", "RF")}
    for s in seeds:
        feet = s["detail"]["feet"]
        clock = [t for t in feet[FEET["LH"]]["touchdowns_s"] if t >= FROM_S]
        for a, b in zip(clock, clock[1:]):
            for leg in pooled:
                hit = [t for t in feet[FEET[leg]]["touchdowns_s"] if a <= t < b]
                if hit:
                    pooled[leg].append((hit[0] - a) / (b - a))
    return {leg: med(v) for leg, v in pooled.items()}


def column(out: Path) -> dict:
    ev = json.loads((out / "evaluation.json").read_text())
    seeds = ev["seeds"]
    col = {"cmd": ev["judged_command_mm_s"], "n": len(seeds), "phase": phases(seeds)}
    col["hz"] = {leg: med([s["detail"]["feet"][body]["touchdown_hz"] for s in seeds]) for leg, body in FEET.items()}
    col["advance"] = {leg: med([s["detail"]["feet"][body]["median_step_advance_mm"] for s in seeds])
                      for leg, body in FEET.items()}
    col["stride_hz"] = med([s["detail"]["footfall"]["stride_hz"] for s in seeds])
    col["flight"] = med([s["metrics"].get("flight_stride_share") for s in seeds])
    col["flight_s"] = med([s["metrics"].get("flight_s_median") for s in seeds])
    col["heel"] = {leg: med([s["detail"]["heels"][body]["heel_down_share"] for s in seeds]) for leg, body in HEELS}
    col["heel_mm"] = {leg: med([s["detail"]["heels"][body]["heel_stance_height_mm"] for s in seeds])
                      for leg, body in HEELS}
    worst, names = [], collections.Counter()
    for s in seeds:
        rated = [c for c in s["detail"]["drives"]["channels"] if c.get("effort_rms_rated_ratio") is not None]
        channel = max(rated, key=lambda c: c["effort_rms_rated_ratio"])
        worst.append(channel["effort_rms_rated_ratio"])
        names[channel["joint"]] += 1
    col["rms"], col["rms_drive"] = med(worst), names.most_common(1)[0][0]
    peak = med([s["metrics"].get("effort_peak_ratio_max") for s in seeds])
    col["margin"] = None if peak is None else 1.0 - peak
    shares = collections.defaultdict(list)
    for s in seeds:
        for c in s["detail"]["drives"]["channels"]:
            if c.get("effort_clamp_share") is not None:
                shares[c["joint"]].append(c["effort_clamp_share"])
    col["at_peak"] = sorted(((j, med(v)) for j, v in shares.items() if med(v) >= AT_PEAK_SHARE), key=lambda jv: -jv[1])
    rows = ev.get("closure", {}).get("rows", [])
    col["loop"] = max((r["max"] for r in rows if r["kind"] == "connect" and r["max"] is not None), default=None)
    col["cable"] = max((r["max"] for r in rows if r["kind"] == "joint" and r["max"] is not None), default=None)
    col["cable_worst"] = max((r for r in rows if r["kind"] == "joint" and r["max"] is not None),
                             key=lambda r: r["max"], default={"name": "–"})["name"]
    col["falls"] = sum(1 for s in seeds if s["metrics"].get("falls"))
    col["nonfinite"] = sum(1 for s in seeds if not finite(s["metrics"]))
    return col


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cols = sorted((column(Path(a)) for a in argv), key=lambda c: c["cmd"])
    rows = [
        ("touchdown phase of RH / LF / RF in LH's stride (pooled median, t ≥ 4 s)",
         lambda c: " / ".join(fmt(c["phase"][k]) for k in ("RH", "LF", "RF"))),
        ("engine footfall stride Hz (seed median)", lambda c: fmt(c["stride_hz"])),
        ("touchdown Hz LF / RF; LH / RH", lambda c: f"{fmt(c['hz']['LF'], '%.1f')} / {fmt(c['hz']['RF'], '%.1f')}; "
         f"{fmt(c['hz']['LH'], '%.1f')} / {fmt(c['hz']['RH'], '%.1f')}"),
        ("step advance mm LF / RF; LH / RH", lambda c: f"{fmt(c['advance']['LF'], '%.0f')} / {fmt(c['advance']['RF'], '%.0f')}; "
         f"{fmt(c['advance']['LH'], '%.0f')} / {fmt(c['advance']['RH'], '%.0f')}"),
        ("flight share; flight s", lambda c: f"{fmt(c['flight'])}; {fmt(c['flight_s'], '%.3f')}"),
        ("heel pad share of hind stance LH / RH", lambda c: f"{fmt(c['heel']['LH'])} / {fmt(c['heel']['RH'])}"),
        ("heel pad stance height mm LH / RH", lambda c: f"{fmt(c['heel_mm']['LH'], '%.0f')} / {fmt(c['heel_mm']['RH'], '%.0f')}"),
        ("worst RMS / rated (drive); peak margin", lambda c: f"{fmt(c['rms'])} (`{c['rms_drive']}`); {fmt(c['margin'])}"),
        (f"drives at their clamp ≥ {AT_PEAK_SHARE:.2f} of frames (seed median)",
         lambda c: ", ".join(f"`{j}` {fmt(v)}" for j, v in c["at_peak"]) or "none"),
        ("hind rod loop gap max mm; cable gap max ° (which)",
         lambda c: f"{fmt(c['loop'], '%.1f')}; {fmt(c['cable'], '%.1f')} (`{c['cable_worst']}`)"),
        ("falls; non-finite seeds", lambda c: f"{c['falls']}; {c['nonfinite']}"),
    ]
    print("| command mm/s | " + " | ".join(str(int(c["cmd"])) for c in cols) + " |")
    print("|---|" + "---|" * len(cols))
    for label, cell in rows:
        print(f"| {label} | " + " | ".join(cell(c) for c in cols) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
