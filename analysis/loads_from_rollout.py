#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The load case, measured from the machine doing its job (S0, step 3b).

For a printed bracket you declare the load, because you know it. For a leg
in a walking robot you do not: the load on a thigh is whatever the policy
made the leg do, and guessing it is how a part gets designed for a duty
cycle it never sees.

MuJoCo already computes it. ``mj_rnePostConstraint`` fills two arrays that
nothing in the engine reads:

* ``data.cfrc_int[body]`` -- the 6-D **joint reaction wrench** between a
  body and its parent.
* ``data.cfrc_ext[body]`` -- the 6-D **external wrench** on that body,
  contact and applied.

So the load case for "is this thigh strong enough" is *the worst wrench
that body saw across a rollout*, read out of the same MJCF
``assembly.mjcf`` already exports. Nothing new is needed from the engine:
``contact_force`` being a deferred engine observation does not matter,
because this runs offboard in stock MuJoCo.

**How the rollout gets here, and how you know it arrived.** This does not
run a policy. It replays a trace the engine already published --
``outputs/*-simulation-trace.json``, schema
``cadex-assembly-simulation-trace-v1`` -- by holding each frame's
``actuator_commands`` over that frame's interval and stepping stock MuJoCo.
Then it **checks its own replay**: every frame's replayed body positions are
compared against the poses the trace recorded, and the worst mismatch is in
the report. A replay that tracked the trace to within a micron reproduced
the rollout and its wrenches are the rollout's wrenches. One that did not
says so with a number, and the number is usually the same cause -- a trace
sampled at fewer frames a second than the policy acted at holds only some
of the actions, so the replay gets a different trajectory. Author the
rollout at ``frames_per_second`` equal to the control rate when you intend
to read loads off it.

That check is the whole reason this is trustworthy: it is ADR-129's lesson
applied to a second thing. The wrench is not "what MuJoCo says if you feed
it something plausible", it is "what MuJoCo says on a trajectory that
demonstrably is the one the policy flew".

**Not part of the engine, not in the payload.** ADR-141, the same contract
``training/`` holds under (ADR-084). ``mujoco`` is pinned in
``analysis/requirements.txt`` and installed into a venv; the pin must match
the release that wrote the model, for the reason ADR-075 pins it exactly.

Usage::

    python analysis/loads_from_rollout.py model.xml \\
        --trace outputs/legs-simulation-trace.json --body thigh_left
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any, Sequence

import numpy as np

REPORT_SCHEMA = "cadex-analysis-rollout-loads-v1"
TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
LOAD_CASE_SCHEMA = "cadex-analysis-load-case-v1"

#: Below this, in millimetres, the replay is the rollout. A trace frame
#: records a pose the solver produced from the same actions on the same
#: model, so an exact replay differs only by the order floating-point
#: operations happened in. Above it, the report says the trajectory diverged
#: and the wrenches belong to a different motion than the one that was
#: watched.
REPLAY_TOLERANCE_MM = 1.0e-3


class RolloutLoadError(RuntimeError):
    """A refusal, with a sentence a person can act on."""


def _mujoco() -> Any:
    try:
        import mujoco
    except ImportError as error:  # pragma: no cover - environment dependent
        raise RolloutLoadError(
            "This needs `mujoco`. Install it into the analysis venv: "
            "`python3 -m venv .venv && .venv/bin/pip install -r "
            "analysis/requirements.txt`. The pin must match the release that "
            f"wrote the model. ({error})"
        ) from error
    return mujoco


def read_trace(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    schema = str(raw.get("schema") or "")
    if schema != TRACE_SCHEMA:
        raise RolloutLoadError(
            f"{path.name} declares schema {schema!r}, and this reads "
            f"{TRACE_SCHEMA!r} -- the trace `assembly.rollout` and "
            "`assembly.simulation` publish."
        )
    if not raw.get("frames"):
        raise RolloutLoadError(f"{path.name} carries no frames.")
    return raw


def replay(model_path: Path, trace: dict[str, Any]) -> dict[str, Any]:
    """Step the trace's own actions through stock MuJoCo, recording wrenches.

    Returns per-body peak wrenches, the frame each peak happened on, and the
    replay fidelity against the trace's recorded poses.
    """

    mujoco = _mujoco()
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    if model.nkey:
        mujoco.mj_resetDataKeyframe(model, data, 0)
    else:
        mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    frames = [frame for frame in trace["frames"]
              if frame.get("frame_kind") != "input"]
    if not frames:
        raise RolloutLoadError("The trace has no solver_output frames to replay.")

    components = [str(name) for name in (trace.get("component_outputs") or [])]
    body_ids: dict[str, int] = {}
    for name in components:
        found = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name))
        if found < 0:
            raise RolloutLoadError(
                f"The trace plays a component named {name!r} and the model "
                "carries no body of that name. The trace and the MJCF must "
                "come from the same accepted attempt."
            )
        body_ids[name] = found

    channels = [str(row["actuator"]) for row in (trace.get("actuator_channels") or [])]
    actuator_ids = []
    for name in channels:
        found = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name))
        if found < 0:
            raise RolloutLoadError(
                f"The trace names an actuator {name!r} the model does not carry."
            )
        actuator_ids.append(found)

    interval = float(trace.get("parameters", {}).get("time_step_s") or 0.0)
    if interval <= 0.0:
        raise RolloutLoadError(
            "The trace declares no positive `parameters.time_step_s`, so "
            "there is no interval to hold each action over."
        )
    step = float(model.opt.timestep)
    per_frame = max(1, int(round(interval / step)))
    if abs(per_frame * step - interval) > 1e-9:
        raise RolloutLoadError(
            f"The trace's frame interval ({interval:g} s) is not a whole "
            f"number of the model's solver steps ({step:g} s). The replay "
            "would land its actions between two frames."
        )

    names = list(body_ids)
    peaks = {
        name: {
            "internal": _empty_peak(),
            "external": _empty_peak(),
        }
        for name in names
    }
    worst_position_mm = 0.0
    worst_frame = -1

    for index, frame in enumerate(frames):
        commands = frame.get("actuator_commands")
        if commands is not None and actuator_ids:
            values = [float(value) for value in commands]
            if len(values) != len(actuator_ids):
                raise RolloutLoadError(
                    f"Frame {index} carries {len(values)} actuator commands "
                    f"and the trace advertises {len(actuator_ids)} channels."
                )
            for actuator, value in zip(actuator_ids, values):
                data.ctrl[actuator] = value
        if index:
            for _ in range(per_frame):
                mujoco.mj_step(model, data)
        mujoco.mj_rnePostConstraint(model, data)

        placements = frame.get("component_placements") or {}
        for name in names:
            body = body_ids[name]
            recorded = placements.get(name)
            if recorded:
                observed = np.asarray(data.xpos[body], dtype=float) * 1000.0
                expected = np.asarray(recorded["position_mm"], dtype=float)
                error = float(np.linalg.norm(observed - expected))
                if error > worst_position_mm:
                    worst_position_mm = error
                    worst_frame = index
            _record(peaks[name]["internal"], model, data, body, index, "cfrc_int")
            _record(peaks[name]["external"], model, data, body, index, "cfrc_ext")

    return {
        "bodies": peaks,
        "frames": len(frames),
        "frame_interval_s": interval,
        "solver_step_s": step,
        "steps_per_frame": per_frame,
        "replay": {
            "worst_position_error_mm": worst_position_mm,
            "worst_frame": worst_frame,
            "tolerance_mm": REPLAY_TOLERANCE_MM,
            "reproduced": worst_position_mm <= REPLAY_TOLERANCE_MM,
        },
        "anchors": _anchors(mujoco, model, data, body_ids),
    }


def _empty_peak() -> dict[str, Any]:
    return {
        "peak_force_n": 0.0, "peak_force_frame": -1, "at_peak_force": None,
        "peak_torque_n_mm": 0.0, "peak_torque_frame": -1, "at_peak_torque": None,
    }


def _record(peak: dict[str, Any], model: Any, data: Any, body: int,
            frame: int, field: str) -> None:
    """One body's wrench this frame, moved onto the body's own centre of mass.

    MuJoCo's ``cfrc_*`` are *com-based*: the torque is about
    ``subtree_com[body_rootid[body]]``, not about the body. A wrench read at
    the wrong reference point is a torque that is wrong by ``r x F``, which
    on a leg is the whole number -- so it is moved here rather than left for
    a reader to notice. ``t_p = t_c + (c - p) x F``.
    """

    raw = np.asarray(getattr(data, field)[body], dtype=float)
    torque_c = raw[:3]
    force = raw[3:]
    centre = np.asarray(data.subtree_com[model.body_rootid[body]], dtype=float)
    point = np.asarray(data.xipos[body], dtype=float)
    torque = torque_c + np.cross(centre - point, force)

    force_n = force
    torque_n_mm = torque * 1000.0  # N m -> N mm
    force_magnitude = float(np.linalg.norm(force_n))
    torque_magnitude = float(np.linalg.norm(torque_n_mm))
    snapshot = {
        "force_n": [float(value) for value in force_n],
        "torque_n_mm": [float(value) for value in torque_n_mm],
        "about_mm": [float(value) * 1000.0 for value in point],
    }
    if force_magnitude > peak["peak_force_n"]:
        peak["peak_force_n"] = force_magnitude
        peak["peak_force_frame"] = frame
        peak["at_peak_force"] = snapshot
    if torque_magnitude > peak["peak_torque_n_mm"]:
        peak["peak_torque_n_mm"] = torque_magnitude
        peak["peak_torque_frame"] = frame
        peak["at_peak_torque"] = snapshot


def _anchors(mujoco: Any, model: Any, data: Any,
             body_ids: dict[str, int]) -> dict[str, Any]:
    """Where each body is held, and where its children pull on it.

    A body's own joints are how its parent holds it; its children's joints
    are where the children hang off it. Those two sets are exactly the
    support and the load of a static analysis of that one part, which is why
    they are reported here in millimetres rather than left to be looked up.
    """

    anchors: dict[str, Any] = {}
    for name, body in body_ids.items():
        own = []
        for index in range(int(model.body_jntnum[body])):
            joint = int(model.body_jntadr[body]) + index
            own.append({
                "joint": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint),
                "anchor_mm": [float(value) * 1000.0 for value in data.xanchor[joint]],
            })
        children = []
        for other in range(int(model.nbody)):
            if int(model.body_parentid[other]) != body:
                continue
            child_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, other)
            for index in range(int(model.body_jntnum[other])):
                joint = int(model.body_jntadr[other]) + index
                children.append({
                    "body": child_name,
                    "joint": mujoco.mj_id2name(
                        model, mujoco.mjtObj.mjOBJ_JOINT, joint),
                    "anchor_mm": [float(value) * 1000.0
                                  for value in data.xanchor[joint]],
                })
        anchors[name] = {
            "held_at": own,
            "children_at": children,
            "mass_kg": float(model.body_mass[body]),
            "centre_of_mass_mm": [float(value) * 1000.0
                                  for value in data.xipos[body]],
        }
    return anchors


def load_case_fragment(body: str, measured: dict[str, Any], *,
                       radius_mm: float) -> dict[str, Any]:
    """A starting point for ``cadex_stress.py``, not an answer.

    The wrench is measured; where it attaches to *this part* is a judgement
    the author makes, so this writes the supports and loads out as sphere
    regions around the joint anchors the model reports and expects to be
    edited. Two things it deliberately does not decide:

    * **The material.** It is left ``null``. There is no default strength in
      this tree and there should not be: a safety factor against a yield
      nobody declared is a number pretending to be a verdict.
    * **The sign.** ``cfrc_int`` is the wrench the parent applies to the
      body through the joint. Held at that joint and loaded by its children,
      a part is in equilibrium; held at a child and loaded by the parent it
      is the same statics with every sign flipped. Which one you want
      depends on which end of the part you are asking about.
    """

    anchors = measured["anchors"][body]
    peak = measured["bodies"][body]["internal"]["at_peak_force"] or {
        "force_n": [0.0, 0.0, 0.0], "torque_n_mm": [0.0, 0.0, 0.0]}
    supports = [
        {"name": f"held at {row['joint']}",
         "region": {"sphere": {"centre_mm": row["anchor_mm"],
                               "radius_mm": radius_mm}}}
        for row in anchors["held_at"]
    ] or [{"name": "held (no joint on this body -- edit me)",
           "region": {"sphere": {"centre_mm": anchors["centre_of_mass_mm"],
                                 "radius_mm": radius_mm}}}]
    loads = []
    for row in anchors["children_at"]:
        child = measured["bodies"].get(row["body"], {}).get("internal", {})
        snapshot = child.get("at_peak_force")
        if not snapshot:
            continue
        loads.append({
            "name": f"{row['body']} through {row['joint']}",
            "region": {"sphere": {"centre_mm": row["anchor_mm"],
                                  "radius_mm": radius_mm}},
            "force_n": snapshot["force_n"],
            "torque_n_mm": snapshot["torque_n_mm"],
        })
    if not loads:
        loads.append({
            "name": "the parent's reaction (no children on this body)",
            "region": {"sphere": {"centre_mm": anchors["centre_of_mass_mm"],
                                  "radius_mm": radius_mm}},
            "force_n": peak["force_n"],
            "torque_n_mm": peak["torque_n_mm"],
        })
    return {
        "schema": LOAD_CASE_SCHEMA,
        "material": None,
        "supports": supports,
        "loads": loads,
        "note": (f"Measured from a rollout, worst frame "
                 f"{measured['bodies'][body]['internal']['peak_force_frame']}. "
                 "Declare a material and check which end you meant to hold."),
    }


def measure(model_path: Path, trace_path: Path, *, bodies: Sequence[str] = (),
            radius_mm: float = 2.0) -> dict[str, Any]:
    trace = read_trace(trace_path)
    measured = replay(model_path, trace)
    chosen = list(bodies) or sorted(measured["bodies"])
    unknown = [name for name in chosen if name not in measured["bodies"]]
    if unknown:
        raise RolloutLoadError(
            f"The trace plays no component named {', '.join(unknown)}. It "
            f"plays: {', '.join(sorted(measured['bodies']))}."
        )
    warnings: list[str] = []
    if not measured["replay"]["reproduced"]:
        warnings.append(
            f"The replay drifted {measured['replay']['worst_position_error_mm']:.4g} "
            f"mm from the trace by frame {measured['replay']['worst_frame']}, "
            "so these wrenches belong to a nearby motion rather than to the "
            "one that was recorded. The usual cause is a trace sampled at "
            "fewer frames a second than the policy acted at, which holds only "
            "some of the actions."
        )
    return {
        "schema": REPORT_SCHEMA,
        "input": {
            "model": str(model_path),
            "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
            "trace": str(trace_path),
            "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            "simulation_output": trace.get("simulation_output"),
            "policy": (trace.get("policy") or {}).get("policy_output"),
        },
        "replay": measured["replay"],
        "frames": measured["frames"],
        "frame_interval_s": measured["frame_interval_s"],
        "steps_per_frame": measured["steps_per_frame"],
        "bodies": {name: {**measured["bodies"][name], **measured["anchors"][name]}
                   for name in chosen},
        "load_cases": {name: load_case_fragment(name, measured, radius_mm=radius_mm)
                       for name in chosen},
        "warnings": warnings,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "mujoco": getattr(_mujoco(), "__version__", "unknown"),
        },
        "cadex_importable": _cadex_importable(),
    }


def _cadex_importable() -> bool:
    try:
        import CadexDynamics  # noqa: F401
    except Exception:
        return False
    return True


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="loads_from_rollout.py",
        description="The worst wrench each body saw across a published rollout.")
    parser.add_argument("model", type=Path, help="the exported MJCF")
    parser.add_argument("--trace", type=Path, required=True,
                        help=f"a {TRACE_SCHEMA} JSON file")
    parser.add_argument("--body", action="append", default=[],
                        help="restrict to these components (repeatable)")
    parser.add_argument("--radius-mm", type=float, default=2.0,
                        help="how wide the emitted regions are around an anchor")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--emit-load-case", type=Path, default=None,
                        help="write one body's load-case fragment here")
    options = parser.parse_args(list(argv[1:]))

    try:
        report = measure(options.model, options.trace, bodies=options.body,
                         radius_mm=options.radius_mm)
    except RolloutLoadError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for warning in report["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    if options.emit_load_case:
        if len(options.body) != 1:
            print("refused: --emit-load-case writes one body's fragment, so "
                  "name exactly one --body.", file=sys.stderr)
            return 2
        options.emit_load_case.write_text(
            json.dumps(report["load_cases"][options.body[0]], indent=2,
                       sort_keys=True), encoding="utf-8")
    if options.out:
        options.out.write_text(json.dumps(report, indent=2, sort_keys=True),
                               encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
