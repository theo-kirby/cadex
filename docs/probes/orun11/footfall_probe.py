"""Re-read judged rollout traces for ADR-774's heel and footfall metrics.

Usage: pixi run python docs/probes/orun11/footfall_probe.py MODEL.xml EVALUATION_DIR [...]
       [--heel-shapes-from OTHER_MODEL.xml]

Builds the evaluation rig from the run's exported model with the cat's feet
and the hock cases as heels, then measures every seed trace in each
evaluation directory against the judged task's reference, as the engine's
evaluation would, and prints one row per seed and the medians. It reads the
traces an evaluation already wrote; it plays nothing.

A model whose hock case has no collision shape (t2-g4's) is refused by the
engine; ``--heel-shapes-from`` borrows the heel shapes of another model of
the same bodies (t2-g5's 40 mm sphere on the case), so the case's height is
still read. The case could not touch the floor in such a run.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics  # noqa: E402
import CadexEvaluation  # noqa: E402

FEET = ["c_paw_fl", "c_paw_fr", "c_paw_hl", "c_paw_hr"]
HEELS = ["c_qdd_hock_l", "c_qdd_hock_r"]
KEYS = ["heel_down_stance_share_min", "heel_down_at_toeoff_share_min", "heel_stance_height_mm_max",
        "heel_foot_flat_share_min", "touchdown_rate_ratio_max", "touchdown_rate_ratio_min",
        "hind_overreach_mm_min", "pair_lag_fore_median", "pair_lag_hind_median",
        "max_forward_speed_2s_mm_s", "effort_peak_ratio_max", "effort_rms_rated_ratio_max"]


def judge(rig, directory: Path) -> list[dict]:
    task = json.loads((directory / "judged-task.json").read_text())
    rows = []
    for path in sorted(directory.glob("seed-*-trace.json")):
        trace = CadexEvaluation.load_trace(path)
        read = CadexEvaluation.measure(trace["samples"], trace["episode"], rig,
                                       drives=trace["drives"], reference=task["reference"])
        m, d = read["metrics"], read["detail"]
        heels = d.get("heels") or {}
        rows.append({
            "seed": path.name.split("-")[1], **{k: m.get(k) for k in KEYS},
            "per_hind": {f: {k: heels[f][k] for k in ("heel_down_share", "heel_down_at_toeoff_share",
                                                       "heel_stance_height_mm", "flat_share",
                                                       "sole_pitch_deg_median")} for f in heels},
            "touchdown_hz": d["footfall"]["touchdown_hz"], "stride_hz": d["footfall"]["stride_hz"],
            "overreach_mm": {k: v["median"] for k, v in d["footfall"]["overreach_mm"].items()},
        })
    return rows


def fmt(v) -> str:
    return "-" if v is None else (f"{v:.3g}" if isinstance(v, float) else str(v))


def main(argv: list[str]) -> None:
    borrow = None
    if "--heel-shapes-from" in argv:
        at = argv.index("--heel-shapes-from")
        borrow, argv = argv[at + 1], argv[:at] + argv[at + 2:]
    model = CadexDynamics.load_model(Path(argv[0]).read_bytes())
    if borrow is None:
        rig = CadexDynamics.evaluation_rig(model, feet=FEET, heels=HEELS)
    else:
        rig = CadexDynamics.evaluation_rig(model, feet=FEET)
        donor = CadexDynamics.load_model(Path(borrow).read_bytes())
        rig["heels"] = CadexDynamics.evaluation_rig(donor, feet=FEET, heels=HEELS)["heels"]
        print(f"heel shapes borrowed from {borrow}")
    for directory in map(Path, argv[1:]):
        rows = judge(rig, directory)
        print(f"\n## {directory.name}\n")
        print(json.dumps(rows, indent=1, default=float))
        print("\nmedian over seeds:")
        for k in KEYS:
            values = [r[k] for r in rows if isinstance(r[k], (int, float))]
            print(f"  {k}: {fmt(statistics.median(values)) if values else '-'} ({len(values)}/{len(rows)})")


if __name__ == "__main__":
    main(sys.argv[1:])
