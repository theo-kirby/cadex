# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The training model: a fast MJCF cut from a CAD export, and the check that it is faithful.

The engine's MJCF export is the judge. Training on it is slow (contacts on every
collision shape, a body per part, the engine's solver), so this cuts a copy for
training only, the way Playground's Go1 model is cut, changed in four ways and
no others:

* **Floor contact on the feet and the fall geoms only.** The feet are the
  collision geoms of the bodies that hold a ``touch`` sensor's site (the export
  writes one per foot). The fall geoms, by default, are the collision geoms
  that sit, once static bodies are merged, on the root or on a body carrying
  more than one foot (the trunk, the spine, the head on the trunk): what a fall
  lands on. They get ``condim`` 1 (``--fall-condim``) and ``priority`` 1 so
  their condim, not the floor's, is the contact's. Every other collision geom
  (knee drums, shins, forearms) is switched off.
* **No self-collision.** Robot geoms get ``contype`` 0 and the floor
  ``conaffinity`` 0, so only floor pairs exist; the ``<contact>`` excludes are
  dead and go.
* **Static parts merged into their bodies.** A joint-free body no sensor,
  equality or tendon names is fused into its parent by the parallel-axis sum.
  A body holding a foot or a named fall geom is kept (ADR-951): MuJoCo softens
  a contact by its bodies' ``invweight0``, so a paw fused into its forearm
  presses about three times stiffer, and leon VI's cut drifted 5.65 mm from
  its export with the export's own solver.
  MuJoCo's ``fusestatic`` is not used: it stops wherever a sensor names a
  subtree. A Cadex export writes every body frame as the world frame, which is
  what makes moving elements up exact; a static body with its own frame is
  refused.
* **A cheap solver.** 2 ms, Euler without Euler damping, ``--iterations`` 2,
  ``--ls-iterations`` 3: the fastest setting that passed the fidelity check on
  leon V. Euler integrates joint damping explicitly, so a stiff servo on a light
  link (the biped's) blows up under it; ``cut`` then falls back to
  ``implicitfast`` at the same step and iterations (``LADDER``). Naming any
  solver option tries that one setting only.

* **A held, cable-coupled chain welded, if asked** (``--weld``, ADR-959).
  Each named joint (``fnmatch`` patterns) goes, and so does every joint
  equality that names one, so the chain is rigid at its build pose and its
  bodies fuse. A welded joint must be unactuated, coupled by a joint
  equality, named by no sensor or tendon, and at ``qpos0`` in every
  keyframe; otherwise the cut is refused. Its use is a chain whose driving
  joints are held, not the policy's (leon VI's tail): the export's judge
  still plays the full chain.

Masses, inertias, joints, actuators, equalities, sensors and keyframes are kept,
less only what ``--weld`` names.
``cut`` compiles both models and refuses to write unless total mass,
nq/nv/nu/neq, the actuated joint order, the sensor count and the joint-space
mass matrix at qpos0 (to 1e-9) match (with ``--weld``: less the welded
joints' coordinates and the equalities dropped, the matrix compared on the
kept DoFs), and unless the cut passes ``fidelity``
(``--no-check`` skips that). The model is marked
``cadex:tier = training`` so the dashboard and ``cadex_train.py`` know it.

``fidelity`` drives the engine export and each training model on the CPU with
the same open-loop sinusoids (every actuator ``A sin(2 pi f t + 2 pi i / nu)``
about home, held per 20 ms control step, 2 s, f in 1-3 Hz by A in
0.025-0.1 rad) and compares the root's position. Where the engine disagrees
with itself at half its timestep by more than ``--converged`` (1 mm) the motion
is chaotic and the signal is reported but not gated. A model passes when every
gated signal stays within ``--tolerance`` (5 mm), and when it stands for 10 s
from keyframe 0 at zero action: finite, tilt under 5 deg, only the feet on the
floor, carrying the weight within 2%. The feet are the bodies holding a touch
sensor's site, or those holding the ``--feet`` geoms when given.

    python training/cadex_training_model.py cut --project DIR --out MODEL.xml [--json REPORT]
        [--engine MJCF] [--timestep S] [--iterations N] [--ls-iterations N]
        [--integrator Euler|implicitfast] [--feet G,...] [--fall-geoms G,...] [--fall-condim 1]
        [--weld 'j_tail[3-7]_*',...]
    python training/cadex_training_model.py fidelity MODEL.xml [...] --project DIR [--json OUT] [--feet G,...]

``--project`` reads the accepted attempt's MJCF export; ``--engine`` names one.
Each prints one JSON report and exits 0 only on a pass. Needs ``mujoco`` and
``numpy`` (the training venv); the standard library at module scope (ADR-084).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

FLOOR = "environment/floor"
DEFAULTS = {"timestep": 0.002, "iterations": 2, "ls_iterations": 3, "integrator": "Euler"}
#: The settings ``cut`` tries, fastest first; it keeps the first that passes.
LADDER = (DEFAULTS, {**DEFAULTS, "integrator": "implicitfast"})
CONTROL_DT = 0.02
SECONDS = 2.0
FREQUENCIES_HZ = (1.0, 2.0, 3.0)
AMPLITUDES_RAD = (0.025, 0.05, 0.075, 0.1)
TOLERANCE_M = 0.005
CONVERGED_M = 0.001
STAND_SECONDS = 10.0
MAX_TILT_DEG = 5.0
LOAD_TOLERANCE = 0.02


def project_export(project: Path) -> Path:
    """The accepted attempt's MJCF export in a Cadex project."""

    staging = json.loads((project / "script.json").read_text())["accepted_attempt"]["staging"]
    found = sorted((project / staging / "outputs").glob("*model.xml"))
    if len(found) != 1:
        raise SystemExit(f"{project}: expected one MJCF export in {staging}/outputs, found {len(found)}")
    return found[0]


def _touch_sites(root) -> set[str]:
    return {el.get("site") for section in root.findall("sensor") for el in section
            if el.tag == "touch" and el.get("site")}


def _foot_bodies(root) -> list:
    sites = _touch_sites(root)
    return [b for b in root.iter("body") if any(s.get("name") in sites for s in b.findall("site"))]


def colliding_geoms(xml: str) -> set[str]:
    """The geoms that take part in any contact, as MuJoCo compiles them (defaults applied)."""

    import mujoco as mj

    m = mj.MjModel.from_xml_string(xml)
    return {mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g) for g in range(m.ngeom)
            if m.geom_contype[g] or m.geom_conaffinity[g]} - {None}


def _inertia(el):
    import numpy as np

    mass = float(el.get("mass"))
    pos = np.array([float(v) for v in el.get("pos", "0 0 0").split()])
    quat = np.array([float(v) for v in el.get("quat", "1 0 0 0").split()])
    w, x, y, z = quat / np.linalg.norm(quat)
    rot = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                    [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                    [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    diag = np.array([float(v) for v in el.get("diaginertia").split()])
    return mass, pos, rot @ np.diag(diag) @ rot.T


def merged_inertial(inertials) -> dict[str, str]:
    """One ``<inertial>``'s attributes for several, by the parallel-axis theorem."""

    import numpy as np

    parts = [_inertia(el) for el in inertials]
    mass = sum(m for m, _, _ in parts)
    com = sum(m * p for m, p, _ in parts) / mass
    tensor = sum(i + m * (np.dot(p - com, p - com) * np.eye(3) - np.outer(p - com, p - com))
                 for m, p, i in parts)
    diag, rot = np.linalg.eigh((tensor + tensor.T) / 2)
    if np.linalg.det(rot) < 0:
        rot[:, 0] = -rot[:, 0]
    w = np.sqrt(max(0.0, 1 + np.trace(rot))) / 2
    if w > 1e-6:
        quat = np.array([w, (rot[2, 1] - rot[1, 2]) / (4 * w), (rot[0, 2] - rot[2, 0]) / (4 * w),
                         (rot[1, 0] - rot[0, 1]) / (4 * w)])
    else:  # a half turn: the axis from the largest diagonal
        k = int(np.argmax(np.diag(rot)))
        axis = np.zeros(3)
        axis[k] = np.sqrt(max(0.0, (1 + rot[k, k]) / 2))
        for j in range(3):
            if j != k:
                axis[j] = (rot[k, j] + rot[j, k]) / (4 * axis[k])
        quat = np.array([0.0, *axis])
    fmt = lambda v: " ".join(f"{x:.9g}" for x in v)  # noqa: E731
    return {"pos": fmt(com), "quat": fmt(quat / np.linalg.norm(quat)), "mass": f"{mass:.9g}",
            "diaginertia": fmt(np.maximum(diag, 0.0))}


def _framed(body) -> bool:
    """Whether a body has a frame of its own: one that is not the identity (``pos="0 0 0"`` is not)."""

    identity = {"pos": [0.0] * 3, "quat": [1.0, 0.0, 0.0, 0.0], "euler": [0.0] * 3}
    for key in ("pos", "quat", "euler", "axisangle", "xyaxes", "zaxis"):
        text = body.get(key)
        if text is not None and [float(v) for v in text.split()] != identity.get(key):
            return True
    return False


def fuse_static(root, keep: Iterable[str] = ()) -> int:
    """Fuse every joint-free body nothing names, and not in ``keep``, into its parent; return how many."""

    named = set(keep)
    for section in [*root.findall("sensor"), *root.findall("equality"), *root.findall("tendon")]:
        for el in section.iter():
            for key in ("objname", "body", "refname", "body1", "body2"):
                if el.get(key):
                    named.add(el.get(key))
    fused = 0

    def visit(body):
        nonlocal fused
        for child in [c for c in body if c.tag == "body"]:
            visit(child)
            static = child.find("joint") is None and child.find("freejoint") is None
            if not static or child.get("name") in named or body.tag == "worldbody":
                continue
            if _framed(child):
                raise ValueError(f"static body {child.get('name')} has its own frame; fusion needs world-frame bodies")
            index = list(body).index(child)
            inertials = [el for el in (body.find("inertial"), child.find("inertial")) if el is not None]
            body.remove(child)
            if len(inertials) == 2:
                for key, value in merged_inertial(inertials).items():
                    inertials[0].set(key, value)
            elif inertials and inertials[0] is child.find("inertial"):
                body.insert(0, inertials[0])
                index += 1
            for el in [c for c in child if c.tag != "inertial"]:
                body.insert(index, el)
                index += 1
            fused += 1

    visit(root.find("worldbody"))
    return fused


def _bodies_holding(root, geoms: Iterable[str]) -> set[str]:
    names = set(geoms)
    return {str(b.get("name")) for b in root.iter("body") if any(g.get("name") in names for g in b.findall("geom"))}


def default_fall_geoms(root, colliding: set[str], feet: set[str]) -> list[str]:
    """Colliding non-foot geoms on the root or on a body carrying more than one foot (``root`` fused)."""

    sites = _touch_sites(root)
    out = []

    def visit(body, top: bool) -> int:
        here = sum(1 for s in body.findall("site") if s.get("name") in sites)
        below = sum(visit(c, False) for c in body.findall("body"))
        if top or here + below > 1:
            out.extend(g.get("name") for g in body.findall("geom")
                       if g.get("name") in colliding and g.get("name") not in feet)
        return here + below

    for body in root.find("worldbody").findall("body"):
        visit(body, True)
    return out


def weld_chain(xml: str, root, patterns: Iterable[str]) -> dict[str, Any]:
    """Remove the joints ``patterns`` match, and every joint equality naming one, from ``root``.

    ``xml`` is ``root``'s text, compiled to read the keyframes. Returns the
    welded joints, the engine DoF and qpos indices they held, and the
    equalities dropped. Refuses a joint that is actuated, coupled by no joint
    equality, named by a sensor or tendon, or off ``qpos0`` in a keyframe.
    """

    import mujoco as mj
    import numpy as np

    joints = {j.get("name"): j for b in root.iter("body") for j in b.findall("joint") if j.get("name")}
    chosen: list[str] = []
    for pattern in patterns:
        hits = [n for n in joints if fnmatch.fnmatchcase(n, pattern)]
        if not hits:
            raise ValueError(f"--weld {pattern!r} matches no joint")
        chosen += [n for n in hits if n not in chosen]

    def naming(sections, keys=("joint", "joint1", "joint2", "objname", "jointinparent")) -> set[str]:
        return {el.get(k) for sec in sections for el in sec.iter() for k in keys if el.get(k)}

    actuated = naming(root.findall("actuator"))
    sensed = naming(root.findall("sensor"))
    tendons = naming(root.findall("tendon"))
    equalities = [(sec, el) for sec in root.findall("equality") for el in sec.findall("joint")]
    coupled = {el.get(k) for _, el in equalities for k in ("joint1", "joint2") if el.get(k)}
    m = mj.MjModel.from_xml_string(xml)
    for name in chosen:
        j = joints[name]
        why = ("it is actuated" if name in actuated else
               "a sensor names it" if name in sensed else
               "a tendon names it" if name in tendons else
               "no joint equality couples it" if name not in coupled else
               "it is not a hinge or slide" if j.get("type", "hinge") not in ("hinge", "slide") else None)
        if why:
            raise ValueError(f"cannot weld {name}: {why}")
        adr = int(m.jnt_qposadr[mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, name)])
        for k in range(m.nkey):
            if abs(float(m.key_qpos[k, adr]) - float(m.qpos0[adr])) > 1e-9:
                raise ValueError(f"cannot weld {name}: keyframe {k} holds it at {m.key_qpos[k, adr]:.6g}, "
                                 f"not its build pose {m.qpos0[adr]:.6g}")
    ids = [mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, n) for n in chosen]
    qpos = sorted(int(m.jnt_qposadr[i]) for i in ids)
    dofs = sorted(int(m.jnt_dofadr[i]) for i in ids)

    for key in root.iter("key"):
        for attr, drop in (("qpos", set(qpos)), ("qvel", set(dofs))):
            if key.get(attr):
                values = key.get(attr).split()
                key.set(attr, " ".join(v for i, v in enumerate(values) if i not in drop))
    dropped = []
    for sec, el in equalities:
        if el.get("joint1") in chosen or el.get("joint2") in chosen:
            sec.remove(el)
            dropped.append(el.get("name") or f"{el.get('joint1')}~{el.get('joint2')}")
    for sec in [s for s in root.findall("equality") if len(s) == 0]:
        root.remove(sec)
    for body in root.iter("body"):
        for j in [j for j in body.findall("joint") if j.get("name") in chosen]:
            body.remove(j)
    return {"joints": chosen, "dofs": dofs, "qpos": qpos, "equalities": dropped}


def derive(xml: str, *, timestep: float, iterations: int, ls_iterations: int, integrator: str,
           feet: Iterable[str] | None = None, fall_geoms: Iterable[str] | None = None,
           fall_condim: int = 1, weld: Iterable[str] | None = None) -> tuple[str, dict[str, Any]]:
    """The training MJCF text for an engine MJCF text, and the feet and fall geoms it kept (and what it welded)."""

    colliding = colliding_geoms(xml)
    root = ET.fromstring(xml)
    names = {g.get("name") for g in root.iter("geom")}
    if feet is None:
        feet = [g.get("name") for b in _foot_bodies(root) for g in b.findall("geom")
                if g.get("name") in colliding]
        if not feet:
            raise ValueError("no foot found: no colliding geom on a body holding a touch sensor's site")
    feet = list(feet)
    missing = [n for n in (FLOOR, *feet, *(fall_geoms or ())) if n not in names]
    if missing:
        raise ValueError(f"the MJCF has no geom {missing}")

    for contact in root.findall("contact"):
        root.remove(contact)
    welded = weld_chain(xml, root, weld) if weld else None
    floor_geoms = {*feet, *(fall_geoms or ())}
    fuse_static(root, keep=_bodies_holding(root, floor_geoms))
    fall = list(fall_geoms) if fall_geoms is not None else default_fall_geoms(root, colliding, set(feet))

    option = root.find("option")
    if option is None:
        option = ET.Element("option")
        root.insert(1, option)
    option.set("timestep", repr(timestep))
    option.set("iterations", str(iterations))
    option.set("ls_iterations", str(ls_iterations))
    option.set("integrator", integrator)
    if integrator == "Euler":
        flag = option.find("flag")
        if flag is None:
            flag = ET.SubElement(option, "flag")
        flag.set("eulerdamp", "disable")

    for geom in root.iter("geom"):
        name = geom.get("name")
        if name == FLOOR:
            geom.set("contype", "1")
            geom.set("conaffinity", "0")
        elif name in feet or name in fall:
            geom.set("contype", "0")
            geom.set("conaffinity", "1")
            if name in fall:
                geom.set("condim", str(fall_condim))
                # A contact takes the larger condim of its two geoms unless one has
                # the higher priority, so without this the floor's 3 wins.
                geom.set("priority", "1")
        else:
            geom.set("contype", "0")
            geom.set("conaffinity", "0")

    custom = root.find("custom")
    if custom is None:
        custom = ET.SubElement(root, "custom")
    for text in [t for t in custom.findall("text") if t.get("name") == "cadex:tier"]:
        custom.remove(text)
    ET.SubElement(custom, "text", name="cadex:tier", data="training")

    ET.indent(root, space="  ")
    kept: dict[str, Any] = {"feet": feet, "fall_geoms": fall}
    if welded:
        kept["welded"] = welded
    return ET.tostring(root, encoding="unicode") + "\n", kept


def compiled(xml: str) -> dict[str, Any]:
    """What a compiled model holds, for comparing the two."""

    import mujoco as mj
    import numpy as np

    m = mj.MjModel.from_xml_string(xml)
    floor = mj.mj_name2id(m, mj.mjtObj.mjOBJ_GEOM, FLOOR)
    colliding = [mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g) for g in range(m.ngeom)
                 if g != floor and (m.geom_contype[g] or m.geom_conaffinity[g])]
    d = mj.MjData(m)
    mj.mj_forward(m, d)
    full = np.zeros((m.nv, m.nv))
    mj.mj_fullM(m, d, full)
    return {
        "mass_matrix": full.tolist(),
        "nbody": int(m.nbody), "nq": int(m.nq), "nv": int(m.nv), "nu": int(m.nu), "neq": int(m.neq),
        "nsensor": int(m.nsensor), "ngeom_colliding": len(colliding), "colliding": colliding,
        "mass_kg": round(float(m.body_mass.sum()), 6),
        "actuated_joints": [mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, int(j)) for j in m.actuator_trnid[:, 0]],
        "timestep": float(m.opt.timestep), "iterations": int(m.opt.iterations),
        "ls_iterations": int(m.opt.ls_iterations),
    }


def compare(engine: dict, train: dict, welded: dict | None = None) -> list[str]:
    """What the cut must not have changed (less what ``welded``, ``weld_chain``'s report, took out)."""

    import numpy as np

    welded = welded or {"qpos": [], "dofs": [], "equalities": []}
    expect = {**engine, "nq": engine["nq"] - len(welded["qpos"]), "nv": engine["nv"] - len(welded["dofs"]),
              "neq": engine["neq"] - len(welded["equalities"])}
    problems = [f"{k}: engine {expect[k]}, training {train[k]}"
                for k in ("nq", "nv", "nu", "neq", "nsensor", "actuated_joints") if expect[k] != train[k]]
    if abs(engine["mass_kg"] - train["mass_kg"]) > 1e-6 * engine["mass_kg"]:
        problems.append(f"mass_kg: engine {engine['mass_kg']}, training {train['mass_kg']}")
    if not problems:
        keep = [i for i in range(engine["nv"]) if i not in set(welded["dofs"])]
        a, b = np.array(engine["mass_matrix"])[np.ix_(keep, keep)], np.array(train["mass_matrix"])
        if np.abs(a - b).max() > 1e-9 * max(1.0, np.abs(a).max()):
            problems.append(f"mass matrix at qpos0 differs by {np.abs(a - b).max():.3g}")
    return problems


# --- fidelity ---------------------------------------------------------------

def controls(nu: int, amplitude: float, frequency: float, seconds: float = SECONDS):
    """The open-loop control sequence, one row per control step."""

    import numpy as np

    t = np.arange(int(round(seconds / CONTROL_DT)))[:, None] * CONTROL_DT
    phase = 2 * np.pi * np.arange(nu)[None, :] / nu
    return amplitude * np.sin(2 * np.pi * frequency * t + phase)


def _reset(mj, m, d) -> None:
    mj.mj_resetDataKeyframe(m, d, 0) if m.nkey else mj.mj_resetData(m, d)


def root_path(xml: str, ctrl, timestep: float | None = None):
    """The root's position at the end of each control step under ``ctrl``."""

    import mujoco as mj
    import numpy as np

    m = mj.MjModel.from_xml_string(xml)
    if timestep is not None:
        m.opt.timestep = timestep
    d = mj.MjData(m)
    _reset(mj, m, d)
    n = round(CONTROL_DT / m.opt.timestep)
    path = np.empty((len(ctrl), 3))
    for k, row in enumerate(ctrl):
        d.ctrl[:] = row
        for _ in range(n):
            mj.mj_step(m, d)
        path[k] = d.qpos[:3]
    return path


def max_error(a, b) -> float:
    """The largest root position error between two paths; a blow-up is infinite."""

    import numpy as np

    err = np.linalg.norm(a - b, axis=1).max()
    return float(err) if np.isfinite(err) else float("inf")


def floor_loads(model, data) -> dict[str, float]:
    """The normal force on the floor, by the body that presses it."""

    import mujoco as mj
    import numpy as np

    loads: dict[str, float] = {}
    for i in range(data.ncon):
        c = data.contact[i]
        f = np.zeros(6)
        mj.mj_contactForce(model, data, i, f)
        if model.geom_bodyid[c.geom1] == 0:
            other = c.geom2
        elif model.geom_bodyid[c.geom2] == 0:
            other = c.geom1
        else:
            continue
        body = mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, int(model.geom_bodyid[other]))
        loads[body] = loads.get(body, 0.0) + abs(float(f[0]))
    return loads


def stand(xml: str, seconds: float = STAND_SECONDS, feet: Iterable[str] | None = None) -> dict[str, Any]:
    """A zero-action stand from keyframe 0; the feet are the bodies holding ``feet`` geoms, else touch sites."""

    import mujoco as mj
    import numpy as np

    m = mj.MjModel.from_xml_string(xml)
    root = ET.fromstring(xml)
    feet = (_bodies_holding(root, feet) if feet is not None
            else {str(b.get("name")) for b in _foot_bodies(root)})
    d = mj.MjData(m)
    _reset(mj, m, d)
    d.ctrl[:] = 0.0
    p0, q0 = d.qpos[:3].copy(), d.qpos[3:7].copy()
    for _ in range(int(round(seconds / m.opt.timestep))):
        mj.mj_step(m, d)
    finite = bool(np.all(np.isfinite(d.qpos)) and np.all(np.isfinite(d.qvel)))
    mj.mj_forward(m, d)
    loads = floor_loads(m, d) if finite else {}
    dq = np.zeros(3)
    mj.mju_subQuat(dq, d.qpos[3:7], q0)
    tilt = float(np.degrees(np.linalg.norm(dq[:2]))) if finite else float("inf")
    weight = 9.81 * float(m.body_mass.sum())
    total = sum(loads.values())
    on_feet = set(loads) == feet
    ok = finite and tilt < MAX_TILT_DEG and on_feet and abs(total - weight) <= LOAD_TOLERANCE * weight
    return {"seconds": seconds, "finite": finite, "tilt_deg": round(tilt, 3),
            "drift_mm": round(1000 * float(np.linalg.norm(d.qpos[:2] - p0[:2])), 2) if finite else None,
            "settle_mm": round(1000 * float(d.qpos[2] - p0[2]), 2) if finite else None,
            "floor_load_n": round(total, 1), "weight_n": round(weight, 1),
            "loads_n": {k: round(v, 1) for k, v in sorted(loads.items())}, "on_feet_only": on_feet, "pass": ok}


def judge(engine_xml: str, models: dict[str, str], tolerance: float = TOLERANCE_M,
          converged: float = CONVERGED_M, frequencies=FREQUENCIES_HZ, amplitudes=AMPLITUDES_RAD,
          stand_seconds: float = STAND_SECONDS, feet: Iterable[str] | None = None) -> dict[str, Any]:
    """Every signal on the engine, its half-step floor and each model; then each model's stand."""

    import mujoco as mj
    import numpy as np

    engine = mj.MjModel.from_xml_string(engine_xml)
    nu, dt = engine.nu, float(engine.opt.timestep)
    signals = []
    for f in frequencies:
        for a in amplitudes:
            ctrl = controls(nu, a, f)
            ref = root_path(engine_xml, ctrl)
            floor = max_error(root_path(engine_xml, ctrl, timestep=dt / 2), ref)
            signals.append({
                "frequency_hz": f, "amplitude_rad": a,
                "engine_travel_mm": round(1000 * float(np.linalg.norm(ref[-1] - ref[0])), 2),
                "engine_half_step_mm": round(1000 * floor, 3), "gated": floor <= converged,
                "error_mm": {name: round(1000 * max_error(root_path(xml, ctrl), ref), 3)
                             for name, xml in models.items()}})
    verdicts = {}
    for name, xml in models.items():
        gated = [s["error_mm"][name] for s in signals if s["gated"]]
        worst = max(gated) if gated else None
        fidelity = bool(gated) and worst <= 1000 * tolerance
        standing = stand(xml, stand_seconds, feet)
        verdicts[name] = {"fidelity_worst_gated_mm": worst, "fidelity_pass": fidelity,
                          "stand": standing, "pass": fidelity and standing["pass"]}
    return {"tolerance_mm": 1000 * tolerance, "converged_mm": 1000 * converged,
            "control_dt": CONTROL_DT, "seconds": SECONDS, "engine_timestep": dt,
            "signals": signals, "models": verdicts}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _emit(report: dict, path: Path | None) -> None:
    text = json.dumps(report, indent=1)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
    print(text)


def _engine_path(args) -> Path:
    if args.engine:
        return args.engine
    if args.project:
        return project_export(args.project)
    raise SystemExit("name the engine MJCF: --project DIR or --engine MJCF")


def _names(text: str | None) -> list[str] | None:
    return None if text is None else [n for n in text.split(",") if n]


def cmd_cut(args) -> int:
    source = _engine_path(args)
    engine_xml = source.read_text()
    given = {k: getattr(args, k) for k in DEFAULTS if getattr(args, k) is not None}
    ladder = [{**LADDER[0], **given}] if given else list(LADDER)
    engine = compiled(engine_xml)
    tried = []
    for options in ladder:
        train_xml, kept = derive(engine_xml, **options, feet=_names(args.feet),
                                 fall_geoms=_names(args.fall_geoms), fall_condim=args.fall_condim,
                                 weld=_names(args.weld))
        train = compiled(train_xml)
        problems = compare(engine, train, kept.get("welded"))
        verdict = None
        if not problems and not args.no_check:
            verdict = judge(engine_xml, {"training": train_xml}, args.tolerance, args.converged,
                            feet=kept["feet"])
            if not verdict["models"]["training"]["pass"]:
                problems = ["fidelity or standing failed"]
        tried.append({"options": options, "problems": problems, "sha256": sha256(train_xml),
                      "check": verdict and _check_summary(verdict)})
        if not problems:
            break
    train.pop("mass_matrix")
    report = {"ok": not problems, "problems": problems, "engine_mjcf": str(source),
              "engine_mjcf_sha256": sha256(engine_xml), "training_mjcf_sha256": sha256(train_xml),
              "out": str(args.out), **kept, "options": {**options, "fall_condim": args.fall_condim},
              "tried": tried, "fidelity": verdict,
              "engine": {k: v for k, v in engine.items() if k != "mass_matrix"}, "training": train}
    if not problems:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(train_xml)
    _emit(report, args.json)
    return 1 if problems else 0


def _check_summary(verdict: dict) -> dict:
    model = verdict["models"]["training"]
    return {"worst_gated_mm": model["fidelity_worst_gated_mm"],
            "gated": sum(s["gated"] for s in verdict["signals"]), "signals": len(verdict["signals"]),
            "stand_tilt_deg": model["stand"]["tilt_deg"], "stand_pass": model["stand"]["pass"],
            "pass": model["pass"]}


def cmd_fidelity(args) -> int:
    import mujoco as mj

    source = _engine_path(args)
    engine_xml = source.read_text()
    texts = {str(p): p.read_text() for p in args.models}
    result = judge(engine_xml, texts, args.tolerance, args.converged, feet=_names(args.feet))
    result["engine_mjcf"] = str(source)
    result["engine_mjcf_sha256"] = sha256(engine_xml)
    for name, xml in texts.items():
        m = mj.MjModel.from_xml_string(xml)
        result["models"][name].update(
            sha256=sha256(xml),
            options={"timestep": float(m.opt.timestep), "iterations": int(m.opt.iterations),
                     "ls_iterations": int(m.opt.ls_iterations), "integrator": int(m.opt.integrator)})
    _emit(result, args.json)
    return 0 if all(v["pass"] for v in result["models"].values()) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("cut", "fidelity"):
        p = sub.add_parser(name)
        p.add_argument("--project", type=Path, help="a Cadex project: its accepted MJCF export")
        p.add_argument("--engine", type=Path, help="the engine MJCF export itself")
        p.add_argument("--json", type=Path, help="also write the report here")
        if name == "cut":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--timestep", type=float, help="seconds (with any solver option: only this setting)")
            p.add_argument("--iterations", type=int)
            p.add_argument("--ls-iterations", type=int)
            p.add_argument("--integrator", choices=("Euler", "implicitfast", "implicit", "RK4"))
            p.add_argument("--no-check", action="store_true", help="skip the fidelity and standing check")
            p.add_argument("--fall-geoms", help="comma-separated geoms kept against the floor besides the "
                                                "feet (default: the root's and multi-foot bodies')")
            p.add_argument("--fall-condim", type=int, default=1, choices=(1, 3))
            p.add_argument("--weld", help="comma-separated joint patterns (fnmatch) of a held, cable-coupled "
                                          "chain to weld at its build pose, with its couplings (ADR-959)")
        else:
            p.add_argument("models", nargs="+", type=Path, help="training MJCFs to judge")
        p.add_argument("--feet", help="comma-separated foot geoms (default: on the touch sensors' bodies)")
        p.add_argument("--tolerance", type=float, default=TOLERANCE_M, help="metres")
        p.add_argument("--converged", type=float, default=CONVERGED_M, help="metres")
    args = parser.parse_args(argv)
    return cmd_cut(args) if args.command == "cut" else cmd_fidelity(args)


if __name__ == "__main__":
    sys.exit(main())
