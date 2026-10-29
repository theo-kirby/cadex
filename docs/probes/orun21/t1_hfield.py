# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""T1: does a heightfield step stably in MJX-JAX? (winter-bay-5176, R1 T-3/C-23)

Run from ~/cadex-train-venv:  python docs/probes/orun21/t1_hfield.py [--quick]

One course, the ADR-716 measurement's features (two 40 mm bumps, an 80 mm
step up and down, a 15 degree ramp up and down), sampled by the engine's own
``CadexDynamics.terrain_grid`` and written as the engine writes it (normalised
``userdata``, 50 mm base), and as placed boxes for comparison. Four rigs:

- ``block``: ADR-714's rig, a box block with a box arm on a hinge, random
  +-0.8 N.m held 0.1 s; the case that went non-finite;
- ``block-spheres``: the same bodies, but only four corner spheres and an
  arm-tip sphere collide (R1 C-23: the sphere-heightfield pair);
- ``go1``: the orun18 Go1 (Playground's feet-only model, four sphere feet),
  position targets home +- 0.6 rad held 0.1 s, started at up to 3 m/s
  forward across the course's features;
- ``go1-shins``: the same Go1 with its capsule calves colliding too, to
  show whether the capsule-heightfield (convex) pair carries the defect.

For each rig, ground (plane, heightfield, boxes) and backend (MuJoCo, MJX) it
prints envs non-finite, the highest base, and the peak joint speed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex" / "cadex_tests"))
import dynamics_fixtures as fx  # noqa: E402

GO1 = Path.home() / "cadex-projects/orun21-lab/go1/outputs/go1-model.xml"

COURSE = {
    "x_range_mm": [-1000.0, 5000.0], "y_range_mm": [-1500.0, 1500.0], "cell_mm": 20.0,
    "features": [
        {"kind": "bump", "x_mm": 600.0, "y_mm": 150.0, "radius_mm": 250.0, "height_mm": 40.0},
        {"kind": "bump", "x_mm": 900.0, "y_mm": -200.0, "radius_mm": 250.0, "height_mm": 40.0},
        {"kind": "step", "x_mm": 1500.0, "height_mm": 80.0},
        {"kind": "step", "x_mm": 2200.0, "height_mm": -80.0},
        {"kind": "slope", "from_x_mm": 2800.0, "to_x_mm": 3300.0, "grade_deg": 15.0},
        {"kind": "slope", "from_x_mm": 3500.0, "to_x_mm": 4000.0, "grade_deg": -15.0},
    ],
}

BLOCK = """
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <body name="block" pos="0 0 0.06">
      <freejoint/>
      <geom name="b" type="box" size="0.1 0.06 0.04" mass="2" {box}/>
      {block_spheres}
      <body name="arm" pos="0.1 0 0.04">
        <joint name="hinge" type="hinge" axis="0 1 0" damping="0.01"/>
        <geom name="a" type="box" size="0.12 0.015 0.015" pos="0.12 0 0" mass="0.3" {box}/>
        {arm_sphere}
      </body>
    </body>
  </worldbody>
  <actuator><motor joint="hinge" ctrlrange="-0.8 0.8"/></actuator>
</mujoco>
"""


#: ADR-714's own course and rig (its deleted test, git 2594ca4c^), built by the
#: engine: a 100 x 40 x 20 mm block at z = 10 mm, a 300 mm arm hinged 30 mm
#: above it with no collision, an 0.8 N.m motor.
ADR714_COURSE = {
    "x_range_mm": [-400.0, 1600.0], "y_range_mm": [-400.0, 400.0], "cell_mm": 20.0,
    "features": [
        {"kind": "step", "x_mm": 400.0, "height_mm": 80.0},
        {"kind": "slope", "from_x_mm": 800.0, "to_x_mm": 1200.0, "grade_deg": -10.0},
        {"kind": "bump", "x_mm": 200.0, "y_mm": 200.0, "radius_mm": 100.0, "height_mm": 40.0},
    ],
}


def adr714_xml(ground: str, collision: str) -> str:
    block = (100.0, 40.0, 20.0)
    shape = (fx.collision_shape("box", size_mm=list(block)) if collision == "box"
             else fx.collision_shape("sphere", radius_mm=10.0))
    components, joints, _ = fx.build(
        [{"name": "block", "world": fx.frame((0.0, 0.0, 10.0)), "size": block,
          "collision": {"shapes": [shape], "mesh": None}},
         {"name": "arm", "size": (300.0, 40.0, 20.0)}],
        [{"name": "hinge", "kind": "revolute", "parent": "block", "child": "arm",
          "parent_frame": fx.frame((0.0, 0.0, 30.0), (1.0, 0.0, 0.0), 90.0),
          "child_frame": fx.frame((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0), "values": [0.0]}])
    motor = {"joint": "hinge", "motion_type": "angular", "kind": "motor",
             "control_nmm": "0", "torque_limit_nmm": 800.0}
    terrain = {"plane": None, "heightfield": ADR714_COURSE}.get(ground)
    if ground == "boxes":
        terrain = {k: v for k, v in ADR714_COURSE.items() if k != "cell_mm"}
        terrain["form"] = "boxes"
    built = CadexDynamics.build_model(components, joints, actuators=[motor],
                                      **({"terrain": terrain} if terrain else {}))
    return CadexDynamics.export_mjcf(built)["xml"].decode("utf-8")


def block_xml(spheres: bool) -> str:
    if not spheres:
        return BLOCK.format(box="", block_spheres="", arm_sphere="")
    corners = "".join(
        f'<geom type="sphere" size="0.02" pos="{sx * 0.08} {sy * 0.045} -0.03" mass="0.01"/>'
        for sx in (-1, 1) for sy in (-1, 1))
    return BLOCK.format(box='contype="0" conaffinity="0"', block_spheres=corners,
                        arm_sphere='<geom type="sphere" size="0.02" pos="0.24 0 0" mass="0.01"/>')


def with_ground(spec: mujoco.MjSpec, ground: str, floor: dict) -> None:
    """Replace any plane with the engine's course in ``ground`` form."""

    for geom in list(spec.geoms):
        if geom.type == mujoco.mjtGeom.mjGEOM_PLANE:
            spec.delete(geom)
    world = spec.worldbody
    if ground == "plane":
        world.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.01], **floor)
        return
    if ground == "heightfield":
        grid = CadexDynamics.terrain_grid(COURSE)
        d = grid["descriptor"]
        lo, hi = d["lowest_mm"], d["highest_mm"]
        (x0, x1), (y0, y1) = d["x_range_mm"], d["y_range_mm"]
        spec.add_hfield(name="course", size=[(x1 - x0) / 2000, (y1 - y0) / 2000, (hi - lo) / 1000,
                                             CadexDynamics.TERRAIN_BASE_MM / 1000],
                        nrow=int(d["nrow"]), ncol=int(d["ncol"]),
                        userdata=[(h - lo) / (hi - lo) for h in grid["heights_mm"]])
        world.add_geom(type=mujoco.mjtGeom.mjGEOM_HFIELD, hfieldname="course",
                       pos=[(x0 + x1) / 2000, (y0 + y1) / 2000, lo / 1000], **floor)
        return
    boxes = dict(COURSE, form="boxes")
    boxes.pop("cell_mm")
    d = CadexDynamics.terrain_grid(boxes)["descriptor"]
    world.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.01],
                   pos=[0, 0, d["lowest_mm"] / 1000], **floor)
    placed = CadexDynamics.terrain_box_geoms(d["boxes"], d["lowest_mm"], None)
    for pos, quat, half in zip(placed["pos_m"], placed["quat"], placed["size_m"]):
        world.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=pos, quat=quat, size=half, **floor)


def build(rig: str, ground: str) -> mujoco.MjModel:
    if rig.startswith("adr714"):
        return mujoco.MjModel.from_xml_string(
            adr714_xml(ground, "sphere" if rig == "adr714-sphere" else "box"))
    if rig.startswith("block"):
        spec = mujoco.MjSpec.from_string(block_xml(rig == "block-spheres"))
        floor = {"friction": [1.0, 0.005, 0.0001], "condim": 3}
    else:
        spec = mujoco.MjSpec.from_file(str(GO1))
        floor = {"friction": [0.6, 0.005, 0.0001], "contype": 1, "conaffinity": 0, "priority": 1}
        if rig == "go1-shins":
            for geom in spec.geoms:
                body = geom.parent.name if geom.parent else ""
                if body.endswith("calf") and geom.type == mujoco.mjtGeom.mjGEOM_CAPSULE:
                    geom.conaffinity = 1
    with_ground(spec, ground, floor)
    return spec.compile()


def plan(model: mujoco.MjModel, rig: str, envs: int, steps: int, seed: int):
    """Initial states and the control sequence, shared by both backends."""

    rng = np.random.default_rng(seed)
    data = mujoco.MjData(model)
    q0 = np.tile(model.key_qpos[0] if model.nkey else data.qpos, (envs, 1))
    v0 = np.zeros((envs, model.nv))
    if rig.startswith("go1"):
        q0[:, 0] = rng.uniform(-0.3, 3.8, envs)
        q0[:, 1] = rng.uniform(-0.4, 0.4, envs)
        # Stand on the course's local height, not z = 0.
        for i in range(envs):
            q0[i, 2] += CadexDynamics.terrain_height_mm(COURSE["features"], q0[i, 0] * 1e3,
                                                        q0[i, 1] * 1e3) / 1e3 + 0.03
        v0[:, 0] = rng.uniform(0.0, 3.0, envs)
        home = model.key_ctrl[0]
        hold = rng.uniform(-0.6, 0.6, (steps // 5 + 1, envs, model.nu))
        ctrl = np.clip(home + np.repeat(hold, 5, axis=0)[:steps], model.actuator_ctrlrange[:, 0],
                       model.actuator_ctrlrange[:, 1])
    elif rig.startswith("adr714"):
        # ADR-715's draw: the solved pose at the origin, +-0.8 N.m held 10 steps.
        hold = rng.uniform(-1.0, 1.0, (steps // 5 + 1, envs, model.nu))
        ctrl = np.repeat(hold, 5, axis=0)[:steps] * model.actuator_forcerange[:, 1]
    else:
        q0[:, 0] = rng.uniform(-0.3, 3.8, envs)
        for i in range(envs):
            q0[i, 2] = 0.045 + CadexDynamics.terrain_height_mm(
                COURSE["features"], q0[i, 0] * 1e3, 0.0) / 1e3
        hold = rng.uniform(-0.8, 0.8, (steps // 5 + 1, envs, model.nu))
        ctrl = np.repeat(hold, 5, axis=0)[:steps]
    return q0, v0, ctrl


def substeps(model: mujoco.MjModel, rig: str) -> int:
    # Each control holds for 5 controls of ``substeps`` physics steps: 0.1 s
    # on the Go1 (4 ms) and the hand block (2 ms), 10 solver steps on ADR-714's.
    return 2 if rig.startswith("adr714") else 5


def summarise(qpos: np.ndarray, qvel: np.ndarray, finite_until: np.ndarray, steps: int) -> dict:
    return {
        "nonfinite": int((finite_until < steps).sum()),
        "first_nonfinite": int(finite_until.min()) if (finite_until < steps).any() else None,
        "top_base_m": float(np.nanmax(np.where(np.isfinite(qpos[..., 2]), qpos[..., 2], np.nan))),
        "peak_joint_rad_s": float(np.nanmax(np.abs(np.where(np.isfinite(qvel[..., 6:]),
                                                            qvel[..., 6:], np.nan)))),
    }


def run_mujoco(model, rig, q0, v0, ctrl):
    envs, steps = q0.shape[0], ctrl.shape[0]
    data = mujoco.MjData(model)
    qp = np.full((steps, envs, model.nq), np.nan)
    qv = np.full((steps, envs, model.nv), np.nan)
    until = np.full(envs, steps)
    for i in range(envs):
        mujoco.mj_resetData(model, data)
        data.qpos[:], data.qvel[:] = q0[i], v0[i]
        for t in range(steps):
            data.ctrl[:] = ctrl[t, i]
            for _ in range(substeps(model, rig)):
                mujoco.mj_step(model, data)
            if not (np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()):
                until[i] = t
                break
            qp[t, i], qv[t, i] = data.qpos, data.qvel
    return summarise(qp, qv, until, steps)


def run_mjx(model, rig, q0, v0, ctrl):
    import jax
    import jax.numpy as jnp
    from mujoco import mjx

    m = mjx.put_model(model)
    n = substeps(model, rig)

    def one(q, v, us):
        d = mjx.make_data(m).replace(qpos=q, qvel=v)

        def control(d, u):
            d = d.replace(ctrl=u)
            d = jax.lax.fori_loop(0, n, lambda _, d: mjx.step(m, d), d)
            return d, (d.qpos, d.qvel)

        _, out = jax.lax.scan(control, d, us)
        return out

    run = jax.jit(jax.vmap(one, in_axes=(0, 0, 1), out_axes=1))
    qp, qv = run(jnp.asarray(q0, jnp.float32), jnp.asarray(v0, jnp.float32),
                 jnp.asarray(ctrl, jnp.float32))
    qp, qv = np.asarray(qp, np.float64), np.asarray(qv, np.float64)
    bad = ~(np.isfinite(qp).all(-1) & np.isfinite(qv).all(-1))
    steps = ctrl.shape[0]
    until = np.where(bad.any(0), bad.argmax(0), steps)
    for i, u in enumerate(until):
        qp[u:, i] = np.nan
        qv[u:, i] = np.nan
    return summarise(qp, qv, until, steps)


#: The training screen's course: 30 x 30 m at 100 mm, 64 raised-cosine bumps
#: and dips of 30-60 mm on a 3.5 m grid clear of the origin (Playground's
#: rough Go1 is 5 cm of relief), so an episode does not walk off it.
def screen_course(seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    features = []
    for i in range(8):
        for j in range(8):
            features.append({"kind": "bump", "x_mm": -12250.0 + 3500.0 * i,
                             "y_mm": -12250.0 + 3500.0 * j,
                             "radius_mm": float(rng.uniform(900.0, 1500.0)),
                             "height_mm": float(rng.choice([-1, 1]) * rng.uniform(30.0, 60.0))})
    return {"x_range_mm": [-15000.0, 15000.0], "y_range_mm": [-15000.0, 15000.0],
            "cell_mm": 100.0, "features": features}


def write_go1_bundle(out: Path) -> None:
    """The orun18 Go1 joystick bundle with its plane swapped for the course."""

    import hashlib
    global COURSE
    task_path = GO1.parent / "go1_joystick-task.json"
    task = json.loads(task_path.read_text())
    COURSE = screen_course()
    spec = mujoco.MjSpec.from_file(str(GO1))
    with_ground(spec, "heightfield",
                {"friction": [0.6, 0.005, 0.0001], "contype": 1, "conaffinity": 0, "priority": 1})
    spec.compile()
    xml = spec.to_xml().encode()
    out.mkdir(parents=True, exist_ok=True)
    (out / "go1-hfield-model.xml").write_bytes(xml)
    task["model"] = dict(task["model"], path="go1-hfield-model.xml", bytes=len(xml),
                         sha256=hashlib.sha256(xml).hexdigest())
    task["terrain"] = CadexDynamics.terrain_grid(COURSE)["descriptor"]
    task["label"] = "go1 joystick on a heightfield (orun21 T1)"
    (out / "go1-hfield-task.json").write_text(json.dumps(task, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rigs", default="adr714,adr714-sphere,go1,go1-shins")
    parser.add_argument("--grounds", default="plane,heightfield,boxes")
    parser.add_argument("--envs", type=int, default=32)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--mujoco-envs", type=int, default=32)
    parser.add_argument("--out")
    parser.add_argument("--bundle", help="write the Go1 heightfield screen's bundle here and stop")
    args = parser.parse_args()
    if args.bundle:
        write_go1_bundle(Path(args.bundle))
        return
    rows = []
    for rig in args.rigs.split(","):
        for ground in args.grounds.split(","):
            model = build(rig, ground)
            q0, v0, ctrl = plan(model, rig, args.envs, args.steps, args.seed)
            for backend in ("mujoco", "mjx"):
                k = args.mujoco_envs if backend == "mujoco" else args.envs
                start = time.time()
                fn = run_mujoco if backend == "mujoco" else run_mjx
                row = fn(model, rig, q0[:k], v0[:k], ctrl[:, :k])
                row.update(rig=rig, ground=ground, backend=backend, envs=k,
                           wall_s=round(time.time() - start, 1), ngeom=model.ngeom)
                rows.append(row)
                print(json.dumps(row), flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
