"""Compose a box course onto an exported cat bundle with the engine's own
builder (terrain_grid + _environment_box_course), so a probe needs no
24-minute re-export. Writes <out>/outputs/{run-task.json, <model>.xml}."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(ROOT / "training"))
import mujoco
import CadexDynamics as D
import cadex_train as T

def compose(bundle: str, terrain: dict, out: str) -> dict:
    path = Path(bundle)
    task = json.loads(path.read_text())
    xml = (path.parent / Path(task["model"]["path"]).name).read_bytes()
    robot = T.robot_xml(xml)
    descriptor = D.terrain_grid(terrain)["descriptor"]
    spec = mujoco.MjSpec.from_string(robot.decode())
    D._environment_box_course(mujoco, spec, descriptor)
    spec.compile()
    text = spec.to_xml().encode()
    mujoco.MjModel.from_xml_string(text.decode())
    outdir = Path(out) / "outputs"
    outdir.mkdir(parents=True, exist_ok=True)
    name = Path(task["model"]["path"]).name
    (outdir / name).write_bytes(text)
    task["model"]["sha256"] = hashlib.sha256(text).hexdigest()
    task["terrain"] = descriptor
    (outdir / "run-task.json").write_text(json.dumps(task))
    return descriptor

BASE = {"form": "boxes", "collides_with": [1], "x_range_mm": [-2000.0, 9000.0],
        "y_range_mm": [-4000.0, 4000.0]}
KINDS = {
    "mild": {"seed": 47, "courses": 16, "clear_mm": 600.0, "run_mm": [400.0, 900.0], "step_mm": [15.0, 40.0],
             "grade_deg": [3.0, 8.0], "slope_mm": [500.0, 1000.0], "bump_mm": [10.0, 25.0],
             "bump_radius_mm": [120.0, 220.0], "bumps": 6},
    "moguls": {"seed": 81, "courses": 16, "bump_mm": [40.0, 80.0], "bump_radius_mm": [250.0, 400.0], "bumps": 8},
    "rock": {"seed": 82, "courses": 16, "rock_mm": [30.0, 60.0], "rock_radius_mm": [250.0, 400.0],
             "rocks": 3, "run_mm": [900.0, 1600.0], "clear_mm": 500.0},
    "platform50": {"seed": 83, "courses": 16, "platform_mm": [450.0, 500.0], "platforms": 2,
                   "clear_mm": 500.0},
    "mixed": {"seed": 84, "courses": 16, "step_mm": [50.0, 100.0], "grade_deg": [5.0, 15.0],
              "bump_mm": [30.0, 80.0], "bump_radius_mm": [250.0, 400.0], "bumps": 4,
              "platform_mm": [100.0, 500.0], "rock_mm": [30.0, 60.0], "run_mm": [600.0, 1200.0]},
}
# The run-out: a narrow course, so a wandering cat leaves its sides within seconds.
RUNOUT = {"form": "boxes", "collides_with": [1], "x_range_mm": [-1000.0, 3000.0],
          "y_range_mm": [-300.0, 300.0],
          "random": {"seed": 85, "courses": 16, "step_mm": [50.0, 100.0], "run_mm": [400.0, 800.0],
                     "clear_mm": 400.0}}

if __name__ == "__main__":
    bundle, outroot, *only = sys.argv[1:]
    for kind, rnd in list(KINDS.items()) + [("runout", None)]:
        if only and kind not in only:
            continue
        terrain = RUNOUT if rnd is None else {**BASE, "random": rnd}
        d = compose(bundle, terrain, f"{outroot}/{kind}")
        pool = d["pool"]
        print(kind, "slots", d["slots"], "dome_slots", d.get("dome_slots"),
              "boxes/course", [c["boxes"] for c in pool][:16], "domes", [c.get("domes", 0) for c in pool][:16],
              "highest", round(max(c["highest_mm"] for c in pool), 1))
