"""How deep the feet sink on a model the product exported, under a stepping load.  (ot11 R1, W10)

``contact_depth.py`` measured ADR-469 by patching the spring into a model the
old engine exported. This reads the model the *current* engine exported and
accepted, unpatched, and drives it with trained policies whose network reads
what that model's task emits. Per seed and foot it reports the deepest point
of the foot sphere below the floor after the 1.0 s settle (the same reading
as ``contact_depth.py`` and W10), and it refuses a model with a contact
margin or gap (``CadexDynamics.contact_offsets``), whose feet would be held
off the floor rather than measured on it.

    pixi run python docs/probes/ot11/runner/rebuilt_depth.py \\
        --model MODEL.xml --task TASK.json --policy NAME=POLICY.cxpolicy [...] \\
        --seeds 1101-1110 --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import mujoco

from contact_depth import D, FEET, SETTLE_S  # noqa: E402  (puts the engine source on the path)

#: A foot higher than this is off the floor: the contract's stance height.
STANCE_MM = 1.0


def depth(model, task: dict, container: dict, seed: int) -> dict:
    """``contact_depth.depth``, plus each foot's share of frames off the floor
    and how many times it left it, so the load is shown to be a stepping one."""

    geoms = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{name}/collision0") for name in FEET]
    interval = float(task["episode"]["control_interval_s"])
    lows: list[list[float]] = []

    def sample(step, data, final, action):
        if step * interval >= SETTLE_S:
            lows.append([1000.0 * (data.geom_xpos[g][2] - model.geom_size[g][0]) for g in geoms])

    episode = D.evaluate_episode(
        model, task, seed=seed, sample=sample,
        actions=lambda _step, obs: D.policy_forward(container["header"], container["weights"], obs))
    row = {"seed": seed, "steps": int(episode["step_count"]),
           "termination": episode.get("termination") or "horizon"}
    if not lows:
        return {**row, "deepest_mm": None, "worst_mm": None}
    heights = np.array(lows)
    up = heights > STANCE_MM
    lifts = (up[1:] & ~up[:-1]).sum(axis=0)
    return {**row,
            "deepest_mm": {name: round(float(heights[:, k].min()), 2) for k, name in enumerate(FEET)},
            "worst_mm": round(float(heights.min()), 2),
            "lifted_share": {name: round(float(up[:, k].mean()), 3) for k, name in enumerate(FEET)},
            "lift_offs": {name: int(lifts[k]) for k, name in enumerate(FEET)},
            "highest_mm": {name: round(float(heights[:, k].max()), 2) for k, name in enumerate(FEET)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--policy", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--seeds", default="1101-1110")
    parser.add_argument("--hip-mm", type=float, default=None,
                        help="hip height, to report the worst depth in hip heights as W10 does")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    first, last = (int(part) for part in args.seeds.split("-"))
    xml = args.model.read_bytes()
    task = json.loads(args.task.read_text(encoding="utf-8"))
    model = D.load_model(xml)
    offsets = D.contact_offsets(model)
    if offsets:
        raise SystemExit(f"this model holds contact surfaces off their geometry: {offsets}")
    report = {
        "schema": "cadex-ot11-rebuilt-depth-v1",
        "model_sha256": hashlib.sha256(xml).hexdigest(),
        "task_sha256": hashlib.sha256(args.task.read_bytes()).hexdigest(),
        "timestep_s": float(model.opt.timestep),
        "solref": sorted({tuple(round(float(v), 6) for v in row) for row in model.geom_solref}),
        "contact_offsets": offsets,
        "policies": {},
    }
    for item in args.policy:
        name, path = item.split("=", 1)
        blob = Path(path).read_bytes()
        container = D.decode_policy(blob)
        rows = [depth(model, task, container, seed) for seed in range(first, last + 1)]
        read = [row["worst_mm"] for row in rows if row["worst_mm"] is not None]
        entry = {"lift_offs_min": min(min(r["lift_offs"].values()) for r in rows if r.get("lift_offs")),
                 "policy_sha256": hashlib.sha256(blob).hexdigest(), "seeds": rows,
                 "seeds_read": len(read), "worst_mm": min(read), "best_mm": max(read)}
        if args.hip_mm:
            entry["worst_hip_heights"] = round(min(read) / args.hip_mm, 4)
            entry["best_hip_heights"] = round(max(read) / args.hip_mm, 4)
        report["policies"][name] = entry
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in v if x not in ("seeds", "policy_sha256")}
                      for k, v in report["policies"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
