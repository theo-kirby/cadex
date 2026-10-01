"""Can a quadruped at rest pass W10?  (ot11 P1, the walk contract's trust check)

Two measurements, neither of which changes the contract:

1. **Where each foot's lowest frame falls.**  For every trace of one walk
   evaluation, each foot's height series is read with the same reader W10
   uses (``CadexEvaluation.foot_series`` over ``CadexDynamics.evaluation_rig``)
   and its lowest frame is placed in one of three phases: the reset drop
   (before the 1.0 s settle), stance before the shove, or after the shove.
2. **A passive standing rollout.**  The evaluated model, on CPU MuJoCo, from
   its ``solved`` keyframe with every position servo held at zero (the
   solved pose), dropped from 0 to 15 mm, for 10 s.  No policy.

    pixi run python docs/probes/ot11/runner/w10_trust.py \
        --project PROJECT --evaluation EVAL_DIR_NAME --model RUN_MODEL_XML --out OUT.json

W10 passes when every foot's lowest height over every frame is at least
``-0.05`` hip heights.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src" / "Mod" / "cadex"))
import CadexDynamics as D  # noqa: E402
import CadexEvaluation as E  # noqa: E402

FEET = ("c_foot_fl", "c_foot_fr", "c_foot_rl", "c_foot_rr")
W10_HIP_HEIGHTS = -0.05
SETTLE_S = 1.0
SHOVE_S = 0.15


def phases(evaluation: Path, rig: dict) -> list[dict]:
    rows = []
    for path in sorted(evaluation.glob("seed-*-trace.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        samples = E.read_trace(raw)["samples"]
        times = [moment for moment, _ in samples]
        policy = raw["policy"]
        shove = float(policy["disturbance"][0]["start_s"])
        row = {"seed": policy["seed"], "termination": policy["termination"] or "truncated",
               "reset_lift_mm": round(1000 * policy["reset_variation"][0]["height_m"], 2),
               "shove_s": round(shove, 2), "feet": {}}
        for name in FEET:
            height = E.foot_series(samples, name, rig["feet"][name], rig["floor_mm"])["height"]

            def window(a: float, b: float) -> list[float]:
                return [h for t, h in zip(times, height) if a <= t < b]

            low = min(range(len(height)), key=height.__getitem__)
            stance = window(SETTLE_S, shove)
            row["feet"][name] = {
                "lowest_mm": round(height[low], 2), "frame": low, "t_s": round(times[low], 2),
                "phase": ("reset drop" if times[low] < SETTLE_S
                          else "stance before shove" if times[low] < shove else "after shove"),
                "lowest_before_settle_mm": round(min(window(0.0, SETTLE_S)), 2),
                "lowest_stance_before_shove_mm": round(min(stance), 2),
                "median_stance_before_shove_mm": round(sorted(stance)[len(stance) // 2], 2),
                "lowest_after_shove_mm": round(min(window(shove, 1e9)), 2),
            }
        rows.append(row)
    return rows


def passive(model_xml: Path, lift_mm: float, seconds: float) -> dict:
    model = mujoco.MjModel.from_xml_path(str(model_xml))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    data.qpos[2] += lift_mm / 1000.0
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)
    geoms = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{name}/collision0") for name in FEET]

    def lows() -> list[float]:
        return [float(1000 * (data.geom_xpos[g][2] - model.geom_size[g][0])) for g in geoms]

    frame = round(0.02 / model.opt.timestep)  # the trace's 50 Hz frames
    series = []
    for step in range(round(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
        if (step + 1) % frame == 0:
            series.append(((step + 1) * model.opt.timestep, lows()))
    feet = {}
    for k, name in enumerate(FEET):
        moment, lowest = min(((t, h[k]) for t, h in series), key=lambda pair: pair[1])
        rest = [h[k] for t, h in series if t >= seconds / 2]
        feet[name] = {"lowest_mm": round(lowest, 2), "t_s": round(moment, 2),
                      "rest_mean_mm": round(sum(rest) / len(rest), 2)}
    return {"lift_mm": lift_mm, "seconds": seconds, "feet": feet,
            "worst_mm": min(foot["lowest_mm"] for foot in feet.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--evaluation", required=True, help="directory name under evaluations/")
    parser.add_argument("--model", type=Path, required=True, help="the evaluated MJCF")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model))
    rig = D.evaluation_rig(model, feet=FEET)
    limit = W10_HIP_HEIGHTS * rig["hip_height_mm"]
    report = {
        "schema": "cadex-ot11-w10-trust-v1",
        "mujoco_version": mujoco.__version__,
        "timestep_s": float(model.opt.timestep),
        "hip_height_mm": rig["hip_height_mm"],
        "w10_limit_mm": limit,
        "evaluation": args.evaluation,
        "phases": phases(args.project / "evaluations" / args.evaluation, rig),
        "passive": [passive(args.model, lift, 10.0) for lift in (0.0, 5.0, 10.0, 15.0)],
        "passive_lift_scan": [passive(args.model, 0.5 * i, 2.0) for i in range(11)],
    }
    for run in report["passive"] + report["passive_lift_scan"]:
        run["passes_w10"] = run["worst_mm"] >= limit
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
