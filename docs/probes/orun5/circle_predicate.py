"""P1's circle predicate on the rig's own physics: a rocking ball fails it, a circling one passes.

Drives an exported ball-and-plate MJCF with a scripted tracker -- no
policy: the plate tilts by a PD law on the ball's true position towards a
moving target -- under two targets, and holds each 10 s trace against the
task bundle's own
success predicates with Cadex's evaluator (``CadexEvaluation.motion_metrics``
and ``check``, ADR-587):

* ``rock``: the ball starts on the circle and the plate swings it back and
  forth across the circle's top, the failure a circle spec bounding only
  the radius passes (net turns about zero);
* ``circle``: the plate tilts in the circle's phase, so the ball goes round.

Usage::

    pixi run python docs/probes/orun5/circle_predicate.py RUN_DIR [--task task_circle] [--plot OUT.png]

``RUN_DIR`` is a ``cadex train --out`` directory holding ``model-model.xml``
and ``<task>-task.json``. Prints one JSON object: per target, the motion
metrics and every predicate row.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as evaluation  # noqa: E402

RADIUS_MM = 40.0
ROLLING = 5.0 / 7.0 * 9.81      # a solid ball's acceleration per radian of tilt, m/s^2


def target(kind: str, t: float) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """The ball's target position (m), velocity (m/s) and acceleration (m/s^2) on the panel at ``t``."""

    r = RADIUS_MM / 1000.0
    if kind == "rock":
        # back and forth 25 mm either side of the circle's top, at 0.4 Hz: a bearing swing of about +/-35 degrees
        w, a = 2.0 * math.pi * 0.4, 0.025
        s, c = math.sin(w * t), math.cos(w * t)
        return (a * s, r), (a * w * c, 0.0), (-a * w * w * s, 0.0)
    w = 2.0 * math.pi * 0.3          # 3 laps in 10 s
    s, c = math.sin(w * t), math.cos(w * t)
    return (r * c, r * s), (-r * w * s, r * w * c), (-r * w * w * c, -r * w * w * s)


KP, KD = 9.0, 4.2                   # 3 rad/s, damping 0.7


def tilt(kind: str, t: float, position, velocity) -> tuple[float, float]:
    """(roll, pitch) targets in radians. Pitch rolls the ball along +x, roll along -y."""

    (px, py), (vx, vy), (ax, ay) = target(kind, t)
    cx = ax + KP * (px - position[0]) + KD * (vx - velocity[0])
    cy = ay + KP * (py - position[1]) + KD * (vy - velocity[1])
    limit = math.radians(8.0)
    return max(-limit, min(limit, -cy / ROLLING)), max(-limit, min(limit, cx / ROLLING))


def pose(position_m, quat_wxyz) -> dict:
    w, x, y, z = (float(v) for v in quat_wxyz)
    return {"position_mm": [float(v) * 1000.0 for v in position_m], "rotation_xyzw": [x, y, z, w]}


def run(model_path: Path, bundle: dict, kind: str) -> tuple[list, bool, list]:
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved"))
    ball = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "c_ball")
    plate = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "c_plate")
    free = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "c_ball/free")]
    dof = model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "c_ball/free")]
    (x0, y0), (vx, vy), _ = target(kind, 0.0)
    data.qpos[free:free + 2] += (x0, y0)
    data.qvel[dof:dof + 2] = (vx, vy)
    mujoco.mj_forward(model, data)
    # The plate's component frame is the world at the solved pose, so its pose now is the body's
    # motion since then; the ball is built about its centre, so its body frame is the point read.
    p0, q0 = data.xpos[plate].copy(), data.xquat[plate].copy()
    q0_inv = np.zeros(4)
    mujoco.mju_negQuat(q0_inv, q0)
    roll_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "j_roll/position")
    pitch_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "j_pitch/position")
    episode = bundle["episode"]
    steps, per = int(episode["max_steps"]), int(episode["solver_steps_per_action"])
    edge_mm = 62.5
    samples, path, completed = [], [], True
    for step in range(steps + 1):
        dq = np.zeros(4)
        mujoco.mju_mulQuat(dq, data.xquat[plate], q0_inv)
        rot = np.zeros(9)
        mujoco.mju_quat2Mat(rot, dq)
        origin = data.xpos[plate] - rot.reshape(3, 3) @ p0
        placements = {"c_plate": pose(origin, dq), "c_ball": pose(data.xpos[ball], data.xquat[ball])}
        samples.append((data.time, placements))
        local = rot.reshape(3, 3).T @ (data.xpos[ball] - origin) * 1000.0 - np.array([0.0, 0.0, 159.5])
        path.append((float(local[0]), float(local[1])))
        if math.hypot(local[0], local[1]) > edge_mm or abs(local[2]) > 3.0:
            completed = False
            break
        if step == steps:
            break
        velocity = rot.reshape(3, 3).T @ data.qvel[dof:dof + 3]
        data.ctrl[roll_act], data.ctrl[pitch_act] = tilt(kind, data.time, (local[0] / 1000.0, local[1] / 1000.0),
                                                         velocity)
        for _ in range(per):
            mujoco.mj_step(model, data)
    return samples, completed, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--task", default="task_circle")
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()
    bundle = json.loads((args.run_dir / f"{args.task}-task.json").read_text())
    spec = bundle["success"]
    rig = {"body": spec["body"], "centre": spec["centre"]}
    report, paths = {}, {}
    for kind in ("rock", "circle"):
        samples, completed, paths[kind] = run(args.run_dir / "model-model.xml", bundle, kind)
        measured = evaluation.motion_metrics(samples, rig, completed=completed)
        metrics = {"completed": 1.0 if completed else 0.0,
                   **{k: v for k, v in measured.items() if k != "motion"}}
        rows = evaluation.check(spec["predicates"], metrics)
        report[kind] = {"metrics": metrics, "predicates": rows, "pass": all(r["pass"] for r in rows)}
    print(json.dumps(report, indent=2))
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(8, 4.2), facecolor="#16181c")
        for ax, kind in zip(axes, ("rock", "circle")):
            xs, ys = zip(*paths[kind])
            ax.set_facecolor("#16181c")
            ax.add_patch(plt.Circle((0, 0), RADIUS_MM, fill=False, ls="--", color="#6b7078"))
            ax.plot(xs, ys, color="#d8602a", lw=1.2)
            ax.plot(xs[0], ys[0], "o", color="#e6e0d2", ms=4)
            m = report[kind]["metrics"]
            verdict = "pass" if report[kind]["pass"] else "fail"
            ax.set_title(f"{kind}: turns {m['turns']:+.2f}, laps {m['laps']:.0f}, "
                         f"mean r {m['mean_distance_mm']:.1f} mm -> {verdict}", color="#e6e0d2", fontsize=9)
            ax.set_xlim(-65, 65), ax.set_ylim(-65, 65), ax.set_aspect("equal")
            ax.tick_params(colors="#9aa0a8", labelsize=7)
            for side in ax.spines.values():
                side.set_color("#3a3e45")
            ax.set_xlabel("ball x on the panel, mm", color="#9aa0a8", fontsize=8)
        fig.tight_layout()
        fig.savefig(args.plot, dpi=110, facecolor=fig.get_facecolor())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
