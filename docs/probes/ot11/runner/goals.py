"""The goals an evaluation will hold, drawn before anything is trained.  (ot11)

The contract fixes each seed's goals as points computed from the accepted
model before its first training run.  This draws them the way the engine's
evaluation does -- the spec's conditions (``evaluation_task``), one
``random.Random(seed)`` stream, the randomisation and variation draws first,
then ``draw_episode_goals`` -- from an exported task bundle and its model,
and prints one row per seed.  It trains nothing and plays no episode.

    pixi run python docs/probes/ot11/runner/goals.py TASK.json MODEL.xml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src/Mod/cadex"))


def draw(task: dict, xml: bytes) -> dict:
    import mujoco
    import CadexDynamics as dynamics

    model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    played = dynamics.evaluation_task(task)
    seeds = []
    for seed in task["success"]["seeds"]:
        rng = random.Random(int(seed))
        dynamics.apply_randomisation(mujoco, model, mujoco.MjData(model), played, rng=rng)
        dynamics.draw_episode_variation(played, rng)
        goals = dynamics.draw_episode_goals(mujoco, model, played, rng)
        seeds.append({"seed": int(seed), "goals": [
            {"label": goal["label"],
             "segments": [[round(value, 4) for value in segment] for segment in goal["segments"]]}
            for goal in goals]})
    return {
        "schema": "ot11-drawn-goals-v1",
        "model_sha256": hashlib.sha256(xml).hexdigest(),
        "scale": task["success"].get("scale"),
        "goal": [{key: entry[key] for key in ("label", "kind", "segments", "resample_steps")}
                 for entry in played.get("goal") or ()],
        "seeds": seeds,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task", type=Path)
    parser.add_argument("model", type=Path)
    args = parser.parse_args(argv)
    task = json.loads(args.task.read_text(encoding="utf-8"))
    print(json.dumps(draw(task, args.model.read_bytes()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
