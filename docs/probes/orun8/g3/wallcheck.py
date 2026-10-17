"""Does a body other than the paws pass inside a platform on a paws-only course?
Stock MuJoCo, rough-c4's actor, the platform50 pool; reports per episode the
deepest any non-foot body origin sits inside a platform box."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))
import numpy as np, mujoco
import CadexDynamics as D
bundle = Path(sys.argv[1]); actor = Path(sys.argv[2]); n = int(sys.argv[3])
task = json.loads(bundle.read_text())
xml = (bundle.parent / Path(task["model"]["path"]).name).read_bytes()
container = D.decode_policy(actor.read_bytes())
terrain = task["terrain"]
inside_eps = 0; worst = []
for k in range(n):
    model = D.load_model(xml)
    entry = terrain["pool"][k % len(terrain["pool"])]
    feats = [D._terrain_feature(f, i, "g3") for i, f in enumerate(entry["features"])]
    built = D.terrain_boxes(feats, terrain["x_range_mm"], terrain["y_range_mm"])
    course = {key: v for key, v in terrain.items() if key != "pool"}
    course.update(features=feats, boxes=built["boxes"], domes=built["domes"],
                  lowest_mm=built["lowest_mm"], highest_mm=built["highest_mm"], course={"pool": k})
    D.place_terrain_course(model, course)
    plats = [b for b in built["boxes"] if b["shape"] == "block" and max(b["top_mm"]) > 300]
    deepest = {"mm": 0.0, "body": None}
    def sample(step, data, final, action):
        for b in range(1, model.nbody):
            x, y, z = data.xpos[b] * 1000.0
            for p in plats:
                (xa, xb), (ya, yb) = p["x_range_mm"], p["y_range_mm"]
                if xa < x < xb and ya < y < yb and z < p["top_mm"][0]:
                    depth = min(x - xa, xb - x, p["top_mm"][0] - z)
                    if depth > deepest["mm"]:
                        deepest.update(mm=depth, body=mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b))
        return None
    played = {**task, "terrain": course, "episode": {**task["episode"], "max_steps": 600}}
    header, weights = container["header"], container["weights"]
    ep = D.evaluate_episode(model, played, seed=2000 + k, record_steps=False, sample=sample,
                            actions=lambda s, obs: D.policy_forward(header, weights, obs, context="g3"))
    worst.append((round(float(deepest["mm"]), 1), deepest["body"], ep.get("termination"), ep.get("step_count")))
    inside_eps += int(deepest["mm"] > 20.0)
print(json.dumps({"episodes": n, "inside_over_20mm": inside_eps, "rows": worst}))
