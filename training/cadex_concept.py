# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The concept model: a robot spec as a box-and-capsule MJCF, trained before any CAD.

A legged design's first questions -- link lengths, stance angles, which way a
knee bends, joint limits, where the drives sit -- are answered by training a
policy, and a full CAD build is the dearest place to ask them. This writes a
crude model straight from a spec (``cadex-concept-v1`` JSON): trunk boxes,
capsule segments, sphere feet, the drives' gains, limits and rotor inertia.
It changes in seconds, so a sweep can train each variant; the numbers that
pass are frozen into the spec, the CAD is built to meet them, and the detailed
model is trained again to confirm the concept was close enough.

The model is written the way the engine writes ``assembly.mjcf`` (and the way a
training model is cut from it): every body frame is the world frame at the home
pose, so the home pose is the zero of every joint and the ``solved`` keyframe;
the floor touches only feet and the trunk's fall geoms; each drive is a
position actuator ``<joint>/position``; and the sensors are the export's, in
its order (``obs/N``: each actuated joint's position, velocity and force, then
the IMU's orientation and rate, the root's centre of mass and velocity, and
each foot's centre of mass and touch). A tool that reads an engine export by
name reads a concept model the same way.

The spec, all lengths in metres, masses in kilograms, angles in degrees:

* ``drives``: name -> a datasheet in ``cadex_proxy.py``'s library format
  (``peak_torque_nm``, ``rated_torque_nm``, ``no_load_speed_rpm``,
  ``gear_ratio``, ``rotor_inertia_gcm2``, ``back_drive_torque_nm``,
  ``mass_g``), from which the damping, armature and friction come as the
  proxy derives them, plus the servo's ``kp`` and ``kd``; or those MJCF
  numbers given raw (``peak_nm``, ``armature``, ``damping``,
  ``frictionloss``). The housing's mass is not added for you: place it with
  ``end_mass`` or ``masses``.
* ``trunk``: bodies, the first the root. Each has ``name``, ``boxes`` and
  ``capsules`` (``mass``, ``center``/``half`` or ``from``/``to``/``radius``;
  ``fall: true`` lets it touch the floor), point ``masses`` (``at``, ``kg``),
  and every body but the root a ``parent`` and a ``joint`` (``name``, ``at``,
  ``axis``, ``range``, ``drive``).
* ``imu``: ``body``, ``parent``, ``at``.
* ``legs``: each with ``mount`` (a trunk body), ``start`` (its first joint),
  ``mirror`` (adds a right leg reflected in y; ``{s}`` in a name becomes ``l``
  or ``r``), ``joints`` and ``foot``. A joint has ``name``, ``body``, ``axis``,
  ``range`` (the left leg's), either a ``drive`` or ``follows`` + ``ratio`` (a
  passive joint tied to another, a linkage), and the segment its body spans to
  the next joint: ``to`` [dx, dy, dz], or ``length`` with ``pitch`` (from
  straight down, positive toward +x) and ``dy``. The segment carries ``mass``
  as a capsule of ``radius`` and ``end_mass`` at its far end. ``foot``:
  ``body``, ``radius``, ``mass``.
* ``options``: ``timestep``, ``iterations``, ``ls_iterations``,
  ``integrator``, ``solref``.

A right leg mirrors the left: points and axes reflect in y and each range
negates and swaps, so a joint angle on the right is the mirror of the same
angle on the left, as the export writes it.

The model stands on its feet: the whole spec is moved in z so the lowest foot
sphere rests on the floor, and the report gives every other foot's height off
it (a sweep that lengthens one leg lifts the others). It also says what the spec
implies -- each leg's hip height (its first pitch joint's), its reach from there, and
its ``bend`` (one less the hip-to-foot distance over the summed segments: a leg near 0 is straight and
can barely slide its foot along the floor) -- which is what a sweep reads.

    ~/cadex-train-venv/bin/python training/cadex_concept.py SPEC.json --out MODEL.xml \\
        [--set legs.1.joints.2.length=0.15 ...] [--report REPORT.json]

Like ``cadex_train.py`` it imports only the standard library at module scope;
``mujoco`` is imported where the model is checked.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "cadex-concept-v1"
DEFAULT_OPTIONS = {"timestep": 0.0025, "iterations": 1, "ls_iterations": 5,
                   "integrator": "Euler", "solref": 0.004}
PASSIVE_DAMPING = 0.005
POINT_RADIUS = 0.01


class ConceptError(ValueError):
    pass


def apply_sets(spec: Mapping[str, Any], sets: Sequence[str]) -> dict:
    """``path=value`` overrides: a dotted path of keys and list indices, a JSON value."""
    out = copy.deepcopy(dict(spec))
    for item in sets:
        path, _, raw = item.partition("=")
        if not path or not _:
            raise ConceptError(f"--set {item!r}: expected path=value")
        keys = path.split(".")
        node: Any = out
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value
    return out


def _mirror(v: Sequence[float]) -> list[float]:
    return [v[0], -v[1], v[2]]


def _segment(joint: Mapping[str, Any]) -> list[float]:
    if "to" in joint:
        return [float(x) for x in joint["to"]]
    if "length" not in joint:
        raise ConceptError(f"joint {joint.get('name')!r}: give 'to' or 'length' and 'pitch'")
    length, pitch = float(joint["length"]), math.radians(float(joint.get("pitch", 0.0)))
    return [length * math.sin(pitch), float(joint.get("dy", 0.0)), -length * math.cos(pitch)]


def _add(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def expand_legs(spec: Mapping[str, Any]) -> list[dict]:
    """Each leg in world points at the home pose: every left (or unmirrored) leg, then every right."""
    left, right = [], []
    for leg in spec.get("legs", []):
        for side in ("l", "r") if leg.get("mirror") else ("",):
            flip = _mirror if side == "r" else (lambda v: list(v))
            name = (lambda s, side=side: s.replace("{s}", side))
            point = flip(leg["start"])
            joints = []
            for joint in leg["joints"]:
                seg = flip(_segment(joint))
                lo, hi = (float(x) for x in joint.get("range", (-180.0, 180.0)))
                joints.append({
                    "name": name(joint["name"]), "body": name(joint["body"]),
                    "at": point, "axis": flip(joint["axis"]),
                    "range": (-hi, -lo) if side == "r" else (lo, hi),
                    "drive": joint.get("drive"),
                    "follows": name(joint["follows"]) if joint.get("follows") else None,
                    "ratio": float(joint.get("ratio", 1.0)),
                    "end": _add(point, seg), "mass": float(joint.get("mass", 0.0)),
                    "radius": float(joint.get("radius", 0.02)),
                    "end_mass": float(joint.get("end_mass", 0.0)),
                    "limited": "range" in joint})
                point = _add(point, seg)
            foot = leg["foot"]
            entry = {"mount": leg["mount"], "joints": joints,
                     "foot": {"body": name(foot["body"]), "at": point,
                              "radius": float(foot["radius"]), "mass": float(foot["mass"])}}
            (right if side == "r" else left).append(entry)
    return left + right


def _fmt(v: Sequence[float] | float) -> str:
    if isinstance(v, (int, float)):
        return f"{float(v):.6g}"
    return " ".join(f"{float(x):.6g}" for x in v)


def _drop(v: Sequence[float], dz: float) -> list[float]:
    return [v[0], v[1], v[2] - dz]


def _drive(name: str, d: Mapping[str, Any]) -> dict:
    """A drive as the model takes it: a datasheet (the proxy's library format) or raw numbers."""
    out = dict(d)
    if "peak_torque_nm" in d:
        from cadex_proxy import ProxyError, drive_constants  # noqa: PLC0415 -- a sibling script

        try:
            constants = drive_constants(d)
        except ProxyError as exc:
            raise ConceptError(f"drive {name!r}: {exc}") from exc
        out = {**{k: v for k, v in constants.items() if v is not None}, **d}
        out.setdefault("frictionloss", 0.0)
    for key in ("peak_nm", "kp", "kd", "armature", "damping", "frictionloss"):
        if not isinstance(out.get(key), (int, float)):
            raise ConceptError(f"drive {name!r} needs {key}, or a datasheet that gives it")
    return out


def build(spec: Mapping[str, Any]) -> tuple[str, dict]:
    """The MJCF text and the report."""
    if spec.get("format") != FORMAT:
        raise ConceptError(f"spec format must be {FORMAT!r}")
    drives = {k: _drive(k, v) for k, v in spec.get("drives", {}).items() if not k.startswith("_")}
    trunk = spec["trunk"]
    legs = expand_legs(spec)
    if not legs:
        raise ConceptError("a concept needs at least one leg")
    dz = min(leg["foot"]["at"][2] - leg["foot"]["radius"] for leg in legs)
    opts = {**DEFAULT_OPTIONS, **spec.get("options", {})}
    solref = _fmt(opts["solref"])

    root = ET.Element("mujoco", model=spec.get("name", "cadex-concept"))
    ET.SubElement(root, "compiler", angle="radian", autolimits="false", inertiafromgeom="true")
    option = ET.SubElement(root, "option", integrator=str(opts["integrator"]),
                           timestep=_fmt(opts["timestep"]), iterations=str(opts["iterations"]),
                           ls_iterations=str(opts["ls_iterations"]))
    ET.SubElement(option, "flag", island="disable", eulerdamp="disable")
    ET.SubElement(root, "size", nkey="1")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "geom", name="environment/floor", size="0 0 0.1", type="plane",
                  solref=solref, contype="1", conaffinity="0")

    bodies: dict[str, ET.Element] = {}
    actuated: list[tuple[str, Mapping[str, Any]]] = []  # legs' drives, then the trunk's
    trunk_actuated: list[tuple[str, Mapping[str, Any]]] = []
    couplings: list[tuple[str, str, float]] = []

    def point_mass(body: ET.Element, name: str, at, kg: float) -> None:
        if kg > 0:
            ET.SubElement(body, "geom", name=name, type="sphere", size=_fmt(POINT_RADIUS),
                          pos=_fmt(_drop(at, dz)), mass=_fmt(kg), contype="0",
                          conaffinity="0", group="3")

    def joint(body: ET.Element, name: str, at, axis, rng, limited: bool, drive: str | None,
              into: list) -> None:
        attrs = {"name": name, "pos": _fmt(_drop(at, dz)), "axis": _fmt(axis)}
        if limited:
            attrs.update(limited="true", range=_fmt([math.radians(rng[0]), math.radians(rng[1])]))
        else:
            attrs["limited"] = "false"
        if drive:
            if drive not in drives:
                raise ConceptError(f"joint {name!r}: unknown drive {drive!r}")
            d = drives[drive]
            attrs.update(armature=_fmt(d["armature"]), damping=_fmt(d["damping"]),
                         frictionloss=_fmt(d["frictionloss"]))
            into.append((name, d))
        else:
            attrs["damping"] = _fmt(PASSIVE_DAMPING)
        ET.SubElement(body, "joint", **attrs)

    for i, part in enumerate(trunk):
        parent = world if i == 0 else bodies.get(part.get("parent", ""))
        if parent is None:
            raise ConceptError(f"trunk body {part['name']!r}: parent must come before it")
        body = ET.SubElement(parent, "body", name=part["name"])
        bodies[part["name"]] = body
        if i == 0:
            ET.SubElement(body, "joint", name=f"{part['name']}/free", type="free")
        else:
            j = part["joint"]
            joint(body, j["name"], j["at"], j["axis"], j.get("range", (-180, 180)),
                  "range" in j, j.get("drive"), trunk_actuated)
        for k, box in enumerate(part.get("boxes", [])):
            fall = bool(box.get("fall"))
            ET.SubElement(body, "geom", name=f"{part['name']}/box{k}", type="box",
                          size=_fmt(box["half"]), pos=_fmt(_drop(box["center"], dz)),
                          mass=_fmt(box["mass"]), solref=solref, condim="1",
                          contype="0", conaffinity="1" if fall else "0")
        for k, cap in enumerate(part.get("capsules", [])):
            fall = bool(cap.get("fall"))
            ET.SubElement(body, "geom", name=f"{part['name']}/capsule{k}", type="capsule",
                          fromto=_fmt(_drop(cap["from"], dz) + _drop(cap["to"], dz)),
                          size=_fmt(cap["radius"]), mass=_fmt(cap["mass"]), solref=solref,
                          condim="1", contype="0", conaffinity="1" if fall else "0")
        for k, m in enumerate(part.get("masses", [])):
            point_mass(body, f"{part['name']}/mass{k}", m["at"], float(m["kg"]))

    imu = spec.get("imu")
    if imu:
        body = ET.SubElement(bodies[imu["parent"]], "body", name=imu["body"])
        point_mass(body, f"{imu['body']}/mass", imu["at"], float(imu.get("kg", 0.0025)))
        bodies[imu["body"]] = body

    feet = []
    for leg in legs:
        parent = bodies.get(leg["mount"])
        if parent is None:
            raise ConceptError(f"leg mount {leg['mount']!r} is not a trunk body")
        for j in leg["joints"]:
            body = ET.SubElement(parent, "body", name=j["body"])
            joint(body, j["name"], j["at"], j["axis"], j["range"], j["limited"],
                  None if j["follows"] else j["drive"], actuated)
            if j["follows"]:
                couplings.append((j["name"], j["follows"], j["ratio"]))
            if j["mass"] > 0:
                ET.SubElement(body, "geom", name=f"{j['body']}/capsule", type="capsule",
                              fromto=_fmt(_drop(j["at"], dz) + _drop(j["end"], dz)),
                              size=_fmt(j["radius"]), mass=_fmt(j["mass"]), contype="0",
                              conaffinity="0")
            point_mass(body, f"{j['body']}/end", j["end"], j["end_mass"])
            parent = body
        foot = leg["foot"]
        body = ET.SubElement(parent, "body", name=foot["body"])
        ET.SubElement(body, "geom", name=f"{foot['body']}/collision0", type="sphere",
                      size=_fmt(foot["radius"]), pos=_fmt(_drop(foot["at"], dz)),
                      mass=_fmt(foot["mass"]), solref=solref, contype="0", conaffinity="1")
        feet.append((foot, body))

    actuated += trunk_actuated
    if couplings:
        equality = ET.SubElement(root, "equality")
        for follower, leader, ratio in couplings:
            ET.SubElement(equality, "joint", name=f"{follower}/follows", joint1=follower,
                          joint2=leader, polycoef=_fmt([0, ratio, 0, 0, 0]), solref=solref)

    actuator = ET.SubElement(root, "actuator")
    for name, d in actuated:
        kp, kd = float(d["kp"]), float(d["kd"])
        ET.SubElement(actuator, "general", name=f"{name}/position", joint=name,
                      ctrllimited="false", forcelimited="true",
                      forcerange=_fmt([-d["peak_nm"], d["peak_nm"]]), biastype="affine",
                      gainprm=_fmt(kp), biasprm=_fmt([0, -kp, -kd]))

    sensor = ET.SubElement(root, "sensor")
    index = 0

    def add(tag: str, **attrs: str) -> int:
        nonlocal index
        ET.SubElement(sensor, tag, name=f"obs/{index}", **attrs)
        index += 1
        return index - 1

    for name, _ in actuated:
        add("jointpos", joint=name)
        add("jointvel", joint=name)
        add("actuatorfrc", actuator=f"{name}/position")
    if imu:
        add("framequat", objtype="xbody", objname=imu["body"])
        add("frameangvel", objtype="xbody", objname=imu["body"])
    add("subtreecom", body=trunk[0]["name"])
    add("subtreelinvel", body=trunk[0]["name"])
    for foot, body in feet:
        add("subtreecom", body=foot["body"])
        r = _fmt(foot["radius"])
        ET.SubElement(body, "site", name=f"obs/{index}/contact", type="box",
                      pos=_fmt(_drop(foot["at"], dz)), size=f"{r} {r} {r}", rgba="0 0 0 0")
        add("touch", site=f"obs/{index}/contact")

    keyframe = ET.SubElement(root, "keyframe")
    ET.SubElement(keyframe, "key", name="solved")
    ET.indent(root)
    xml = ET.tostring(root, encoding="unicode") + "\n"
    return xml, _report(spec, legs, dz, drives)


def _report(spec, legs, dz, drives) -> dict:
    rows = []
    for leg in legs:
        foot = leg["foot"]
        pitched = [j for j in leg["joints"] if abs(j["axis"][1]) > 0.5]
        first = pitched[0] if pitched else leg["joints"][0]
        chain = leg["joints"][leg["joints"].index(first):]
        rows.append({
            "foot": foot["body"],
            "off_floor_m": round(foot["at"][2] - foot["radius"] - dz, 4),
            "hip_height_m": round(first["at"][2] - dz, 4),
            "bend": round(1.0 - math.dist(first["at"], foot["at"])
                          / sum(math.dist(j["at"], j["end"]) for j in chain), 4),
            "reach_m": round(sum(math.dist(j["at"], j["end"]) for j in chain), 4),
            "hip_to_foot_m": round(math.dist(first["at"], foot["at"]), 4),
            "foot_x_from_hip_m": round(foot["at"][0] - first["at"][0], 4),
            "knee_bends": _knee(leg)})
    return {"format": FORMAT, "name": spec.get("name"), "legs": rows,
            "actuated": [j["name"] for leg in legs for j in leg["joints"] if not j["follows"]]
                        + [t["joint"]["name"] for t in spec["trunk"][1:] if t["joint"].get("drive")],
            "drives": {k: {f: v[f] for f in ("peak_nm", "rated_nm") if f in v}
                       for k, v in drives.items()}}


def _knee(leg) -> str | None:
    """Which way the leg's middle bends: the joint whose segments turn most, by the turn's sign."""
    pitch = [j for j in leg["joints"] if abs(j["axis"][1]) > 0.5 and not j["follows"]]
    if len(pitch) < 2:
        return None
    knee = pitch[1]
    upper = [knee["at"][i] - pitch[0]["at"][i] for i in (0, 2)]
    lower = [knee["end"][i] - knee["at"][i] for i in (0, 2)]
    cross = upper[1] * lower[0] - upper[0] * lower[1]
    return "forward" if cross < 0 else "backward"


def check(xml: str) -> dict:
    """Compile the model and say what MuJoCo makes of it."""
    import mujoco  # noqa: PLC0415 -- only where the model is checked

    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return {"mass_kg": round(float(model.body_subtreemass[1]), 4), "nq": model.nq,
            "nu": model.nu, "nsensor": model.nsensor,
            "com_m": [round(float(x), 4) for x in data.subtree_com[1]]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", help=f"a {FORMAT} JSON")
    parser.add_argument("--out", required=True, help="the MJCF to write")
    parser.add_argument("--set", action="append", default=[], metavar="PATH=VALUE",
                        help="override a spec value by dotted path (repeatable)")
    parser.add_argument("--report", help="also write the report here")
    parser.add_argument("--no-check", action="store_true", help="skip compiling with mujoco")
    args = parser.parse_args(argv)
    try:
        spec = apply_sets(json.loads(Path(args.spec).read_text(encoding="utf-8")), args.set)
        xml, report = build(spec)
    except (ConceptError, KeyError, IndexError) as exc:
        print(f"cadex_concept: {exc}", file=sys.stderr)
        return 2
    if not args.no_check:
        report["compiled"] = check(xml)
    report["sets"] = list(args.set)
    Path(args.out).write_text(xml, encoding="utf-8")
    text = json.dumps(report, indent=1)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
