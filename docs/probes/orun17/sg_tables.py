"""orun17 SG/RL/O9: the speed-commanded policy's tables, one column per judged command, with each clause's verdict.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/sg_tables.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

MODEL_XML is the run's ``train/cat_model-model.xml``; each EVALUATION_DIR is
one ``orun16/sg_judge.py`` evaluation of the same policy at one held command
(``judged_command_mm_s``), with its ``seed-*-trace.json``. Columns are
sorted by command, slowest first. It gathers what orun17 iteration 1 read
with five probes (``orun12/legs.py``, ``orun14/paw_floor.py``,
``orun13/p2_lag.py``, ``orun13/spine_foot.py``, ``orun16/pin_rate.py``) into
the charter's report format, reusing their readings rather than restating
them. Every reading is over frames from the engine's settle (1 s) on, and
every per-seed number is a median over the 10 seeds unless it says
otherwise. Left and right are apart (O5).

**SG (O2a).** Per command and hind leg: the engine's ``heel_down_share``
(``hock_down``'s reading), U (``paw_floor``: the share of on-ground frames
toes-up of the floor past its ``FLAT_DEG``, 10 deg, and past O2's 5 deg), the floor pitch at
lift and the share of lifts toes-up of the floor. Verdicts: the slowest command's heel share
at most 0.1 on each leg; the fastest's at least 0.4 with U past 5 deg (O2) under 0.2 on
each leg; the heel share strictly rising with the command, per leg.

**RL (O3a).** Per command: rotary seeds (``p2_lag``'s rule, over ordered
strides, and over all strides as iteration 1 reported it); each pair's lag
as a share of the stride (the engine's ``pair_lag`` strides, folded to
``min(f, 1 - f)``); and each pair's lag **in ms, measured** rather than
estimated: a ``pair_lag`` stride's folded share times its own period (the
next stride's ``start_s`` less its own; the last stride, and any period over
twice the seed's median, a missed landing, are dropped). Per seed the
median; the table gives the median over seeds and the lowest seed, and
the seed-median share of strides under 40 ms (single strides that tie or
nearly tie, which a seed median hides). Verdicts:
rotary on at least 8 of 10 seeds (ordered strides) at each command; each
pair's seed-median lag at least 40 ms on every seed at each command; each
pair's lag share strictly falling with the command.

**O9 and the judged-run line.** Per command: the top 2 s speed (median, and
min / max over seeds); the hind pin rate p95 per leg (``paw_floor``'s
seed-median p95, and the largest seed p95) and its flapping swings; the
cable's largest gap and the largest loop gap (``judge.py``'s ``closure``);
the spine's range per left-hind stride and share at a stop
(``spine_foot``); flight share; the worst drive's RMS over rated (the median
of each seed's worst, and the drive worst most often) and its peak margin,
with the drives at their clamp (peak) on 5% or more of frames, by share;
falls and any non-finite metric (a blow-up). Verdicts: pins p95 under 900
deg/s with no flapping, cable within 1 deg, loops within 2 mm, no
non-finite metric, at each command.

Writes nothing; prints markdown.
"""

from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
for sub in ("orun12", "orun13", "orun14"):
    sys.path.insert(0, str(HERE.parents[1] / sub))
import p2_lag  # noqa: E402
import paw_floor as PF  # noqa: E402
import spine_foot  # noqa: E402
from legs import med  # noqa: E402

HIND = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))
SLOW_HEEL = 0.1
FAST_HEEL = 0.4
U_MAX = 0.2
U5_DEG = 5.0
LAG_MS = 40.0
ROTARY_SEEDS = 8
PIN_P95 = 900.0
CABLE_DEG = 1.0
LOOP_MM = 2.0
AT_PEAK_SHARE = 0.05  # a drive at its clamp on 5% of frames or more is named


def fmt(v, spec="%.2f"):
    return "–" if v is None else spec % v


def lag_ms(strides):
    """Seed-median folded pair lag in ms, each stride's share times its own period."""

    starts = [s["start_s"] for s in strides]
    periods = [b - a for a, b in zip(starts, starts[1:])]
    if not periods:
        return None, None
    typical = statistics.median(periods)
    values = [p2_lag.fold(s["lag"]) * p * 1000.0 for s, p in zip(strides, periods) if p <= 2.0 * typical]
    return med(values), (sum(v < LAG_MS for v in values) / len(values) if values else None)


def u_at(series, deg):
    """U with the toes-up bar at ``deg`` instead of ``paw_floor``'s ``FLAT_DEG``."""

    down = lambda h: h <= PF.E.STANCE_MM  # noqa: E731
    ground = [i for i, t in enumerate(series["t"]) if t >= PF.E.SETTLE_S - 1e-9
              and (down(series["sole"][i]) or down(series["heel"][i]))]
    up = sum(1 for i in ground if (down(series["sole"][i]) and series["pitch"][i] > deg)
             or (not down(series["sole"][i])))
    return up / len(ground) if ground else None


def finite(value):
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite(v) for v in value)
    return not (isinstance(value, float) and not math.isfinite(value))


def column(model, geoms, out: Path):
    ev = json.loads((out / "evaluation.json").read_text())
    seeds = ev["seeds"]
    col = {"name": out.name, "cmd": ev.get("judged_command_mm_s"), "n": len(seeds)}
    speed = sorted(s["metrics"]["max_forward_speed_2s_mm_s"] / 1000.0 for s in seeds
                   if s["metrics"].get("max_forward_speed_2s_mm_s") is not None)
    col["speed"] = (speed[0], statistics.median(speed), speed[-1]) if speed else None
    col["pass"] = len(ev["summary"]["passed"])
    # The paws on their pins (paw_floor) and the engine's heel share.
    engine = {s["seed"]: s["detail"] for s in seeds}
    legs = {leg: [] for leg, _ in HIND}
    for path in sorted(out.glob("seed-*-trace.json")):
        seed = int(path.name.split("-")[1])
        series = PF.seed_series(geoms, ev["rig"], json.loads(path.read_text()))
        for leg, paw in HIND:
            row = PF.leg_stats(series[leg], engine[seed]["heels"][paw]["heel_down_share"])
            row["U5"] = u_at(series[leg], U5_DEG)
            legs[leg].append(row)
    for leg, _ in HIND:
        rs = legs[leg]
        col[leg] = {k: med([r[k] for r in rs]) for k in ("engine", "U", "U5", "lift_pitch", "lift_up", "p95", "flaps")}
        col[leg]["p95_worst"] = max((r["p95"] for r in rs if r["p95"] is not None), default=None)
    # Footfall: rotary seeds and pair lags.
    rows = [p2_lag.seed_row(s) for s in seeds]
    col["rotary"] = sum(r["rotary seed"] is True for r in rows)
    col["rotary_all"] = sum(r["rotary seed (all)"] for r in rows)
    col["undecided"] = sum(r["rotary seed"] is None for r in rows)
    for pair in ("F", "H"):
        both = [lag_ms(s["detail"]["footfall"]["pair_lag"][pair]["strides"]) for s in seeds]
        ms = [m for m, _ in both]
        col[pair] = {"share": med([r[pair + " lag"] for r in rows]), "ms": med(ms),
                     "under": med([u for _, u in both]),
                     "ms_min": min((v for v in ms if v is not None), default=None),
                     "together": med([r[pair + " together"] for r in rows])}
    col["flight"] = med([s["metrics"].get("flight_stride_share") for s in seeds])
    col["flight_s"] = med([s["metrics"].get("flight_s_median") for s in seeds])
    # Spine.
    spine_rows, _ = spine_foot.seed_rows(model, out)
    col["spine"] = med([r["range_sum"] for r in spine_rows])
    col["stop"] = med([r["stop"] for r in spine_rows])
    closure = ev.get("closure", {}).get("rows", [])
    col["cable"] = next((r["max"] for r in closure if r["name"] == "coupling/cable_spine"), None)
    gaps = [r["max"] for r in closure if r["kind"] == "connect" and r["max"] is not None]
    col["loop"] = max(gaps) if gaps else None
    # Drives.
    worst, names = [], collections.Counter()
    for s in seeds:
        rated = [c for c in s["detail"]["drives"]["channels"] if c.get("effort_rms_rated_ratio") is not None]
        if rated:
            channel = max(rated, key=lambda c: c["effort_rms_rated_ratio"])
            worst.append(channel["effort_rms_rated_ratio"])
            names[channel["joint"]] += 1
    col["rms"] = med(worst)
    col["rms_drive"] = names.most_common(1)[0][0] if names else "–"
    peak = med([s["metrics"].get("effort_peak_ratio_max") for s in seeds])
    col["margin"] = None if peak is None else 1.0 - peak
    # The engine's effort is the actuator's force after MuJoCo's forcerange,
    # so a peak ratio of 1.0 is a drive held at its clamp (the drive's peak),
    # never past it: a margin of 0 says which drives saturate, not a fault in
    # the column. Name them, by the seed-median share of frames at the clamp.
    shares = collections.defaultdict(list)
    for s in seeds:
        for c in s["detail"]["drives"]["channels"]:
            if c.get("effort_clamp_share") is not None:
                shares[c["joint"]].append(c["effort_clamp_share"])
    col["at_peak"] = sorted(((j, med(v)) for j, v in shares.items() if med(v) >= AT_PEAK_SHARE),
                            key=lambda jv: -jv[1])
    col["falls"] = sum(1 for s in seeds if s["metrics"].get("falls"))
    col["nonfinite"] = sum(1 for s in seeds if not finite(s["metrics"]))
    return col


def strictly(values, rising):
    if any(v is None for v in values) or len(values) < 2:
        return False
    return all((b > a) if rising else (b < a) for a, b in zip(values, values[1:]))


def verdict(ok):
    return "**pass**" if ok else "fail"


def table(cols, rows):
    print("| command mm/s | " + " | ".join(str(c["cmd"]) for c in cols) + " |")
    print("|---|" + "---|" * len(cols))
    for label, cell in rows:
        print(f"| {label} | " + " | ".join(cell(c) for c in cols) + " |")
    print()


def lr(key, spec="%.2f"):
    return lambda c: f"{fmt(c['LH'][key], spec)} / {fmt(c['RH'][key], spec)}"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = PF.paw_capsules(model)
    cols = sorted((column(model, geoms, Path(a)) for a in argv[1:]), key=lambda c: c["cmd"] or 0)
    print(f"# {', '.join(c['name'] for c in cols)}\n")

    print("## SG: posture follows speed\n")
    table(cols, [
        ("top 2 s m/s median (min / max)", lambda c: "–" if not c["speed"] else
         f"**{c['speed'][1]:.2f}** ({c['speed'][0]:.2f} / {c['speed'][2]:.2f})"),
        ("heel share of stance LH / RH (engine `hock_down`)", lr("engine")),
        ("U LH / RH (toes-up of floor past 10°, `paw_floor`)", lr("U")),
        ("U LH / RH past 5° (O2, the verdict's)", lr("U5")),
        ("floor pitch at lift LH / RH °", lr("lift_pitch", "%+.1f")),
        ("lifts toes-up of floor LH / RH", lr("lift_up")),
    ])
    slow, fast = cols[0], cols[-1]
    sg = {
        f"slowest ({slow['cmd']}) heel ≤ {SLOW_HEEL} each leg": all(
            slow[leg]["engine"] is not None and slow[leg]["engine"] <= SLOW_HEEL for leg, _ in HIND),
        f"fastest ({fast['cmd']}) heel ≥ {FAST_HEEL} each leg": all(
            fast[leg]["engine"] is not None and fast[leg]["engine"] >= FAST_HEEL for leg, _ in HIND),
        f"fastest U (past {U5_DEG:g}°, O2) < {U_MAX} each leg": all(
            fast[leg]["U5"] is not None and fast[leg]["U5"] < U_MAX for leg, _ in HIND),
        "heel share rises with the command, LH": strictly([c["LH"]["engine"] for c in cols], True),
        "heel share rises with the command, RH": strictly([c["RH"]["engine"] for c in cols], True),
    }
    for k, ok in sg.items():
        print(f"- {k}: {verdict(ok)}")
    print(f"\nSG: {verdict(all(sg.values()) and len(cols) >= 3)} ({len(cols)} commands)\n")

    print("## RL: rotary at every speed\n")
    table(cols, [
        ("rotary seeds, ordered strides (all strides)", lambda c: f"{c['rotary']}/{c['n']} ({c['rotary_all']}/{c['n']})"
         + (f", {c['undecided']} undecided" if c["undecided"] else "")),
        ("fore lag, share of stride", lambda c: fmt(c["F"]["share"], "%.3f")),
        ("hind lag, share of stride", lambda c: fmt(c["H"]["share"], "%.3f")),
        ("fore lag ms, median (lowest seed)", lambda c: f"{fmt(c['F']['ms'], '%.0f')} ({fmt(c['F']['ms_min'], '%.0f')})"),
        ("hind lag ms, median (lowest seed)", lambda c: f"{fmt(c['H']['ms'], '%.0f')} ({fmt(c['H']['ms_min'], '%.0f')})"),
        ("strides under 40 ms fore / hind (seed median)", lambda c: f"{fmt(c['F']['under'])} / {fmt(c['H']['under'])}"),
        ("strides landing together fore / hind", lambda c: f"{fmt(c['F']['together'])} / {fmt(c['H']['together'])}"),
    ])
    rl = {
        f"rotary ≥ {ROTARY_SEEDS}/10 at every command": all(c["rotary"] >= ROTARY_SEEDS for c in cols),
        f"each pair ≥ {LAG_MS:.0f} ms on every seed at every command": all(
            c[p]["ms_min"] is not None and c[p]["ms_min"] >= LAG_MS for c in cols for p in ("F", "H")),
        "fore lag share falls with the command": strictly([c["F"]["share"] for c in cols], False),
        "hind lag share falls with the command": strictly([c["H"]["share"] for c in cols], False),
    }
    for k, ok in rl.items():
        print(f"- {k}: {verdict(ok)}")
    print(f"\nRL: {verdict(all(rl.values()) and len(cols) >= 3)}\n")

    print("## O9 and the judged-run line\n")
    table(cols, [
        ("gallop_spec pass", lambda c: f"{c['pass']}/{c['n']}"),
        ("pin p95 °/s LH / RH (worst seed)", lambda c: f"{fmt(c['LH']['p95'], '%.0f')} / {fmt(c['RH']['p95'], '%.0f')} "
         f"({fmt(c['LH']['p95_worst'], '%.0f')} / {fmt(c['RH']['p95_worst'], '%.0f')})"),
        ("flapping swings LH / RH", lr("flaps")),
        ("cable gap max °", lambda c: fmt(c["cable"])),
        ("loop gap max mm", lambda c: fmt(c["loop"], "%.1f")),
        ("spine range per stride (sum) °; at a stop", lambda c: f"{fmt(c['spine'], '%.1f')}; {fmt(c['stop'])}"),
        ("flight share; flight s", lambda c: f"{fmt(c['flight'])}; {fmt(c['flight_s'], '%.3f')}"),
        ("worst RMS / rated (drive); peak margin", lambda c: f"{fmt(c['rms'])} (`{c['rms_drive']}`); {fmt(c['margin'])}"),
        (f"at peak: drives ≥ {AT_PEAK_SHARE:.2f} of frames at the clamp (seed median)",
         lambda c: ", ".join(f"`{j}` {fmt(v)}" for j, v in c["at_peak"]) or "none"),
        ("falls; non-finite seeds", lambda c: f"{c['falls']}; {c['nonfinite']}"),
    ])
    o9 = {
        f"pins p95 < {PIN_P95:.0f} °/s, no flapping": all(
            c[leg]["p95"] is not None and c[leg]["p95"] < PIN_P95 and not c[leg]["flaps"] for c in cols for leg, _ in HIND),
        f"cable within {CABLE_DEG:.0f}°": all(c["cable"] is not None and c["cable"] <= CABLE_DEG for c in cols),
        f"loops within {LOOP_MM:.0f} mm": all(c["loop"] is not None and c["loop"] <= LOOP_MM for c in cols),
        "no blow-up": all(c["nonfinite"] == 0 for c in cols),
    }
    for k, ok in o9.items():
        print(f"- {k}: {verdict(ok)}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
