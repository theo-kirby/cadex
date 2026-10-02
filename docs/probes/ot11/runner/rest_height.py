"""How high each foot rests above the floor, read from a stored walk evaluation's traces.

Round 11's publication left one check owed before a W10 pass on r13 can be
read as a fix: r13 adds a contact margin to each foot sphere, which makes
MuJoCo push on the foot before its geometry reaches the floor. W10 reads the
geometry's lowest point, and so does the stance test (``STANCE_MM``), so a
margin can lift a resting foot out of the floor *and* out of what the
evaluation counts as stance. This reads, per foot over the settled frames:

- ``p05_mm`` / ``median_mm`` -- the 5th percentile and median of its height
  (the 5th percentile is where it rests when it is down);
- ``stance_share`` -- frames at or under ``STANCE_MM``, which is what the
  duty factor counts;
- ``band_share`` -- frames above ``STANCE_MM`` and at or under
  ``STANCE_MM + band`` (default 3 mm): touching under a margin, but not stance.

It recomputes the heights the evaluation's own way (``foot_series`` on the
stored trace, the feet rebuilt from the evaluated model) and refuses to
report unless each foot's settled lowest height equals the stored one.

    pixi run python docs/probes/ot11/runner/rest_height.py --out OUT.json \\
        PROJECT/evaluations/EVAL_DIR [...]
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w10_reread import D, E, model_for  # noqa: E402


def rest(directory: Path, band_mm: float) -> dict:
    report = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    model = model_for(directory.parent.parent, report["model_sha256"])
    rig = {**D.evaluation_rig(D.load_model(model.read_bytes()), feet=report["spec"]["feet"]),
           **report["rig"]}
    feet: dict[str, dict[str, list[float]]] = {}
    for row in report["seeds"]:
        raw = json.loads((directory / f"seed-{row['seed']}-trace.json").read_text(encoding="utf-8"))
        samples = E.read_trace(raw)["samples"]
        for name, geoms in rig["feet"].items():
            height = E.foot_series(samples, name, geoms, rig["floor_mm"])["height"]
            settled = [h for (moment, _), h in zip(samples, height) if moment >= E.SETTLE_S]
            stored = row["detail"]["feet"][name]["settled_lowest_height_mm"]
            if not math.isclose(min(settled), stored, rel_tol=0.0, abs_tol=1e-9):
                raise SystemExit(f"{directory.name} seed {row['seed']} {name}: "
                                 f"{min(settled)} != stored {stored}")
            per = feet.setdefault(name, {"p05_mm": [], "median_mm": [],
                                         "stance_share": [], "band_share": []})
            ordered = sorted(settled)
            per["p05_mm"].append(ordered[int(0.05 * (len(ordered) - 1))])
            per["median_mm"].append(statistics.median(settled))
            per["stance_share"].append(sum(h <= E.STANCE_MM for h in settled) / len(settled))
            per["band_share"].append(sum(E.STANCE_MM < h <= E.STANCE_MM + band_mm
                                         for h in settled) / len(settled))
    return {
        "evaluation": f"{directory.parent.parent.name}/evaluations/{directory.name}",
        "policy_sha256": report["policy_sha256"], "model_sha256": report["model_sha256"],
        "seeds": [row["seed"] for row in report["seeds"]],
        "feet": {name: {key: [round(min(v), 3), round(max(v), 3)] for key, v in per.items()}
                 for name, per in feet.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--band-mm", type=float, default=3.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [rest(directory, args.band_mm) for directory in args.evaluations]
    args.out.write_text(json.dumps({"schema": "cadex-ot11-rest-height-v1", "settle_s": E.SETTLE_S,
                                    "stance_mm": E.STANCE_MM, "band_mm": args.band_mm,
                                    "ranges_are": "[min, max] over the evaluation's seeds",
                                    "evaluations": rows}, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(row["evaluation"])
        for name, per in row["feet"].items():
            print(f"  {name}: " + "  ".join(f"{k} {v[0]}..{v[1]}" for k, v in per.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
