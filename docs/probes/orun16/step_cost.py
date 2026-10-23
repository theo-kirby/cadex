"""orun16 Q2: what a 1 ms solver step costs per simulated second, on the CPU.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/step_cost.py MODEL_XML [SECONDS]

Steps the model as built (2 ms) and as ``rod_solver.py``'s ``dt1`` patch
(1 ms, every equality at 0.002 s: what a build at ``solver_step_s`` 0.001
gives) from its first keyframe (or qpos0) for SECONDS of simulated time
with the actuators held at zero, three repeats, and prints the wall time per
simulated second and the ratio. Zero control drops the cat onto the floor,
so the timed steps carry contacts and every loop constraint. This is the
CPU solver's cost; MJX's per-iteration cost is measured when a bundle at
1 ms is timed on the GPU.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rod_solver import patch  # noqa: E402


def wall_per_sim_s(xml: str, seconds: float) -> tuple[float, float]:
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    best = float("inf")
    for _ in range(3):
        if model.nkey:
            mujoco.mj_resetDataKeyframe(model, data, 0)
        else:
            mujoco.mj_resetData(model, data)
        steps = int(round(seconds / model.opt.timestep))
        start = time.perf_counter()
        for _ in range(steps):
            mujoco.mj_step(model, data)
        best = min(best, (time.perf_counter() - start) / seconds)
    return model.opt.timestep, best


def main(argv: list[str]) -> int:
    xml = Path(argv[1]).read_text()
    seconds = float(argv[2]) if len(argv) > 2 else 2.0
    rows = {name: wall_per_sim_s(patch(xml, name), seconds) for name in ("base", "dt1")}
    for name, (dt, wall) in rows.items():
        print(f"{name}: step {dt * 1000:g} ms, {wall * 1000:.1f} ms wall per simulated s")
    print(f"ratio dt1 / base: {rows['dt1'][1] / rows['base'][1]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
