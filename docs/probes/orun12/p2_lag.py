"""orun12 P2: the pair lags and the fore/hind cadence a clip asks for, against what a policy does.

usage: python3 docs/probes/orun12/p2_lag.py GALLOP_TASK_JSON EVALUATION_DIR [EVALUATION_DIR ...]

**The clip.** From the bundle's ``reference`` block (the engine's own
clip, ``CadexGait.generate``): each foot's touch-down phase, stance share
(duty) and touchdowns per cycle, the fore and hind pairs' lead-trail lag
(right foot's touch-down after the left's, as a share of the cycle, and
folded to ``min(f, 1 - f)`` as ``CadexEvaluation.footfall_metrics``
folds it), the phase from the hind pair's first landing to the fore
pair's first landing, the flights (runs of samples with no foot down) and
the footfall order that ``legs.py`` would read off the clip.

**Each evaluation.** Per seed, from ``evaluation.json``: the engine's
``pair_lag`` strides for each pair, folded median, plus the share of
strides the left foot leads (unfolded lag under 0.5) and the share it
lands with its partner (folded lag under 0.05, one 20 ms frame at 2.4
Hz); the fore and hind touchdown rate over the left hind's stride clock
(``no_tap`` / ``every_stride``); the phase from LH's landing to the first
fore landing after it; the flight share and time; and the footfall orders
``legs.stride_kind`` reads (rotary, transverse, or tied: two first
landings in one frame), split by which hind landed first. A seed is
**rotary** when more than half of its strides are rotary.
Standard library only.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from legs import SETTLE_S, footfall_kind, med, stride_kind  # noqa: E402

PAW = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}


def fold(f):
    return min(f, 1.0 - f)


def clip_report(task: Path):
    ref = json.loads(task.read_text())["reference"]
    p = ref["parameters"]
    contact = ref["contact"]
    n = len(next(iter(contact.values())))
    off = p["phase_offsets"]
    print(f"## The clip ({ref['label']})\n")
    print(f"{p['stride_length_m']:.2f} m at {p['stride_frequency_hz']:.2f} Hz = {p['speed_m_s']:.2f} m/s, "
          f"duty {p['duty_factor']}, {n} samples of {ref['sample_dt_s'] * 1000:.1f} ms\n")
    print("| foot | touch-down phase | stance share | touchdowns / cycle |")
    print("|---|---|---|---|")
    for k in ("LH", "RH", "LF", "RF"):
        c = contact[k]
        downs = sum(1 for i in range(n) if c[i] and not c[i - 1])
        print(f"| {k} | {off[k]:.3f} | {sum(c) / n:.2f} | {downs} |")
    lag_f = (off["RF"] - off["LF"]) % 1.0
    lag_h = (off["RH"] - off["LH"]) % 1.0
    hind0 = min(off["LH"], off["RH"])
    fore0 = min(off["LF"], off["RF"])
    print(f"\nfore pair lag {lag_f:.3f} (folded {fold(lag_f):.3f}); hind pair lag {lag_h:.3f} "
          f"(folded {fold(lag_h):.3f}); hind-to-fore phase {(fore0 - hind0) % 1.0:.3f}")
    flights, run = [], 0
    for i in list(range(n)) * 2:
        if any(contact[k][i] for k in contact):
            if run:
                flights.append(run)
            run = 0
        else:
            run += 1
    flights = flights[len(flights) // 2:]
    order = sorted(PAW, key=lambda k: (off[k] - hind0) % 1.0)
    tied = [k for k in PAW if any(k != j and abs(off[k] - off[j]) < 1e-9 for j in PAW)]
    kind = footfall_kind([PAW[k] for k in order]) if not tied else None
    dt = ref["sample_dt_s"]
    print(f"flights per cycle: {len(flights)}, " + ", ".join(f"{f * dt:.3f} s" for f in flights))
    print(f"footfall order {' '.join(order)}"
          + (f": {kind}" if kind else f": undefined, {' and '.join(tied)} land together") + "\n")


def seed_row(s):
    d = s["detail"]
    ff = d["footfall"]
    row = {"seed": s["seed"]}
    for pair in ("F", "H"):
        strides = ff["pair_lag"][pair]["strides"]
        lags = [st["lag"] for st in strides]
        row[pair + " lag"] = med([fold(x) for x in lags])
        row[pair + " L leads"] = sum(x < 0.5 for x in lags) / len(lags) if lags else None
        row[pair + " together"] = sum(fold(x) < 0.05 for x in lags) / len(lags) if lags else None
    rate = ff["touchdown_rate_ratio"]
    row["fore rate"] = max(rate["LF"], rate["RF"])
    row["hind rate"] = min(rate["LH"], rate["RH"])
    lh = [t for t in d["feet"]["c_paw_hl"]["touchdowns_s"] if t >= SETTLE_S]
    fores = sorted(t for k in ("c_paw_fl", "c_paw_fr") for t in d["feet"][k]["touchdowns_s"])
    phases = []
    for a, b in zip(lh, lh[1:]):
        f = next((t for t in fores if a <= t < b), None)
        if f is not None:
            phases.append((f - a) / (b - a))
    row["LH to fore"] = med(phases)
    strides = d["flight"]["strides"]
    row["flight share"] = sum(st["flight_s"] > 0 for st in strides) / len(strides) if strides else None
    row["flight s"] = med([st["flight_s"] for st in strides])
    kinds = collections.Counter()
    for st in strides:
        order = st["order"]
        hinds = [p for p in order if p in ("c_paw_hl", "c_paw_hr")]
        first = "LH" if hinds and hinds[0] == "c_paw_hl" else ("RH" if hinds else "-")
        kinds[(first, stride_kind(st, d["feet"]) or "unordered")] += 1
    row["kinds"] = kinds
    ordered = sum(v for (_, k), v in kinds.items() if k in ("rotary", "transverse"))
    row["tied"] = sum(v for (_, k), v in kinds.items() if k == "tied")
    rotary = sum(v for (_, k), v in kinds.items() if k == "rotary")
    row["rotary seed"] = len(strides) > 0 and rotary > len(strides) / 2
    row["strides"] = len(strides)
    row["ordered"] = ordered
    row["rotary"] = rotary
    return row


def fmt(v, spec="%.2f"):
    return "–" if v is None else spec % v


def eval_report(path: Path):
    report = json.loads((path / "evaluation.json").read_text())
    rows = [seed_row(s) for s in report["seeds"]]
    print(f"## {path.name}\n")
    print("| seed | fore lag | fore L leads | fore together | hind lag | hind L leads | hind together "
          "| fore rate | hind rate | LH to fore | flight share | flight s | rotary / ordered / tied / strides "
          "| LH first: rot / trans | RH first: rot / trans |")
    print("|---|" + "---|" * 14)
    for r in rows:
        k = r["kinds"]
        print(f"| {r['seed']} | {fmt(r['F lag'], '%.3f')} | {fmt(r['F L leads'])} | {fmt(r['F together'])} "
              f"| {fmt(r['H lag'], '%.3f')} | {fmt(r['H L leads'])} | {fmt(r['H together'])} "
              f"| {fmt(r['fore rate'])} | {fmt(r['hind rate'])} | {fmt(r['LH to fore'], '%.3f')} "
              f"| {fmt(r['flight share'])} | {fmt(r['flight s'], '%.3f')} "
              f"| {r['rotary']} / {r['ordered']} / {r['tied']} / {r['strides']} "
              f"| {k[('LH', 'rotary')]} / {k[('LH', 'transverse')]} | {k[('RH', 'rotary')]} / {k[('RH', 'transverse')]} |")
    m = {key: med([r[key] for r in rows]) for key in
         ("F lag", "H lag", "F together", "H together", "fore rate", "hind rate", "LH to fore", "flight s")}
    print(f"\nmedians: fore lag {fmt(m['F lag'], '%.3f')} (together {fmt(m['F together'])}), hind lag "
          f"{fmt(m['H lag'], '%.3f')} (together {fmt(m['H together'])}), fore rate {fmt(m['fore rate'])}, "
          f"hind rate {fmt(m['hind rate'])}, LH to fore {fmt(m['LH to fore'], '%.3f')}, flight "
          f"{fmt(m['flight s'], '%.3f')} s; rotary seeds {sum(r['rotary seed'] for r in rows)}/{len(rows)}\n")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    clip_report(Path(argv[0]))
    for path in argv[1:]:
        eval_report(Path(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
