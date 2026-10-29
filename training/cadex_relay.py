# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A CAD task bundle re-laid by name onto another model of the same robot: a concept or a cut.

A task bundle (``cadex-training-task-v1``) speaks in its export's numbers:
sensor addresses ordered by its task, body and actuator ids, qpos and qvel
layouts, and per-body randomisation as flat indices into ``body_mass`` and
``body_inertia``. A concept model (``cadex_concept.py``) or a training model
cut from the export (``cadex_training_model.py``) names its bodies, joints
and drives as the export does but numbers them differently, and a cut fuses
joint-free bodies into their parents, so the bundle does not run on either
as it stands. This writes one that does, mapping everything by name:

- **sensors**: the model's own ``<sensor>`` block, and the sites only its
  sensors use, are replaced by the export's, in the export's order, so every
  observation keeps its channels. A site keeps its pose on the nearest of its
  export ancestors the model has (a fused body's site moves to the body it
  was fused into, where it already was in the world). A sensor naming a body,
  joint, drive or geom the model lacks is dropped with its observation; a
  dropped channel that a reward, termination or foot term reads refuses;
- **actions**: each drive by its actuator's name; a missing drive refuses;
- **body entries** (reset variation, shoves, scans; anything with ``body``
  and ``body_id``): by body name, and a ``qpos_adr``/``qvel_adr`` beside it
  by its ``joint``, else the body's own first joint (the free root). An entry
  whose body the model lacks is dropped;
- **randomisation**: each field's row by the name of the body, joint, dof's
  joint, geom, site or actuator it indexes; an entry with any row the model
  lacks is dropped (a battery fused into the pelvis is no longer drawn
  apart from it);
- **poses**: every ``qpos``/``reset_qpos`` and ``qvel``/``reset_qvel`` row,
  joint by joint by name; a joint only the model has takes its ``qpos0``
  (and zero velocity).

Entries it cannot map by name (a goal's ``frame_id``, ``resting_contacts``
or ``driver_qpos_adr``) refuse rather than run wrong. Because the sensors are
the export's, a policy trained on the re-laid bundle reads the same channels
and plays on the export's own bundle: ``cadex evaluate``'s success spec
judges it on the engine MJCF unchanged.

    ~/cadex-train-venv/bin/python training/cadex_relay.py TASK.json MODEL.xml --out DIR

writes ``DIR/outputs/<task>`` and ``DIR/outputs/<model>`` (the model with the
export's sensors; ``cadex_train.py DIR/outputs/<task>`` trains it) and
``DIR/relay.json``, what was mapped and dropped. Exit 2 on a refusal.

Needs ``mujoco`` (the training venv); the standard library at module scope
(ADR-084).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

#: A sensor attribute naming an object, and the object type it names.
_REFERENCES = {"joint": "joint", "actuator": "actuator", "site": "site", "body": "body",
               "tendon": "tendon"}
#: ``objtype``/``reftype`` values and the object type they name.
_OBJTYPES = {"body": "body", "xbody": "body", "geom": "geom", "site": "site",
             "joint": "joint", "actuator": "actuator", "camera": "camera"}
#: A randomised field's prefix and the object type its rows are.
_FIELD_OBJECTS = {"body_": "body", "jnt_": "joint", "dof_": "dof", "geom_": "geom",
                  "site_": "site", "actuator_": "actuator"}
#: A joint type's qpos and qvel widths: free, ball, slide, hinge.
_JOINT_WIDTH = {0: (7, 6), 1: (4, 3), 2: (1, 1), 3: (1, 1)}
#: Index-bearing keys nothing here maps by name.
_UNMAPPED = ("frame_id", "driver_qpos_adr", "resting_contacts")


class Refused(Exception):
    pass


def _obj(mujoco: Any, kind: str) -> Any:
    return getattr(mujoco.mjtObj, f"mjOBJ_{'JOINT' if kind == 'joint' else kind.upper()}")


def _id(mujoco: Any, model: Any, kind: str, name: str) -> int:
    return int(mujoco.mj_name2id(model, _obj(mujoco, kind), name))


def _name(mujoco: Any, model: Any, kind: str, index: int) -> str:
    return str(mujoco.mj_id2name(model, _obj(mujoco, kind), index) or "")


def _sensor_refs(element: ET.Element) -> list[tuple[str, str]]:
    refs = [(kind, str(element.get(attr))) for attr, kind in _REFERENCES.items()
            if element.get(attr)]
    for name, typ in (("objname", "objtype"), ("refname", "reftype")):
        if element.get(name):
            refs.append((_OBJTYPES.get(str(element.get(typ)), str(element.get(typ))),
                         str(element.get(name))))
    return refs


def _fmt(values: Any) -> str:
    return " ".join(f"{float(v):.9g}" for v in values)


def relay_model(source_xml: bytes, target_xml: bytes) -> tuple[bytes, dict[str, Any]]:
    """The target model with the source's sensors and their sites, and what was dropped."""

    import mujoco
    import numpy as np

    src = mujoco.MjModel.from_xml_string(source_xml.decode("utf-8"))
    tgt = mujoco.MjModel.from_xml_string(target_xml.decode("utf-8"))
    data = mujoco.MjData(src)
    mujoco.mj_kinematics(src, data)
    src_root = ET.fromstring(source_xml)
    root = ET.fromstring(target_xml)
    bodies = {str(b.get("name")): b for b in root.iter("body") if b.get("name")}
    sensors = [s for block in src_root.findall("sensor") for s in block]

    def has(kind: str, name: str) -> bool:
        return kind == "site" or _id(mujoco, tgt, kind, name) >= 0

    kept, dropped = [], []
    for element in sensors:
        missing = [f"{kind} {name}" for kind, name in _sensor_refs(element) if not has(kind, name)]
        (dropped if missing else kept).append((element, missing))
    sites = {name for element, _ in kept for kind, name in _sensor_refs(element) if kind == "site"}

    # The target's own instruments go: its sensor block and the sites only it used.
    own = {name for block in root.findall("sensor") for s in block
           for kind, name in _sensor_refs(s) if kind == "site"}
    for block in root.findall("sensor"):
        root.remove(block)
    for body in [root.find("worldbody"), *bodies.values()]:
        for site in list(body.findall("site")) if body is not None else ():
            if site.get("name") in own | sites:
                body.remove(site)

    moved: dict[str, str] = {}
    for name in sorted(sites):
        sid = _id(mujoco, src, "site", name)
        if sid < 0:
            raise Refused(f"the export's sensors name a site it does not have: {name}")
        host = int(src.site_bodyid[sid])
        while host > 0 and _name(mujoco, src, "body", host) not in bodies:
            host = int(src.body_parentid[host])
        if host == 0:
            raise Refused(f"site {name}: no body above it in the export is in the model")
        host_name = _name(mujoco, src, "body", host)
        rot = data.xmat[host].reshape(3, 3)
        pos = rot.T @ (data.site_xpos[sid] - data.xpos[host])
        quat = np.zeros(4)
        site_quat = np.zeros(4)
        mujoco.mju_mat2Quat(site_quat, data.site_xmat[sid])
        neg = np.zeros(4)
        mujoco.mju_negQuat(neg, data.xquat[host])
        mujoco.mju_mulQuat(quat, neg, site_quat)
        original = next(s for s in src_root.iter("site") if s.get("name") == name)
        attrs = {k: v for k, v in original.attrib.items() if k not in ("pos", "quat", "euler",
                                                                          "axisangle", "xyaxes", "zaxis")}
        attrs.update(pos=_fmt(pos), quat=_fmt(quat))
        ET.SubElement(bodies[host_name], "site", attrs)
        src_owner = _name(mujoco, src, "body", int(src.site_bodyid[sid]))
        if src_owner != host_name:
            moved[name] = f"{src_owner} -> {host_name}"

    block = ET.Element("sensor")
    for element, _ in kept:
        block.append(copy.deepcopy(element))
    keyframe = root.find("keyframe")
    root.insert(list(root).index(keyframe) if keyframe is not None else len(root), block)
    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="unicode").encode("utf-8") + b"\n"
    mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    return xml, {"sensors_kept": len(kept),
                 "sensors_dropped": {str(e.get("name")): m for e, m in dropped},
                 "sites_moved": moved}


def relay_task(task: dict[str, Any], source_xml: bytes, target_xml: bytes,
               model_path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """``task`` re-laid onto ``target_xml`` (already carrying the source's sensors)."""

    import mujoco

    src = mujoco.MjModel.from_xml_string(source_xml.decode("utf-8"))
    tgt = mujoco.MjModel.from_xml_string(target_xml.decode("utf-8"))
    task = copy.deepcopy(task)
    report: dict[str, Any] = {"observations_dropped": [], "entries_dropped": [],
                              "randomisation_dropped": [], "joints_only_in_source": [],
                              "joints_only_in_target": []}

    # Observations by sensor name.
    observations, lost = [], []
    for entry in task["observations"]:
        sid = _id(mujoco, tgt, "sensor", str(entry["sensor"]))
        if sid < 0:
            report["observations_dropped"].append(str(entry["name"]))
            lost += [str(c) for c in entry["channels"]]
            continue
        if int(tgt.sensor_dim[sid]) != int(entry["dim"]):
            raise Refused(f"observation {entry['name']}: sensor {entry['sensor']} has "
                          f"dim {int(tgt.sensor_dim[sid])}, the bundle {entry['dim']}")
        observations.append({**entry, "adr": int(tgt.sensor_adr[sid])})
    task["observations"] = observations
    readers = json.dumps([task.get("reward"), task.get("termination"), task.get("feet")])
    used = [c for c in lost if re.search(rf"\b{re.escape(c)}\b", readers)]
    if used:
        raise Refused(f"the reward, terminations or foot terms read channels the model "
                      f"cannot sense: {used}")

    for action in task["actions"]:
        aid = _id(mujoco, tgt, "actuator", str(action["actuator"]))
        if aid < 0:
            raise Refused(f"the model has no drive {action['actuator']}")
        action["index"] = aid

    def first_joint(model: Any, body: int) -> int:
        return int(model.body_jntadr[body]) if int(model.body_jntnum[body]) else -1

    def pose(rows: list, size: str) -> list:
        """Rows in the source's qpos (``nq``) or qvel (``nv``) layout, in the target's."""

        width_src, width_tgt = int(getattr(src, size)), int(getattr(tgt, size))
        adr = "jnt_qposadr" if size == "nq" else "jnt_dofadr"
        out = []
        for row in rows:
            if len(row) != width_src:
                raise Refused(f"a {size} row of {len(row)} numbers, the export has {width_src}")
            new = [float(v) for v in (tgt.qpos0 if size == "nq" else [0.0] * width_tgt)]
            for j in range(tgt.njnt):
                k = _id(mujoco, src, "joint", _name(mujoco, tgt, "joint", j))
                if k < 0:
                    continue
                n = _JOINT_WIDTH[int(src.jnt_type[k])][size == "nv"]
                a, b = int(getattr(src, adr)[k]), int(getattr(tgt, adr)[j])
                new[b:b + n] = [float(v) for v in row[a:a + n]]
            out.append(new)
        return out

    def body_entry(entry: dict, where: str) -> bool:
        name = str(entry.get("body") or "")
        if not name:
            raise Refused(f"{where}: a body_id with no body name")
        b = _id(mujoco, tgt, "body", name)
        if b < 0:
            report["entries_dropped"].append(f"{where}: {entry.get('label', '')} on {name}")
            return False
        entry["body_id"] = b
        for key, adr in (("qpos_adr", "jnt_qposadr"), ("qvel_adr", "jnt_dofadr")):
            if key in entry:
                j = (_id(mujoco, tgt, "joint", str(entry["joint"])) if entry.get("joint")
                     else first_joint(tgt, b))
                if j < 0:
                    raise Refused(f"{where}: {name} has no joint for its {key}")
                entry[key] = int(getattr(tgt, adr)[j])
        return True

    def randomised(entry: dict, where: str) -> bool:
        fields = []
        for field in entry["fields"]:
            name = str(field["field"])
            kind = next((k for p, k in _FIELD_OBJECTS.items() if name.startswith(p)), None)
            if kind is None:
                raise Refused(f"{where}: cannot name the rows of {name}")
            array = getattr(src, name)
            width = int(array.size // array.shape[0])
            row, col = divmod(int(field["index"]), width)
            if kind == "dof":
                k = int(src.dof_jntid[row])
                j = _id(mujoco, tgt, "joint", _name(mujoco, src, "joint", k))
                t = -1 if j < 0 else int(tgt.jnt_dofadr[j]) + row - int(src.jnt_dofadr[k])
            else:
                t = _id(mujoco, tgt, kind, _name(mujoco, src, kind, row))
            if t < 0:
                report["randomisation_dropped"].append(
                    f"{where}: {entry.get('label', '')} on {entry.get('subject', '')}")
                return False
            fields.append({**field, "index": t * width + col})
        entry["fields"] = fields
        return True

    def rows(value: Any, size: str) -> Any:
        flat = bool(value) and not isinstance(value[0], list)
        out = pose([value] if flat else value, size)
        return out[0] if flat else out

    def walk(node: Any, where: str) -> bool:
        """Map ``node`` in place; ``False`` when it is a body entry to drop."""

        if isinstance(node, list):
            node[:] = [item for item in node if walk(item, where)]
        if not isinstance(node, dict):
            return True
        for key in _UNMAPPED:
            if node.get(key):
                raise Refused(f"{where}: {key} cannot be re-laid by name")
        if "body_id" in node or ("qpos_adr" in node and "body" in node):
            if not body_entry(node, where):
                return False
        else:
            for key, adr in (("qpos_adr", "jnt_qposadr"), ("qvel_adr", "jnt_dofadr")):
                if key in node:
                    j = _id(mujoco, tgt, "joint", str(node.get("joint") or node.get("name") or ""))
                    if j < 0:
                        raise Refused(f"{where}: {key} with no joint the model has")
                    node[key] = int(getattr(tgt, adr)[j])
        for key, value in list(node.items()):
            here = f"{where}.{key}"
            if key in ("observations", "actions") and where == "task":
                continue
            if key in ("qpos", "reset_qpos") and isinstance(value, list) and value:
                node[key] = rows(value, "nq")
            elif key in ("qvel", "reset_qvel") and isinstance(value, list) and value:
                node[key] = rows(value, "nv")
            elif key == "randomisation" and isinstance(value, list):
                node[key] = [e for e in value if randomised(e, here)]
            elif not walk(value, here):
                raise Refused(f"{here}: names a body the model does not have")
        return True

    walk(task, "task")
    names = {kind: {_name(mujoco, m, "joint", j) for j in range(m.njnt)} for kind, m in
             (("src", src), ("tgt", tgt))}
    report["joints_only_in_source"] = sorted(names["src"] - names["tgt"])
    report["joints_only_in_target"] = sorted(names["tgt"] - names["src"])
    task["model"] = {**task["model"], "path": model_path, "bytes": len(target_xml),
                     "sha256": hashlib.sha256(target_xml).hexdigest()}

    # The control interval stays the export's; the substeps follow the model's own step,
    # which the trainer never overrides (ADR-863).
    episode = task.get("episode")
    if isinstance(episode, dict) and "solver_steps_per_action" in episode:
        step = float(tgt.opt.timestep)
        interval = float(episode.get("control_interval_s")
                          or float(episode["solver_step_s"]) * int(episode["solver_steps_per_action"]))
        per = interval / step
        if abs(per - round(per)) > 1e-6:
            raise Refused(f"the control interval {interval} s is not a whole number of the model's {step} s steps")
        report["solver_steps"] = [int(episode["solver_steps_per_action"]), int(round(per))]
        episode.update(solver_step_s=step, solver_steps_per_action=int(round(per)))
    return task, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("task", type=Path, help="the CAD task bundle, <root>/outputs/<name>-task.json")
    ap.add_argument("model", type=Path, help="the model to re-lay it onto: a concept or a cut")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import numpy as np
    from cadex_train import globals_for, load_bundle  # noqa: PLC0415 - the trainer's own reading

    bundle = load_bundle(str(a.task), globals_for(np))
    target = a.model.read_bytes()
    try:
        xml, sensed = relay_model(bundle["model_xml"], target)
        path = f"outputs/{a.model.name}"
        task, mapped = relay_task(bundle["task"], bundle["model_xml"], xml, path)
    except Refused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    report = {"schema": "cadex-relay-v1", "task_sha256": bundle["task_sha256"],
              "export_sha256": bundle["model_sha256"],
              "onto_sha256": hashlib.sha256(target).hexdigest(),
              "model_sha256": task["model"]["sha256"], **sensed, **mapped}
    outputs = a.out / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / a.model.name).write_bytes(xml)
    (outputs / a.task.name).write_text(json.dumps(task, indent=1) + "\n", encoding="utf-8")
    (a.out / "relay.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(f"{len(task['observations'])} observations, {len(task['actions'])} drives, "
          f"{sensed['sensors_kept']} sensors kept")
    for key in ("sensors_dropped", "sites_moved", "observations_dropped", "entries_dropped",
                "randomisation_dropped", "joints_only_in_source", "joints_only_in_target"):
        if report[key]:
            print(f"{key.replace('_', ' ')}: {report[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
