# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""G2's go-to-point task written onto any floating-base robot (orun21 G3).

    ~/cadex-train-venv/bin/python training/cadex_joystick.py TASK.json --out DIR \\
        [--speeds VX,VY,WZ] [--label NAME]

``TASK.json`` is any ``cadex-training-task-v1`` bundle (an engine export's, or
``cadex_relay.py``'s re-laid onto a concept or a cut). Its model, its reset
keyframe and the engine's goal and variation algorithm strings are kept;
everything else is replaced by the task the Go1 passed G2 on
(``docs/probes/orun18/a2_bundle.py``, Playground's Go1 joystick, ADR-839/840),
stated generically:

- **goals** ``cx``, ``cy`` (mm/s) and ``cw`` (deg/s), uniform in
  ``±VX``, ``±VY``, ``±WZ`` (m/s, m/s, rad/s; the Go1's 1.5, 0.8, 1.2 by
  default), held 250 steps, four segments; ``cadex_train.py --goto`` drives
  them from ``cadex_goto``'s layer;
- **actor**: the root body's body-frame velocity, gyro and gravity, every
  driven joint's position and velocity, and the last command;
- **actions**: home + 0.5 rad, clipped to the joint's range, on every
  position drive;
- **reward**: Playground's terms and weights, times the control interval; the
  tracking widths, like the reset kick, scale with ``--speeds`` against the
  Go1's (squared for the widths);
- **randomisation**: floor friction 0.4–1.0, joint frictionloss and armature,
  every body's mass ±10 %, a ±1 kg payload on the root (at most ±20 % of its
  mass);
- **termination**: upside down.

What is the robot's own is read from its model: the root (the free joint's
body), the driven joints, their ranges and the keyframe pose, the feet
(bodies with colliding geoms and none below them, or ``--feet``), the floor.
The episode keeps the bundle's 50 Hz control and sets the substeps from the
model's own timestep, refusing one that does not divide it.

Writes ``DIR/outputs/<label>-task.json`` and ``DIR/outputs/<label>-model.xml``
(the model with this task's sensors in place of its own).

Needs ``mujoco`` (the training venv); the standard library at module scope
(ADR-084).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import sys
from pathlib import Path

RAD = 180.0 / math.pi
FUNCTIONS = ["abs", "arcsin", "arctan", "asin", "cos", "exp", "sin", "sqrt", "tanh"]
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
            ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UAdd, ast.USub)
#: cadex_assembly_api's formula bounds and CadexDynamics.MAXIMUM_REWARD_TERMS.
FORMULA_NODES, FORMULA_CHARACTERS, REWARD_TERMS = 512, 2048, 32
#: Playground's Go1 swing height for feet_clearance, m.
SWING_M = 0.1
#: Playground's ±1 kg payload on the trunk, capped at this share of the trunk's
#: own mass, so a small robot's trunk never draws a negative mass (the orun9
#: biped's pelvis is 0.26 kg). The Go1's 5.2 kg trunk and leon V's keep 1 kg.
PAYLOAD_KG, PAYLOAD_SHARE = 1.0, 0.2
#: The Go1's command bounds, m/s and rad/s, which Playground's tracking widths
#: (0.25) and reset kick (0.5 m/s, 0.5 rad/s) are set against. A robot given
#: slower ``--speeds`` has them scaled with its speeds, so a stand still costs
#: what it costs the Go1: at 0.25 the biped's 0.2 m/s command paid 0.85 for
#: standing, and its policy stood (orun21 G3, ADR-865).
GO1_SPEEDS = (1.5, 0.8, 1.2)
#: Written when the source bundle declares no goal (an engine task with a
#: fixed speed, such as the orun9 biped's walk): the trainer records it and
#: draws the value goals below by CadexDynamics.GOAL_ALGORITHM.
GOAL_ALGORITHM = ("CadexDynamics.GOAL_ALGORITHM: each value goal's segments drawn uniform(low, high) "
                  "from random.Random(seed) in bundle order, segment k from control step k * resample_steps")


def _fits(formula: str) -> bool:
    if len(formula) > FORMULA_CHARACTERS:
        return False
    nodes = list(ast.walk(ast.parse(formula, mode="eval")))
    return len(nodes) <= FORMULA_NODES and all(isinstance(n, _ALLOWED) for n in nodes)


def _terms(label: str, weight: float, parts: list[str], wrap: str = "{}") -> list[tuple[str, float, str]]:
    """One summed term, or several with the same weight when one would not fit."""

    for count in range(1, len(parts) + 1):
        size = -(-len(parts) // count)
        chunks = [parts[i:i + size] for i in range(0, len(parts), size)]
        formulas = [wrap.format("+".join(chunk)) for chunk in chunks]
        if all(_fits(f) for f in formulas):
            if len(formulas) == 1:
                return [(label, weight, formulas[0])]
            return [(f"{label}_{i + 1}", weight, f) for i, f in enumerate(formulas)]
    raise SystemExit(f"{label}: a single joint's part does not fit a reward formula")


def _name(text: str) -> str:
    return re.sub(r"\W", "_", text)


def write(task_path: Path, out: Path, speeds: tuple[float, float, float], label: str | None,
          feet_names: list[str] | None) -> dict:
    import mujoco

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cadex_train

    source = json.loads(task_path.read_text(encoding="utf-8"))
    xml = cadex_train._bundle_model_bytes(task_path.resolve(), source)
    if xml is None:
        raise SystemExit(f"the model {source['model']['path']!r} is not beside {task_path}")
    spec = mujoco.MjSpec.from_string(xml.decode("utf-8"))
    for sensor in list(spec.sensors):
        spec.delete(sensor)
    for site in list(spec.sites):
        if site.name.startswith("obs/"):
            spec.delete(site)
    plain = spec.compile()
    episode = dict(source["episode"])
    keyname = str(episode["reset_keyframe"])
    if not any(plain.key(i).name == keyname for i in range(plain.nkey)):
        raise SystemExit(f"the model has no keyframe {keyname!r}")
    home = plain.key(keyname)
    free = [j for j in range(plain.njnt) if int(plain.jnt_type[j]) == mujoco.mjtJoint.mjJNT_FREE]
    if not free:
        raise SystemExit("go-to-point needs a floating base; this model has no free joint")
    root = plain.body(int(plain.jnt_bodyid[free[0]])).name
    dt = float(episode["control_interval_s"])
    per = dt / float(plain.opt.timestep)
    if abs(per - round(per)) > 1e-6:
        raise SystemExit(f"the control interval {dt} s is not a whole number of {plain.opt.timestep} s steps")
    episode.update(solver_step_s=float(plain.opt.timestep), solver_steps_per_action=int(round(per)),
                   episode_seconds=20.0, max_steps=int(round(20.0 / dt)))

    drives = []
    for a in range(plain.nu):
        joint = int(plain.actuator_trnid[a][0])
        if (int(plain.actuator_trntype[a]) != mujoco.mjtTrn.mjTRN_JOINT
                or int(plain.jnt_type[joint]) not in (mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE)
                or float(plain.actuator_biasprm[a][1]) >= 0.0):
            raise SystemExit(f"drive {plain.actuator(a).name!r} is not a position servo on a hinge or slide")
        drives.append((a, plain.joint(joint).name))
    joints = [j for _, j in drives]
    short = {j: _name(j) for j in joints}

    colliding = [g for g in range(plain.ngeom) if plain.geom_contype[g] or plain.geom_conaffinity[g]]
    floors = [g for g in colliding if int(plain.geom_bodyid[g]) == 0 and int(plain.geom_type[g]) == mujoco.mjtGeom.mjGEOM_PLANE]
    if len(floors) != 1:
        raise SystemExit(f"want one floor plane on the world body, found {len(floors)}")
    if feet_names:
        feet = list(feet_names)
    else:
        bodies = {int(plain.geom_bodyid[g]) for g in colliding} - {0}
        below = lambda b: [c for c in range(plain.nbody) if c != b and _under(plain, c, b)]  # noqa: E731
        feet = [plain.body(b).name for b in sorted(bodies) if not any(c in bodies for c in below(b))]
    if len(feet) < 1:
        raise SystemExit("found no feet: give --feet")

    observations = []
    S, J, X, SITE = mujoco.mjtSensor, mujoco.mjtObj.mjOBJ_JOINT, mujoco.mjtObj.mjOBJ_XBODY, mujoco.mjtObj.mjOBJ_SITE

    def add(name, channels, kind, target, stype, objtype, scale, unit, role="policy", objname=None):
        index = len(observations)
        sensor = spec.add_sensor(name=f"obs/{index}", type=stype, objtype=objtype, objname=objname or target)
        observations.append(dict(name=name, channels=channels, kind=kind, target=target,
                                 scale=scale, unit=unit, role=role, sensor=f"obs/{index}"))
        return sensor

    spec.body(root).add_site(name="obs/imu", pos=[0, 0, 0])
    add("bv", ["bvx", "bvy", "bvz"], "body_linear_velocity", root, S.mjSENS_VELOCIMETER, SITE, 1000.0, "mm/s", objname="obs/imu")
    add("bw", ["bwx", "bwy", "bwz"], "body_angular_velocity", root, S.mjSENS_GYRO, SITE, RAD, "deg/s", objname="obs/imu")
    g = add("g", ["gx", "gy", "gz"], "gravity_in_body", "world", S.mjSENS_FRAMEZAXIS, X, 1.0, "1")
    g.reftype, g.refname = X, root
    for j in joints:
        add(f"q_{short[j]}", [f"q_{short[j]}"], "position", j, S.mjSENS_JOINTPOS, J, RAD, "deg")
    for j in joints:
        add(f"dq_{short[j]}", [f"dq_{short[j]}"], "velocity", j, S.mjSENS_JOINTVEL, J, RAD, "deg/s")
    add("q", ["qw", "qx", "qy", "qz"], "component_orientation", root, S.mjSENS_FRAMEQUAT, X, 1.0, "quat", role="privileged")
    add("w", ["wx", "wy", "wz"], "component_angular_velocity", root, S.mjSENS_FRAMEANGVEL, X, RAD, "deg/s", role="privileged")
    add("v", ["vx", "vy", "vz"], "component_linear_velocity", root, S.mjSENS_FRAMELINVEL, X, 1000.0, "mm/s", role="privileged")
    for a, j in drives:
        add(f"tau_{short[j]}", [f"tau_{short[j]}"], "actuator_force", plain.actuator(a).name,
            S.mjSENS_ACTUATORFRC, mujoco.mjtObj.mjOBJ_ACTUATOR, 1000.0, "nmm", role="privileged")
    foot_short = {}
    for k, foot in enumerate(feet):
        body = plain.body(foot).id
        shapes = [g for g in colliding if int(plain.geom_bodyid[g]) == body]
        if not shapes:
            raise SystemExit(f"foot {foot!r} has no colliding geom")
        lo = [min(plain.geom_pos[g][i] - plain.geom_rbound[g] for g in shapes) for i in range(3)]
        hi = [max(plain.geom_pos[g][i] + plain.geom_rbound[g] for g in shapes) for i in range(3)]
        centre = [(a + b) / 2 for a, b in zip(lo, hi)]
        f = foot_short[foot] = f"f{k}"
        spec.body(foot).add_site(name=f"obs/{f}", pos=centre)
        add(f"p{f}", [f"p{f}_x", f"p{f}_y", f"p{f}_z"], "component_position", foot,
            S.mjSENS_FRAMEPOS, SITE, 1000.0, "mm", role="privileged", objname=f"obs/{f}")
        add(f"u{f}", [f"u{f}_x", f"u{f}_y", f"u{f}_z"], "component_linear_velocity", foot,
            S.mjSENS_FRAMELINVEL, SITE, 1000.0, "mm/s", role="privileged", objname=f"obs/{f}")
        index = len(observations)
        spec.body(foot).add_site(name=f"obs/{index}/contact", type=mujoco.mjtGeom.mjGEOM_BOX, pos=centre,
                                 size=[(b - a) / 2 for a, b in zip(lo, hi)], rgba=[0, 0, 0, 0])
        add(f"k{f}", [f"k{f}", f"k{f}_down"], "contact", foot, S.mjSENS_TOUCH, SITE, 1.0, "n",
            role="privileged", objname=f"obs/{index}/contact")
        observations[-1]["contact"] = {"body": foot, "down_above_n": 0.0}

    text = spec.to_xml().encode("utf-8")
    check = mujoco.MjModel.from_xml_string(text.decode("utf-8"))
    for row in observations:
        sid = mujoco.mj_name2id(check, mujoco.mjtObj.mjOBJ_SENSOR, row["sensor"])
        row["adr"], row["dim"] = int(check.sensor_adr[sid]), int(check.sensor_dim[sid])

    qadr = {j: int(plain.jnt_qposadr[plain.joint(j).id]) for j in joints}
    default = {j: float(home.qpos[qadr[j]]) for j in joints}
    lower = {j: float(plain.jnt_range[plain.joint(j).id][0]) for j in joints}
    upper = {j: float(plain.jnt_range[plain.joint(j).id][1]) for j in joints}
    for j in joints:
        if not plain.jnt_limited[plain.joint(j).id]:
            raise SystemExit(f"joint {j!r} has no range")
    actions = [{"actuator": plain.actuator(a).name, "fallback": "0",
                "high": round(min(default[j] + 0.5, upper[j]) * RAD, 6), "index": int(a), "joint": j,
                "kind": "position", "low": round(max(default[j] - 0.5, lower[j]) * RAD, 6),
                "motion_type": "angular", "scale": math.pi / 180.0, "source": "home_plus_0.5_rad",
                "unit": "deg"} for a, j in drives]
    commands = [{"name": f"c_{short[a['joint']]}", "kind": "command", "target": a["joint"],
                 "actuator": a["actuator"], "action": i,
                 "channels": [f"c_{short[a['joint']]}", f"c_{short[a['joint']]}_rate"],
                 "unit": "deg", "rate_unit": "deg/s"} for i, a in enumerate(actions)]

    linear, angular = speeds[0] / GO1_SPEEDS[0], speeds[2] / GO1_SPEEDS[2]
    terms = [
        ("tracking_lin_vel", 1.0, f"exp(-(((cx-bvx)/1000)**2+((cy-bvy)/1000)**2)/{0.25 * linear ** 2:g})"),
        ("tracking_ang_vel", 0.5, f"exp(-((cw-bwz)/{RAD:.4f})**2/{0.25 * angular ** 2:g})"),
        ("lin_vel_z", -0.5, "(vz/1000)**2"),
        ("ang_vel_xy", -0.05, f"(wx/{RAD:.4f})**2+(wy/{RAD:.4f})**2"),
        ("orientation", -5.0, "(2*(qx*qz+qw*qy))**2+(2*(qy*qz-qw*qx))**2"),
    ]
    limits = []
    for j in joints:
        n, lo, hi = f"q_{short[j]}", 0.95 * lower[j] * RAD, 0.95 * upper[j] * RAD
        limits.append(f"(abs({n}-({lo:.3f}))-({n}-({lo:.3f}))+abs({n}-({hi:.3f}))+({n}-({hi:.3f})))")
    terms += _terms("dof_pos_limits", -1.0, limits, "({})/" + f"{2 * RAD:.4f}")
    # Playground's pose weights: 1 on every joint but the last of each leg
    # (the Go1's calf, 0.1): here the nearest driven joint at or above a foot.
    driven = {int(plain.jnt_bodyid[plain.joint(j).id]): j for j in joints}
    last = set()
    for foot in feet:
        body = plain.body(foot).id
        while body > 0 and body not in driven:
            body = int(plain.body_parentid[body])
        if body > 0:
            last.add(driven[body])
    pose_weight = {j: 0.1 if j in last else 1.0 for j in joints}
    pose = [f"{pose_weight[j] / RAD ** 2:.6g}*(q_{short[j]}-({default[j] * RAD:.3f}))**2" for j in joints]
    formula = f"exp(-({'+'.join(pose)}))"
    if not _fits(formula):
        raise SystemExit("pose: the joints' pose term does not fit a reward formula")
    terms.append(("pose", 0.5, formula))
    terms += _terms("feet_clearance", -2.0, [
        f"abs(p{f}_z/1000-{SWING_M})*sqrt(sqrt(u{f}_x**2+u{f}_y**2)/1000)" for f in foot_short.values()])
    taus = [f"tau_{short[j]}/1000" for j in joints]
    formula = "sqrt(" + "+".join(f"({t})**2" for t in taus) + ")+" + "+".join(f"abs({t})" for t in taus)
    if not _fits(formula):
        raise SystemExit("torques: the drives' torque term does not fit a reward formula")
    terms.append(("torques", -0.0002, formula))
    terms += _terms("energy", -0.001, [f"abs(dq_{short[j]}/{RAD:.4f})*abs(tau_{short[j]}/1000)" for j in joints])
    terms += _terms("action_rate", -0.01, [f"(c_{short[j]}_rate*{dt / (0.5 * RAD):.6e})**2" for j in joints])
    terms += _terms("feet_slip", -0.1, [f"((u{f}_x/1000)**2+(u{f}_y/1000)**2)*k{f}_down" for f in foot_short.values()])
    if len(terms) > REWARD_TERMS:
        raise SystemExit(f"{len(terms)} reward terms > {REWARD_TERMS}")
    reward = [{"expression": e, "label": n, "weight": w * dt} for n, w, e in terms]

    floor = floors[0]
    trunk = check.body(root).id
    randomisation = [{"fields": [{"field": "geom_friction", "index": floor * 3}],
                      "low": 0.4 / float(check.geom_friction[floor][0]), "high": 1.0 / float(check.geom_friction[floor][0]),
                      "label": "floor_friction", "mode": "scale", "subject": check.geom(floor).name, "target": "friction"}]
    for field, target, lo, hi in (("dof_frictionloss", "frictionloss", 0.9, 1.1), ("dof_armature", "armature", 1.0, 1.05)):
        for j in joints:
            dof = int(check.jnt_dofadr[check.joint(j).id])
            randomisation.append({"fields": [{"field": field, "index": dof}], "low": lo, "high": hi,
                                  "label": f"{target}_{short[j]}", "mode": "scale", "subject": j, "target": target})
    for body in range(1, check.nbody):
        if check.body_mass[body] > 0.0:
            randomisation.append({"fields": [{"field": "body_mass", "index": body}], "low": 0.9, "high": 1.1,
                                  "label": f"mass_{_name(check.body(body).name)}", "mode": "scale",
                                  "subject": check.body(body).name, "target": "mass"})
    trunk_kg = float(check.body_mass[trunk])
    payload = min(PAYLOAD_KG, PAYLOAD_SHARE * trunk_kg) / trunk_kg
    randomisation.append({"fields": [{"field": "body_mass", "index": trunk}], "low": 1.0 - payload,
                          "high": 1.0 + payload, "label": "trunk_payload", "mode": "scale",
                          "subject": root, "target": "mass"})

    vx, vy, wz = speeds
    common = {"resample_steps": 250, "segments": 4}
    goals = [
        {"channels": ["cx"], "high": 1000.0 * vx, "kind": "value", "label": "command_vx", "low": -1000.0 * vx,
         "name": "cx", "nominal": [round(1000.0 * vx * 2 / 3, 3)], "unit": "mm/s", **common},
        {"channels": ["cy"], "high": 1000.0 * vy, "kind": "value", "label": "command_vy", "low": -1000.0 * vy,
         "name": "cy", "nominal": [0.0], "unit": "mm/s", **common},
        {"channels": ["cw"], "high": wz * RAD, "kind": "value", "label": "command_wz", "low": -wz * RAD,
         "name": "cw", "nominal": [0.0], "unit": "deg/s", **common},
    ]
    label = label or f"{source['label']}_joystick"
    name = _name(label)
    task = {
        "actions": actions, "commands": commands, "disturbance": [], "episode": episode,
        "functions": FUNCTIONS, "goal": goals, "goal_algorithm": source.get("goal_algorithm") or GOAL_ALGORITHM, "label": label,
        "model": {"bytes": len(text), "mujoco_version": mujoco.__version__, "output": name,
                  "path": f"outputs/{name}-model.xml", "sha256": hashlib.sha256(text).hexdigest()},
        "mujoco_version": mujoco.__version__,
        "observations": [{k: v for k, v in r.items() if k != "role" or v == "privileged"} for r in observations],
        "randomisation": randomisation,
        "reset_variation": [{"angular_velocity_high_rad_s": 0.5 * angular, "angular_velocity_low_rad_s": -0.5 * angular,
                             "body": root, "body_id": trunk, "clearance_mm": 0.0, "height_high_m": 0.0,
                             "height_low_m": 0.0, "label": "reset_variation", "linear_velocity_high_m_s": 0.5 * linear,
                             "linear_velocity_low_m_s": 0.0, "qpos_adr": int(check.jnt_qposadr[free[0]]),
                             "qvel_adr": int(check.jnt_dofadr[free[0]]), "tilt_high_rad": 0.0, "tilt_low_rad": 0.0}],
        "reward": reward, "schema": "cadex-training-task-v1",
        "termination": [{"above": None, "below": 0.0, "expression": "1-2*(qx**2+qy**2)", "label": "upside_down"}],
        "variation_algorithm": source["variation_algorithm"],
    }
    outputs = out / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / f"{name}-model.xml").write_bytes(text)
    (outputs / f"{name}-task.json").write_text(json.dumps(task, indent=1, sort_keys=True), encoding="utf-8")
    return {"task": str(outputs / f"{name}-task.json"), "root": root, "feet": feet, "joints": joints,
            "mass_kg": round(float(check.body_subtreemass[trunk]), 3), "episode": episode,
            "reward_terms": [r["label"] for r in reward], "randomisation_entries": len(randomisation),
            "actor_channels": sum(len(r["channels"]) for r in observations if r["role"] == "policy")
            + len(goals) + 2 * len(commands)}


def _under(model, child: int, ancestor: int) -> bool:
    while child > 0:
        child = int(model.body_parentid[child])
        if child == ancestor:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("task", type=Path, help="a cadex-training-task-v1 bundle: its model and keyframe are kept")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--speeds", default="1.5,0.8,1.2", help="VX,VY,WZ: the goals' bounds, m/s, m/s, rad/s")
    ap.add_argument("--label", default=None)
    ap.add_argument("--feet", default=None, help="the feet's body names, comma-separated (default: found)")
    a = ap.parse_args(argv)
    speeds = tuple(float(v) for v in a.speeds.split(","))
    if len(speeds) != 3 or min(speeds) <= 0.0:
        raise SystemExit("--speeds is three positive numbers: VX,VY,WZ")
    report = write(a.task, a.out, speeds, a.label, a.feet.split(",") if a.feet else None)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
