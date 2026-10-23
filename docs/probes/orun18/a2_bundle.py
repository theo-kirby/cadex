"""orun18 A2: Playground's Go1 joystick (flat) as a Cadex task bundle.

The smallest honest route to "the same robot through Cadex's trainer": a
`cadex-training-task-v1` bundle written around Playground's own
`scene_mjx_feetonly_flat_terrain.xml`, so the model, its physics options and
its contact setup are Playground's, and only the task is re-said in the
bundle's language. Ported from orun6 B1's body-frame generator (ADR-712's
evidence, not committed then), with Playground's domain randomisation added
where the bundle's `randomisation` (per-environment scale draws) can say it.

What the bundle cannot say goes to `gaps.json` beside it, and into D2's table
(`a2.md`). One thing outside the *script* language is used on purpose: the
policy reads the trunk's body-frame velocity, gyro and gravity (a velocimeter,
a gyro and a framezaxis with a reference frame on MJCF sensor rows), which the
trainer gathers by address like any other sensor. Playground's policy reads
the same three; orun6 B1 measured the world-frame version as the worse one.

Reads a fetched third-party model (Menagerie `unitree_go1`, BSD-3-Clause, via
Playground 0.2.0, Apache-2.0; `SOURCES.md`); writes outside the repository.
Run with the Cadex training venv (mujoco 3.10.0, the version the bundle
records):

    ~/cadex-train-venv/bin/python -I a2_bundle.py \
        ~/playground-venv/lib/python3.12/site-packages/mujoco_playground/_src/locomotion/go1/xmls \
        ~/orun18/a2 ~/cadex-projects/leo/runs/sgt-4/train/gallop_sg-task.json

The third argument is any engine-written bundle; its `goal_algorithm` and
`variation_algorithm` strings are copied so this bundle states the engine's
own algorithms rather than paraphrasing them.
"""
import ast
import hashlib
import json
import math
import sys
from pathlib import Path

import mujoco

XMLS = Path(sys.argv[1])
ROOT = Path(sys.argv[2]).expanduser()
ENGINE_BUNDLE = Path(sys.argv[3]).expanduser()
DT = 0.02
RAD = 180.0 / math.pi
LEGS = ["FR", "FL", "RR", "RL"]
PARTS = ["hip", "thigh", "calf"]
FUNCTIONS = ["abs", "arcsin", "arctan", "asin", "cos", "exp", "sin", "sqrt", "tanh"]
ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
           ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UAdd, ast.USub)
REWARD_TERMS_CAP = 32       # CadexDynamics.MAXIMUM_REWARD_TERMS
FORMULA_NODES = 512         # cadex_assembly_api._REWARD_FORMULA_NODES
FORMULA_CHARACTERS = 2048   # cadex_assembly_api._REWARD_FORMULA_CHARACTERS
CHANNELS_CAP = 128


def fits(formula):
    """cadex_assembly_api's expression rule: why it would be refused, or None."""
    if len(formula) > FORMULA_CHARACTERS:
        return f"{len(formula)} characters > {FORMULA_CHARACTERS}"
    nodes = list(ast.walk(ast.parse(formula, mode="eval")))
    if len(nodes) > FORMULA_NODES:
        return f"{len(nodes)} AST nodes > {FORMULA_NODES}"
    bad = [type(n).__name__ for n in nodes if not isinstance(n, ALLOWED)]
    return f"unsupported {bad}" if bad else None


def playground_spec():
    """Playground's scene, as its `Go1Env.__init__` leaves it, less meshes.

    base.py applies sim_dt 0.004, ccd_iterations 20 and Kp 35 at load (Kd 0.5
    is already the class's joint damping). Every body states its inertial, so
    the visual meshes carry no mass and are dropped (the referee checks the
    masses against Playground's own compiled model)."""
    spec = mujoco.MjSpec.from_file(str(XMLS / "scene_mjx_feetonly_flat_terrain.xml"))
    for geom in list(spec.geoms):
        if geom.type == mujoco.mjtGeom.mjGEOM_MESH:
            spec.delete(geom)
    for mesh in list(spec.meshes):
        spec.delete(mesh)
    spec.option.timestep = 0.004
    spec.option.ccd_iterations = 20
    for actuator in spec.actuators:
        actuator.gainprm[0] = 35.0
        actuator.biasprm[1] = -35.0
    return spec


spec = playground_spec()
for sensor in list(spec.sensors):
    spec.delete(sensor)
for key in list(spec.keys):
    if key.name != "home":
        spec.delete(key)
# A foot frame the reward reads: a geom-less, massless body at the sphere's
# centre, so the sphere and its contact stay on the calf as Playground has it.
for leg in LEGS:
    foot = spec.geom(leg)
    spec.body(f"{leg}_calf").add_body(name=f"{leg}_foot", pos=list(foot.pos))
    site = spec.site(leg)
    if site is not None:
        spec.delete(site)

observations = []
joints = [f"{leg}_{part}_joint" for leg in LEGS for part in PARTS]
short = {f"{leg}_{part}_joint": f"{leg}{part[0]}" for leg in LEGS for part in PARTS}
J, X, SITE = mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_XBODY, mujoco.mjtObj.mjOBJ_SITE
S = mujoco.mjtSensor


def add(name, channels, kind, target, stype, objtype, scale, unit, role="policy", objname=None):
    index = len(observations)
    spec.add_sensor(name=f"obs/{index}", type=stype, objtype=objtype, objname=objname or target)
    observations.append(dict(name=name, channels=channels, kind=kind, target=target,
                             scale=scale, unit=unit, role=role, sensor=f"obs/{index}"))
    return spec.sensor(f"obs/{index}")


# The policy's 45 sensor channels, Playground's order: body-frame linear
# velocity, gyro, gravity in the body frame, joint positions, joint velocities
# (Playground subtracts the home pose from the positions; the normaliser
# removes any constant offset, so it is not repeated here).
if spec.site("cadex_imu") is None:
    spec.body("trunk").add_site(name="cadex_imu", pos=[0, 0, 0])
add("bv", ["bvx", "bvy", "bvz"], "body_linear_velocity", "trunk", S.mjSENS_VELOCIMETER,
    SITE, 1000.0, "mm/s", objname="cadex_imu")
add("bw", ["bwx", "bwy", "bwz"], "body_angular_velocity", "trunk", S.mjSENS_GYRO,
    SITE, RAD, "deg/s", objname="cadex_imu")
g = add("g", ["gx", "gy", "gz"], "gravity_in_body", "world", S.mjSENS_FRAMEZAXIS, X, 1.0, "1")
g.reftype, g.refname = X, "trunk"
for joint in joints:
    add(f"q{short[joint]}", [f"q{short[joint]}"], "position", joint, S.mjSENS_JOINTPOS, J, RAD, "deg")
for joint in joints:
    add(f"d{short[joint]}", [f"d{short[joint]}"], "velocity", joint, S.mjSENS_JOINTVEL, J, RAD, "deg/s")
# The critic's, and the reward's.
add("q", ["qw", "qx", "qy", "qz"], "component_orientation", "trunk", S.mjSENS_FRAMEQUAT, X, 1.0, "quat", role="privileged")
add("w", ["wx", "wy", "wz"], "component_angular_velocity", "trunk", S.mjSENS_FRAMEANGVEL, X, RAD, "deg/s", role="privileged")
add("v", ["vx", "vy", "vz"], "component_linear_velocity", "trunk", S.mjSENS_FRAMELINVEL, X, 1000.0, "mm/s", role="privileged")
for leg in LEGS:
    add(f"p{leg}", [f"p{leg}_x", f"p{leg}_y", f"p{leg}_z"], "component_position",
        f"{leg}_foot", S.mjSENS_FRAMEPOS, X, 1000.0, "mm", role="privileged")
for joint in joints:
    add(f"tau{short[joint]}", [f"tau{short[joint]}"], "actuator_force", joint.replace("_joint", ""),
        S.mjSENS_ACTUATORFRC, mujoco.mjtObj.mjOBJ_ACTUATOR, 1000.0, "nmm", role="privileged")
# ADR-698's contact: a touch sensor on a box site round the calf's only
# colliding geom, the foot sphere.
compiled_once = spec.compile()
for leg in LEGS:
    calf = compiled_once.body(f"{leg}_calf").id
    shapes = [i for i in range(compiled_once.ngeom) if compiled_once.geom_bodyid[i] == calf
              and (compiled_once.geom_contype[i] or compiled_once.geom_conaffinity[i])]
    assert len(shapes) == 1, (leg, shapes)
    lo = [min(compiled_once.geom_pos[i][k] - compiled_once.geom_rbound[i] for i in shapes) for k in range(3)]
    hi = [max(compiled_once.geom_pos[i][k] + compiled_once.geom_rbound[i] for i in shapes) for k in range(3)]
    index = len(observations)
    spec.body(f"{leg}_calf").add_site(
        name=f"obs/{index}/contact", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[(a + b) / 2 for a, b in zip(lo, hi)], size=[(b - a) / 2 for a, b in zip(lo, hi)],
        rgba=[0, 0, 0, 0])
    add(f"k{leg}", [f"k{leg}", f"k{leg}_down"], "contact", f"obs/{index}/contact",
        S.mjSENS_TOUCH, SITE, 1.0, "n", role="privileged")
    observations[-1]["contact"] = {"body": f"{leg}_calf", "down_above_n": 0.0}
    observations[-1]["target"] = f"{leg}_calf"
for leg in LEGS:
    add(f"u{leg}", [f"u{leg}_x", f"u{leg}_y", f"u{leg}_z"], "component_linear_velocity",
        f"{leg}_foot", S.mjSENS_FRAMELINVEL, X, 1000.0, "mm/s", role="privileged")

xml = spec.to_xml().encode()
check = mujoco.MjModel.from_xml_string(xml.decode())
for row in observations:
    sid = mujoco.mj_name2id(check, mujoco.mjtObj.mjOBJ_SENSOR, row["sensor"])
    row["adr"], row["dim"] = int(check.sensor_adr[sid]), int(check.sensor_dim[sid])
# A contact row reports its force and a derived down flag: one sensordata
# value, two channels.
scalar_channels = sum(len(r["channels"]) for r in observations)
assert scalar_channels <= CHANNELS_CAP, scalar_channels

home = check.key("home")
default = {j: float(home.qpos[check.jnt_qposadr[check.joint(j).id]]) for j in joints}
lower = {j: float(check.jnt_range[check.joint(j).id][0]) for j in joints}
upper = {j: float(check.jnt_range[check.joint(j).id][1]) for j in joints}

# -- actions: Playground's home + 0.5 * tanh-normal, clipped to the range ---
actions = []
for joint in joints:
    aid = [i for i in range(check.nu) if check.actuator_trnid[i][0] == check.joint(joint).id][0]
    lo = max(default[joint] - 0.5, lower[joint]) * RAD
    hi = min(default[joint] + 0.5, upper[joint]) * RAD
    actions.append({"actuator": check.actuator(aid).name, "fallback": "0", "high": round(hi, 6),
                    "index": int(aid), "joint": joint, "kind": "position", "low": round(lo, 6),
                    "motion_type": "angular", "scale": math.pi / 180.0,
                    "source": "playground_action_scale_0.5_rad", "unit": "deg"})

# ADR-696: the policy reads its own previous command, as Playground's reads
# last_act; the rate is the action-rate term's input.
commands = [{"name": f"c{short[a['joint']]}", "kind": "command", "target": a["joint"],
             "actuator": a["actuator"], "action": i,
             "channels": [f"c{short[a['joint']]}", f"c{short[a['joint']]}_rate"],
             "unit": "deg", "rate_unit": "deg/s"} for i, a in enumerate(actions)]

# -- reward: Playground's terms, each weight times dt -------------------------
# Body-frame velocity and yaw rate, as Playground's local_linvel and gyro.
terms = [
    ("tracking_lin_vel", 1.0, "exp(-(((cx-bvx)/1000)**2+((cy-bvy)/1000)**2)/0.25)"),
    ("tracking_ang_vel", 0.5, f"exp(-((cw-bwz)/{RAD:.4f})**2/0.25)"),
    ("lin_vel_z", -0.5, "(vz/1000)**2"),
    ("ang_vel_xy", -0.05, f"(wx/{RAD:.4f})**2+(wy/{RAD:.4f})**2"),
    # Playground's: the xy of the trunk's up vector in the world.
    ("orientation", -5.0, "(2*(qx*qz+qw*qy))**2+(2*(qy*qz-qw*qx))**2"),
]
parts = []
for leg in LEGS:
    for part in PARTS:
        j = f"{leg}_{part}_joint"
        n = f"q{short[j]}"
        lo, hi = 0.95 * lower[j] * RAD, 0.95 * upper[j] * RAD
        parts.append(f"(abs({n}-({lo:.3f}))-({n}-({lo:.3f}))+abs({n}-({hi:.3f}))+({n}-({hi:.3f})))")
terms.append(("dof_pos_limits", -1.0, f"({'+'.join(parts)})/{2 * RAD:.4f}"))
pose = "+".join(
    f"{(1.0 if part != 'calf' else 0.1) / RAD ** 2:.6g}*(q{short[f'{leg}_{part}_joint']}-({default[f'{leg}_{part}_joint'] * RAD:.3f}))**2"
    for leg in LEGS for part in PARTS)
terms.append(("pose", 0.5, f"exp(-({pose}))"))
terms.append(("feet_clearance", -2.0, "+".join(
    f"abs(p{leg}_z/1000-0.1)*sqrt(sqrt(u{leg}_x**2+u{leg}_y**2)/1000)" for leg in LEGS)))
# Playground's units: N*m, rad/s, raw action (target = home + 0.5*a, so the
# change of a per step is rate_deg_s * dt / (0.5 * RAD)).
taus = [f"tau{short[j]}/1000" for j in joints]
terms.append(("torques", -0.0002, "sqrt(" + "+".join(f"({t})**2" for t in taus) + ")+"
              + "+".join(f"abs({t})" for t in taus)))
terms.append(("energy", -0.001, "+".join(f"abs(d{short[j]}/{RAD:.4f})*abs(tau{short[j]}/1000)" for j in joints)))
terms.append(("action_rate", -0.01, "+".join(f"(c{short[j]}_rate*{DT / (0.5 * RAD):.6e})**2" for j in joints)))
terms.append(("feet_slip", -0.1, "+".join(f"((u{leg}_x/1000)**2+(u{leg}_y/1000)**2)*k{leg}_down" for leg in LEGS)))

reward = []
for label, weight, expression in terms:
    why = fits(expression)
    assert why is None, (label, why)
    reward.append({"expression": expression, "label": label, "weight": weight * DT})
assert len(reward) <= REWARD_TERMS_CAP, len(reward)

# -- domain randomisation: Playground's randomize.py, as scale draws --------
# One factor per entry, per environment, held for the run (Playground's
# randomization_fn is also drawn once per environment at wrap time).
floor = [i for i in range(check.ngeom) if check.geom(i).name == "floor"][0]
trunk = check.body("trunk").id
randomisation = [{"fields": [{"field": "geom_friction", "index": floor * 3}],
                  "low": 0.4 / float(check.geom_friction[floor][0]),
                  "high": 1.0 / float(check.geom_friction[floor][0]),
                  "label": "floor_friction", "mode": "scale", "subject": "floor",
                  "target": "friction"}]
for joint in joints:
    dof = int(check.jnt_dofadr[check.joint(joint).id])
    randomisation.append({"fields": [{"field": "dof_frictionloss", "index": dof}], "low": 0.9,
                          "high": 1.1, "label": f"frictionloss_{short[joint]}", "mode": "scale",
                          "subject": joint, "target": "frictionloss"})
for joint in joints:
    dof = int(check.jnt_dofadr[check.joint(joint).id])
    randomisation.append({"fields": [{"field": "dof_armature", "index": dof}], "low": 1.0,
                          "high": 1.05, "label": f"armature_{short[joint]}", "mode": "scale",
                          "subject": joint, "target": "armature"})
for body in range(1, check.nbody):
    if check.body_mass[body] <= 0.0:
        continue
    randomisation.append({"fields": [{"field": "body_mass", "index": body}], "low": 0.9,
                          "high": 1.1, "label": f"mass_{check.body(body).name}", "mode": "scale",
                          "subject": check.body(body).name, "target": "mass"})
# Playground adds U(-1, 1) kg to the trunk after the scale; a second scale of
# the trunk by 1 +/- 1 kg / its mass is the nearest a scale draw comes.
trunk_kg = float(check.body_mass[trunk])
randomisation.append({"fields": [{"field": "body_mass", "index": trunk}],
                      "low": 1.0 - 1.0 / trunk_kg, "high": 1.0 + 1.0 / trunk_kg,
                      "label": "trunk_payload", "mode": "scale", "subject": "trunk", "target": "mass"})

gaps = [
    {"item": "feet_air_time (reward 0.1)", "reason": "stateful: a per-foot timer since lift-off, paid on first contact; an expression reads one step's channels"},
    {"item": "feet_height (reward -0.2)", "reason": "stateful: the swing's peak height, paid on first contact"},
    {"item": "termination (reward -1)", "reason": "no done channel in an expression; the reward floor at 0 makes a fall cost the episode's remaining pay instead"},
    {"item": "stand_still (reward -1)", "reason": "pays only at a zero command; a goal draw is uniform(low, high), never zeroed with a probability"},
    {"item": "observation noise", "reason": "only tracker and load channels carry declared noise; Playground adds uniform noise to joint pos/vel, gyro, gravity and linvel"},
    {"item": "critic observations", "reason": "the critic reads every channel here (world pose/velocities, foot positions and velocities, contacts, torques); Playground's adds accelerometer, air time and perturbation force, and lacks foot positions"},
    {"item": "command sampling", "reason": "Playground resamples after Exp(5 s) and zeroes each axis with a probability; the bundle holds each draw 250 steps (5 s), 4 segments, never zeroed"},
    {"item": "reset", "reason": "reset_variation has tilt, height, spin and a horizontal speed; no xy offset or yaw (Playground: xy U(-0.5, 0.5), yaw U(-pi, pi), all six base velocities U(-0.5, 0.5))"},
    {"item": "trunk CoM jitter +U(-0.05, 0.05) m", "reason": "additive; a randomisation entry only scales"},
    {"item": "trunk mass +U(-1, 1) kg", "reason": "additive; written as a second scale by 1 +/- 1/m"},
    {"item": "qpos0 jitter U(-0.05, 0.05)", "reason": "additive; no dynamic effect without joint stiffness"},
    {"item": "joint pose observation", "reason": "absolute joint angles in degrees rather than offsets from home in radians: a fixed affine map the normaliser absorbs"},
]

goal_common = {"resample_steps": 250, "segments": 4}
goals = [
    {"channels": ["cx"], "high": 1500.0, "kind": "value", "label": "command_vx", "low": -1500.0,
     "name": "cx", "nominal": [1000.0], "unit": "mm/s", **goal_common},
    {"channels": ["cy"], "high": 800.0, "kind": "value", "label": "command_vy", "low": -800.0,
     "name": "cy", "nominal": [0.0], "unit": "mm/s", **goal_common},
    {"channels": ["cw"], "high": 1.2 * RAD, "kind": "value", "label": "command_wz", "low": -1.2 * RAD,
     "name": "cw", "nominal": [0.0], "unit": "deg/s", **goal_common},
]

engine_bundle = json.loads(ENGINE_BUNDLE.read_text())
episode = {"control_hz": 50, "control_interval_s": DT, "episode_seconds": 20.0, "max_steps": 1000,
           "reset_keyframe": "home", "reward_stage": "after_step", "solver_step_s": 0.004,
           "solver_steps_per_action": 5}
task = {
    "actions": actions, "commands": commands, "disturbance": [], "episode": episode,
    "functions": FUNCTIONS, "goal": goals, "goal_algorithm": engine_bundle["goal_algorithm"],
    "label": "go1_joystick",
    "model": {"bytes": len(xml), "mujoco_version": mujoco.__version__, "output": "go1",
              "path": "outputs/go1-model.xml", "sha256": hashlib.sha256(xml).hexdigest()},
    "mujoco_version": mujoco.__version__,
    "observations": [{k: v for k, v in r.items() if k != "role" or v == "privileged"} for r in observations],
    "randomisation": randomisation,
    "reset_variation": [{"angular_velocity_high_rad_s": 0.5, "angular_velocity_low_rad_s": -0.5,
                         "body": "trunk", "body_id": trunk, "clearance_mm": 0.0, "height_high_m": 0.0,
                         "height_low_m": 0.0, "label": "reset_variation", "linear_velocity_high_m_s": 0.5,
                         "linear_velocity_low_m_s": 0.0, "qpos_adr": 0, "qvel_adr": 0,
                         "tilt_high_rad": 0.0, "tilt_low_rad": 0.0}],
    "reward": reward, "schema": "cadex-training-task-v1",
    "termination": [{"above": None, "below": 0.0, "expression": "1-2*(qx**2+qy**2)", "label": "upside_down"}],
    "variation_algorithm": engine_bundle["variation_algorithm"],
}
out = ROOT / "outputs"
out.mkdir(parents=True, exist_ok=True)
(out / "go1-model.xml").write_bytes(xml)
(out / "go1_joystick-task.json").write_text(json.dumps(task, indent=1, sort_keys=True))
(out / "gaps.json").write_text(json.dumps(gaps, indent=1))

# -- fidelity: the bundle's model against Playground's, same controls -------
orig = playground_spec().compile()
a, b = mujoco.MjData(orig), mujoco.MjData(check)
mujoco.mj_resetDataKeyframe(orig, a, orig.key("home").id)
mujoco.mj_resetDataKeyframe(check, b, home.id)
drift, drifts = 0.0, {}
for step in range(500):
    ctrl = home.ctrl + 0.3 * math.sin(step * 0.05)
    a.ctrl[:] = ctrl
    b.ctrl[:] = ctrl
    mujoco.mj_step(orig, a)
    mujoco.mj_step(check, b)
    drift = max(drift, float(abs(a.qpos - b.qpos).max()))
    if step + 1 in (1, 10, 50, 100, 250, 500):
        drifts[step + 1] = drift
print(json.dumps({
    "mass_kg": [float(orig.body_subtreemass[1]), float(check.body_subtreemass[1])],
    "max_qpos_drift_by_step": drifts, "scalar_channels": scalar_channels,
    "policy_channels": sum(len(r["channels"]) for r in observations if r["role"] == "policy")
    + len(goals) + 2 * len(commands),
    "reward_terms": [t["label"] for t in reward], "randomisation_entries": len(randomisation),
    "model_sha256": task["model"]["sha256"]}, indent=1))
