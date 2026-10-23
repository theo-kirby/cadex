"""orun19 S2: is the speed track_speed rewards (comv_x) the speed the judge measures?

Three checks, none needing the GPU:

``sensor MODEL_XML``
    MJX's ``subtreelinvel`` on the root (the ``comv`` observation, obs/64)
    against stock MuJoCo's and a finite-difference COM velocity, at the
    ``solved`` keyframe with random joint velocities.
``judged MODEL_XML EVAL_DIR...``
    On judged evaluations, the whole-body COM (every body's mass at its
    ``ipos`` under the trace's component placements) against the judge's base
    point (``rig.base_com_local_mm`` on ``c_chest_frame``), over the last 2 s,
    and the within-window spread of the COM's forward speed.
``witness ROLLOUT_TRACE...``
    The trainer's own deterministic witness rollout (MJX, nominal command):
    chest-frame speed per 2 s window against the goal.

Run with ``~/cadex-train-venv/bin/python`` (numpy, scipy, mujoco, mjx) and
``JAX_PLATFORMS=cpu``.
"""

from __future__ import annotations

import json
import statistics
import sys

import numpy as np


def sensor(xml_path: str) -> None:
    import jax
    import mujoco
    from mujoco import mjx

    m = mujoco.MjModel.from_xml_path(xml_path)
    adr = m.sensor_adr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SENSOR, "obs/64")]
    key = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "solved")
    rng = np.random.default_rng(0)
    mx, fwd = mjx.put_model(m), jax.jit(mjx.forward)
    for trial in range(4):
        d = mujoco.MjData(m)
        mujoco.mj_resetDataKeyframe(m, d, key)
        d.qvel[:] = rng.normal(0, 1.0, m.nv)
        d.qvel[0] = 3.5 + 0.3 * trial
        mujoco.mj_forward(m, d)
        dt, q2 = 1e-6, d.qpos.copy()
        mujoco.mj_integratePos(m, q2, d.qvel, dt)
        d2 = mujoco.MjData(m)
        d2.qpos[:] = q2
        mujoco.mj_kinematics(m, d2)
        mujoco.mj_comPos(m, d2)
        true = (d2.subtree_com[1] - d.subtree_com[1]) / dt
        via_mjx = np.asarray(fwd(mx, mjx.put_data(m, d)).sensordata[adr:adr + 3])
        print(f"root qvel {d.qvel[:3].round(3)} | mujoco {d.sensordata[adr:adr + 3].round(4)} "
              f"| mjx {via_mjx.round(4)} | finite-difference COM {true.round(4)}")


def judged(xml_path: str, evals: list[str]) -> None:
    import mujoco
    from scipy.spatial.transform import Rotation as R

    m = mujoco.MjModel.from_xml_path(xml_path)
    bodies = [(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i), m.body_mass[i], m.body_ipos[i] * 1000.0)
              for i in range(1, m.nbody)]
    mass = sum(b[1] for b in bodies)
    for ev_dir in evals:
        ev = json.load(open(f"{ev_dir}/evaluation.json"))
        local = np.asarray(ev["rig"]["base_com_local_mm"])
        rows = []
        for seed in ev["seeds"]:
            trace = json.load(open(f"{ev_dir}/{seed['trace']['file']}"))
            frames = [f for f in trace["frames"] if f["frame_kind"] == "solver_output"]
            t = np.asarray([f["nominal_time_s"] for f in frames])
            com, base = [], []
            for f in frames:
                placed = f["component_placements"]
                c = sum(mb * (np.asarray(placed[n]["position_mm"]) + R.from_quat(placed[n]["rotation_xyzw"]).apply(ip))
                        for n, mb, ip in bodies)
                com.append(c / mass)
                chest = placed["c_chest_frame"]
                base.append(np.asarray(chest["position_mm"]) + R.from_quat(chest["rotation_xyzw"]).apply(local))
            com, base = np.asarray(com), np.asarray(base)
            w = t >= t[-1] - 2.0
            i0, i1 = np.where(w)[0][[0, -1]]
            span = t[i1] - t[i0]
            rows.append(((com[i1, 0] - com[i0, 0]) / span / 1000, (base[i1, 0] - base[i0, 0]) / span / 1000,
                         float(np.std(np.gradient(com[:, 0], t)[w])) / 1000))
        cmd = ev["judged_command_mm_s"]
        c, b, sd = (statistics.median(r[k] for r in rows) for k in range(3))
        print(f"cmd {cmd:>5}: COM {c:.3f} m/s, base {b:.3f} m/s, COM/base {c / b:.4f}, "
              f"COM/cmd {c * 1000 / cmd:.3f}, COM forward-speed sd in window {sd:.3f} m/s "
              f"({sd * 1000 / cmd:.1%} of cmd); mass {mass:.2f} kg")


def witness(traces: list[str]) -> None:
    for path in traces:
        trace = json.load(open(path))
        frames = [f for f in trace["frames"] if f["frame_kind"] == "solver_output"]
        t = np.asarray([f["nominal_time_s"] for f in frames])
        goal = np.asarray([f["goal"][0] for f in frames])
        x = np.asarray([f["component_placements"]["c_chest_frame"]["position_mm"][0] for f in frames])
        print(path)
        for a in np.arange(0.0, t[-1] - 1.99, 2.0):
            w = (t >= a) & (t <= a + 2.0)
            v = (x[w][-1] - x[w][0]) / (t[w][-1] - t[w][0])
            print(f"  {a:4.1f}-{a + 2:4.1f} s  goal {goal[w].mean():6.0f}  speed {v / 1000:.3f} m/s  "
                  f"speed/goal {v / goal[w].mean():.3f}")


if __name__ == "__main__":
    verb, rest = sys.argv[1], sys.argv[2:]
    {"sensor": lambda: sensor(rest[0]), "judged": lambda: judged(rest[0], rest[1:]),
     "witness": lambda: witness(rest)}[verb]()
