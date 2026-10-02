"""How deep a policy's feet sink into the floor, on the old contact spring and on the new one (ADR-469).

Owner, 2026-10-01: stepping feet that sink 7-15 mm into the floor are a defect
in the exported contact physics. This is the before/after measurement under a
stepping load: one trained walk policy, driven by the engine's own episode
loop (``CadexDynamics.evaluate_episode`` + ``policy_forward``, CPU MuJoCo),
on the MJCF its run trained on, twice per seed:

- **before**: the MJCF as the run exported it. Its feet and floor carry no
  ``solref``, which is MuJoCo's default (0.02 s, 1), what ``export_mjcf``
  wrote until ADR-469;
- **after**: the same file with one ``<default><geom solref=.../></default>``
  at ``CadexDynamics.CONTACT_TIMECONST_S``, refused unless every geom reads
  that spring afterwards. Nothing else differs.

Per seed and foot it reports the deepest point of the 7.5 mm foot sphere
below the floor after the 1.0 s settle, at every control step. The policy
was trained on the soft spring, so the gait differs between the two runs;
what is measured is the contact, under a load the policy chose.

    pixi run python docs/probes/ot11/runner/contact_depth.py \\
        --run PROJECT/runs/RUN --seeds 1101-1110 --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src" / "Mod" / "cadex"))
import CadexDynamics as D  # noqa: E402

FEET = ("c_foot_fl", "c_foot_fr", "c_foot_rl", "c_foot_rr")
SETTLE_S = 1.0
OLD_SOLREF = (0.02, 1.0)


def depth(model, task: dict, container: dict, seed: int) -> dict:
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
    if not lows:  # ended inside the settle: nothing to read
        return {**row, "deepest_mm": None, "worst_mm": None}
    heights = np.array(lows)
    return {**row,
            "deepest_mm": {name: round(float(heights[:, k].min()), 2) for k, name in enumerate(FEET)},
            "worst_mm": round(float(heights.min()), 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--seeds", default="1101-1110")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    first, last = (int(part) for part in args.seeds.split("-"))
    train = args.run / "train"
    xml = (train / "model-model.xml").read_text(encoding="utf-8")
    task = json.loads((train / "walk_task-task.json").read_text(encoding="utf-8"))
    policy = (train / "walk_task.cxpolicy").read_bytes()
    container = D.decode_policy(policy)

    after_xml = xml.replace(
        "<option ", f'<default><geom solref="{D.CONTACT_TIMECONST_S} 1"/></default><option ', 1)
    models = {"before": D.load_model(xml.encode()), "after": D.load_model(after_xml.encode())}
    if "margin=" in xml or "gap=" in xml:
        raise SystemExit("this model holds geometry off the floor (margin or gap); measure a model without one")
    for label, want in (("before", OLD_SOLREF), ("after", (D.CONTACT_TIMECONST_S, 1.0))):
        if not np.allclose(models[label].geom_solref, want):
            raise SystemExit(f"{label}: not every geom reads solref {want}")
    report = {
        "schema": "cadex-ot11-contact-depth-v1",
        "mujoco_version": mujoco.__version__,
        "run": args.run.name,
        "model_sha256": hashlib.sha256(xml.encode()).hexdigest(),
        "policy_sha256": hashlib.sha256(policy).hexdigest(),
        "timestep_s": float(models["before"].opt.timestep),
        "solref": {"before": list(OLD_SOLREF), "after": [D.CONTACT_TIMECONST_S, 1.0]},
        "settle_s": SETTLE_S,
    }
    for label, model in models.items():
        rows = [depth(model, task, container, seed) for seed in range(first, last + 1)]
        read = [row["worst_mm"] for row in rows if row["worst_mm"] is not None]
        report[label] = {"seeds": rows, "seeds_read": len(read),
                         "worst_mm": min(read), "best_mm": max(read)}
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {"worst": report[k]["worst_mm"], "best": report[k]["best_mm"]}
                      for k in models}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
