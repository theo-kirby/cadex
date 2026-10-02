"""Re-read every stored walk evaluation under W10 as ADR-467 reads it.

ADR-467 moves W10 ("on the floor, not in it") from every frame to the frames
after the 1.0 s settle, as W3, W4 and W8 already are. The contract's rule is
that changing a frozen item re-evaluates every earlier policy. A rollout is
deterministic in its seed and the evaluation stores each seed's trace, so
this re-reads those traces rather than rolling them again:

1. **Agreement.** Every stored metric must come back exactly from the
   stored trace, and the stored W10 value must equal each foot's lowest
   height over *every* frame. If either fails, the re-read is not the
   evaluation and nothing below it counts.
2. **The new reading.** ``foot_lowest_hip_heights_min`` over the settled
   frames, the spec's predicates held again, and the verdict per seed.

    pixi run python docs/probes/ot11/runner/w10_reread.py --out OUT.json \\
        PROJECT/evaluations/EVAL_DIR [...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src" / "Mod" / "cadex"))
import CadexDynamics as D  # noqa: E402
import CadexEvaluation as E  # noqa: E402

W10 = "foot_lowest_hip_heights_min"


def same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
    return a == b


def model_for(project: Path, sha256: str) -> Path:
    """The evaluated MJCF, found in the project by its digest."""

    for path in sorted(project.rglob("*.xml")):
        if hashlib.sha256(path.read_bytes()).hexdigest() == sha256:
            return path
    raise SystemExit(f"{project}: no MJCF with sha256 {sha256}")


def reread(directory: Path) -> dict:
    report = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    spec = report["spec"]
    # The report keeps the rig's scale but not its feet's geoms; those are
    # rebuilt from the evaluated model, the way the evaluation built them.
    model = model_for(directory.parent.parent, report["model_sha256"])
    rig = {**D.evaluation_rig(D.load_model(model.read_bytes()), feet=spec["feet"]),
           **report["rig"]}
    seeds = []
    for row in report["seeds"]:
        raw = json.loads((directory / f"seed-{row['seed']}-trace.json").read_text(encoding="utf-8"))
        samples = E.read_trace(raw)["samples"]
        shoves = [(float(draw["start_s"]), float(entry["duration_s"]))
                  for entry, draw in zip(spec["disturbance"], row["drawn"]["disturbance"], strict=True)
                  if not bool(entry["sustained"])]
        # The command, read the way the evaluation read it: the speed goal's
        # channel in each solver frame, averaged over the settled frames.
        command = None
        for entry in raw["policy"].get("goal") or ():
            if entry["kind"] == "speed":
                place = [c["channel"] for c in raw["goal_channels"]].index(entry["channels"][0])
                command = E.settled_command([(float(f["nominal_time_s"]), float(f["goal"][place]))
                                             for f in raw["frames"]
                                             if f.get("frame_kind") == "solver_output"])
        measured = E.measure(samples, row["episode"], rig, shoves=shoves, command_mm_s=command)
        metrics, feet = measured["metrics"], measured["detail"]["feet"]
        every_frame = min(foot["lowest_height_hip_heights"] for foot in feet.values())
        disagree = sorted(name for name in set(metrics) | set(row["metrics"])
                          if name != W10 and not same(metrics.get(name), row["metrics"].get(name)))
        if not same(every_frame, row["metrics"][W10]):
            disagree.append(W10 + " (every frame)")
        held = E.check(spec["predicates"], metrics)
        void = bool(row["void"])
        seeds.append({
            "seed": row["seed"],
            "agrees": not disagree, "disagrees_on": disagree,
            "w10_every_frame": every_frame, "w10_settled": metrics[W10],
            "lowest_mm": {name: [round(foot["lowest_height_mm"], 2),
                                 None if foot["settled_lowest_height_mm"] is None
                                 else round(foot["settled_lowest_height_mm"], 2)]
                          for name, foot in feet.items()},
            "was": {"pass": row["pass"], "failing": row["failing"]},
            "now": {"pass": not void and all(entry["pass"] for entry in held),
                    "failing": [entry["id"] for entry in held if not entry["pass"]]},
        })
    limit = next(p["min"] for p in spec["predicates"] if p["metric"] == W10)
    return {
        "evaluation": f"{directory.parent.parent.name}/evaluations/{directory.name}",
        "policy_sha256": report["policy_sha256"], "w10_min": limit,
        "agrees": all(seed["agrees"] for seed in seeds),
        "verdict_was": report["verdict"],
        "verdict_now": "pass" if all(seed["now"]["pass"] for seed in seeds) else "fail",
        "w10_fails_was": sum(seed["w10_every_frame"] < limit for seed in seeds),
        "w10_fails_now": sum(seed["w10_settled"] is None or seed["w10_settled"] < limit for seed in seeds),
        "seed_verdicts_moved": [seed["seed"] for seed in seeds if seed["was"]["pass"] != seed["now"]["pass"]],
        "seeds": seeds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evaluations", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [reread(directory) for directory in args.evaluations]
    args.out.write_text(json.dumps({"schema": "cadex-ot11-w10-reread-v1", "adr": "ADR-467",
                                    "settle_s": E.SETTLE_S, "evaluations": rows}, indent=2) + "\n",
                        encoding="utf-8")
    for row in rows:
        print(row["evaluation"], "agrees" if row["agrees"] else "DISAGREES",
              row["verdict_was"], "->", row["verdict_now"],
              f"W10 fails {row['w10_fails_was']} -> {row['w10_fails_now']}",
              "moved:", row["seed_verdicts_moved"])
    return 0 if all(row["agrees"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
