"""Why one hind leg lays its hock down and the other does not: each hind leg's stance against its clip.

Usage: pixi run python docs/probes/orun11/hind_asymmetry.py MODEL.xml EVALUATION_DIR [...]

Reads the seed traces a judged evaluation already wrote (it plays nothing)
and, for each hind leg, over every settled stance (the sole within the
engine's ``STANCE_MM`` of the floor, from ``SETTLE_S``), gives:

* the leg's fold at mid-stance and at the last stance frame (toe-off), for
  hip, knee and hock, beside the clip's own stance values. *Fold* is the
  joint angle signed so that the left and right legs read alike: the right
  side's axes are mirrored, so the right's angle is negated;
* the hock drive's command less its position in stance (how far it is
  behind what the policy asks), and the share of stance frames each of the
  leg's drives spends at 98 % of peak or more;
* the hock case's median stance height and the share of stance with it
  within ``STANCE_MM``, as the engine's heel metric reads it;
* stances per second and stance duration;
* at toe-off, how far ahead of the hock axis (the centre of the case's
  collision sphere) the paw's lowest point is, along the run (+x; negative
  is toes behind the hock): the lever a toe load has about the hock; and
  the vertical paw force the hock drive's peak holds at that lever.

It also prints the clip's own largest frame-to-frame step per hind joint,
in degrees and as the rate it asks for.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics  # noqa: E402
import CadexEvaluation as E  # noqa: E402

FEET = ["c_paw_fl", "c_paw_fr", "c_paw_hl", "c_paw_hr"]
HEELS = ["c_qdd_hock_l", "c_qdd_hock_r"]
LEGS = {"LH": ("c_paw_hl", "l", 1.0), "RH": ("c_paw_hr", "r", -1.0)}
JOINTS = ["hip", "knee", "hock"]
AT_PEAK = 0.98


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def stances(flags, times):
    """Settled runs of True: (first, last) frame indices, each ending in a lift."""

    runs, start = [], None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            if times[start] >= E.SETTLE_S:
                runs.append((start, i - 1))
            start = None
    return runs


def clip_rows(reference):
    names, angles = reference["joints"], reference["joint_angles_rad"]
    dt = reference["sample_dt_s"]
    out = {}
    for leg, (_, side, sign) in LEGS.items():
        stance = [k for k, c in enumerate(reference["contact"][leg]) if c]
        row = {"stance_samples": stance, "down_samples": [k for k, d in enumerate(((reference.get("heels") or {}).get(leg) or {}).get("down") or []) if d]}
        for joint in JOINTS:
            c = names.index(f"j_{joint}_{side}")
            series = [sign * math.degrees(a[c]) for a in angles]
            steps = [abs(series[(k + 1) % len(series)] - series[k]) for k in range(len(series))]
            row[joint] = {"stance": [round(series[k], 1) for k in stance], "max_step_deg": round(max(steps), 1),
                          "max_rate_deg_s": round(max(steps) / dt)}
        out[leg] = row
    return out


def read(rig, directory: Path):
    task = json.loads((directory / "judged-task.json").read_text())
    rows = []
    for path in sorted(directory.glob("seed-*-trace.json")):
        trace = E.load_trace(path)
        samples, drives = trace["samples"], trace["drives"]
        times = [t for t, _ in samples]
        channels = [c["joint"] for c in drives["channels"]]
        peaks = [c["effort_high"] for c in drives["channels"]]
        seed = {"seed": path.name.split("-")[1]}
        for leg, (foot, side, sign) in LEGS.items():
            sole = E.foot_series(samples, foot, rig["feet"][foot], rig["floor_mm"])["height"]
            heel = rig["heels"][foot]
            case = E.foot_series(samples, heel["body"], heel["geoms"], rig["floor_mm"])["height"]

            def lever(i, foot=foot, heel=heel):
                # The case's shape is centred on the hock axis; the run is along +x.
                rotation, origin = E._pose(samples[i][1], foot)
                toe = min((E._lowest(g, rotation, origin)[1] for g in rig["feet"][foot]), key=lambda p: p[2])
                rotation, origin = E._pose(samples[i][1], heel["body"])
                return toe[0] - E._lowest(heel["geoms"][0], rotation, origin)[0][0]
            runs = stances([h <= E.STANCE_MM for h in sole], times)
            frames = [i for a, b in runs for i in range(a, b + 1)]
            col = {j: channels.index(f"j_{j}_{side}") for j in JOINTS}
            fold = lambda i, j: sign * drives["positions"][i][col[j]]
            lag = [sign * (drives["commands"][i][col["hock"]] - drives["positions"][i][col["hock"]])
                   for i in frames if drives["commands"][i] is not None]
            row = {"stances": len(runs),
                   "stance_hz": len(runs) / (times[-1] - E.SETTLE_S) if times[-1] > E.SETTLE_S else None,
                   "stance_ms": med([1000 * (times[b] - times[a] + times[1] - times[0]) for a, b in runs]),
                   "case_mm": med([case[i] for i in frames]),
                   "case_down": (sum(1 for i in frames if case[i] <= E.STANCE_MM) / len(frames)) if frames else None,
                   "hock_cmd_minus_pos": med(lag),
                   "lever_toeoff_mm": med([lever(b) for a, b in runs])}
            hock_peak = peaks[col["hock"]]
            row["paw_force_at_hock_peak_n"] = hock_peak / abs(row["lever_toeoff_mm"]) if row["lever_toeoff_mm"] else None
            for j in JOINTS:
                row[f"{j}_mid"] = med([fold((a + b) // 2, j) for a, b in runs])
                row[f"{j}_toeoff"] = med([fold(b, j) for a, b in runs])
                row[f"{j}_at_peak"] = (sum(1 for i in frames if drives["efforts"][i] is not None
                                           and abs(drives["efforts"][i][col[j]]) >= AT_PEAK * peaks[col[j]])
                                       / len(frames)) if frames else None
            seed[leg] = row
        rows.append(seed)
    return task["reference"], rows


def fmt(v):
    return "-" if v is None else (f"{v:.3g}" if isinstance(v, float) else str(v))


def main(argv):
    model = CadexDynamics.load_model(Path(argv[0]).read_bytes())
    rig = CadexDynamics.evaluation_rig(model, feet=FEET, heels=HEELS)
    for directory in map(Path, argv[1:]):
        reference, rows = read(rig, directory)
        print(f"\n## {directory.name}\n")
        print("clip (fold, deg):", json.dumps(clip_rows(reference)))
        keys = [k for k in rows[0]["LH"]]
        print("\n| measure | " + " | ".join(f"LH s{r['seed'][-2:]}" for r in rows) + " | LH med | RH med |")
        for k in keys:
            lh = [r["LH"][k] for r in rows]
            rh = [r["RH"][k] for r in rows]
            print(f"| {k} | " + " | ".join(fmt(v) for v in lh) + f" | {fmt(med(lh))} | {fmt(med(rh))} |")
        print("\n| measure | " + " | ".join(f"RH s{r['seed'][-2:]}" for r in rows) + " |")
        for k in keys:
            print(f"| {k} | " + " | ".join(fmt(r["RH"][k]) for r in rows) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
