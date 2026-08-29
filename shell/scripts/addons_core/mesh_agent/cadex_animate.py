# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Bake an accepted assembly simulation into Blender playback (cadex ADR-050).

``assembly.simulation(...)`` retains a native kinematics trace as a program
artifact: per frame, a nominal time and every component's solved pose. This
module turns that into F-Curves on the component instances
``cadex_hydrate`` created, so the mechanism moves when you press play and
nothing runs per frame.

A sibling of ``cadex_hydrate`` rather than part of it, deliberately: a
malformed or missing trace must never cost you the geometry. Hydration
happens first and stands alone; this runs after and may fail on its own.

The pure half -- :func:`read_trace`, :func:`frame_of`,
:func:`curves_for_component` -- imports no ``bpy`` and is unit-testable
without Blender. :func:`apply` is the only entry point that touches the
scene.

Five things about this conversion are easy to get wrong, and all five are
silent:

- **Time, not frame index.** The solver's step (``time_step_s``) and the
  playback rate (``frames_per_second``) are independent. Keying on the
  frame index plays a 0.01 s / 30 fps simulation at 3.3x slow motion.
- **Quaternion order.** The trace is xyzw; Blender is wxyz.
- **Hemisphere continuity.** The solver returns ``q`` and ``-q`` for the
  same orientation, and the engine normalizes without de-flipping. Keyed
  raw, a linkage swings through a full rotation between two adjacent
  samples and it reads as a solver bug.
- **Rotation mode.** The default ``'XYZ'`` leaves the quaternion channels
  inert; nothing errors, nothing moves.
- **Slotted actions.** In this Blender ``Action`` has **no ``fcurves``
  attribute at all** -- it is not a legacy collection that quietly does the
  wrong thing, it raises ``AttributeError``. Curves live at
  ``action.layers[].strips[].channelbag(slot).fcurves``.
  ``fcurve_ensure_for_datablock`` creates the layer, strip and slot for you,
  and requires the action to be assigned to the object first.
"""

import hashlib
import json
import math

TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
SIMULATION_KIND = "assembly_simulation_json"

#: On a baked action: the SHA-256 of the trace it was baked from, so an
#: unchanged simulation is not re-baked on every accepted revision.
BAKED_SHA_PROP = "cadex_trace_sha"
ACTION_PREFIX = "CadexSim"

#: On the scene while a simulation is baked: ``{fps, frames, components,
#: seconds}``. The Simulation panel polls on its presence, so a model with
#: no simulation sees the parameters editor exactly as it was.
SCENE_FLAG = "cadex_simulation"

#: On the scene while a *policy rollout* is baked: ``{channels, frames,
#: values}``, where ``values`` is flat and row-major over frames. Only a
#: rollout trace carries ``actuator_channels``, so a kinematics or dynamics
#: simulation leaves this absent and the Actuators panel does not draw.
#:
#: Separate from ``SCENE_FLAG`` rather than folded into it because the two
#: have different lifetimes in the only way that matters: every simulation
#: sets the flag, and only one kind of simulation sets this.
COMMANDS_FLAG = "cadex_actuator_commands"

#: ``BEZT_IPO_LIN`` (DNA_curve_enums.h). Poses are already sampled at the
#: solver's step; Bezier handles between them would invent motion.
LINEAR = 1

#: location xyz + rotation_quaternion wxyz.
CHANNELS = (("location", 3), ("rotation_quaternion", 4))


# -- the pure half: no bpy, no scene ----------------------------------------

def read_trace(path):
    """Read one simulation trace. Returns ``(trace, sha256_of_bytes)``.

    The hash is of the file's bytes rather than anything derived, so it is
    the same identity the engine hashed into ``artifact_sha256``.
    """

    with open(path, "rb") as handle:
        blob = handle.read()
    trace = json.loads(blob.decode("utf-8"))
    if trace.get("schema") != TRACE_SCHEMA:
        raise ValueError("{:s} is not a {:s} trace".format(str(path),
                                                           TRACE_SCHEMA))
    return trace, hashlib.sha256(blob).hexdigest()


def frame_of(time_s, start_s, fps):
    """The Blender frame for a nominal trace time. Fractional on purpose.

    Frame 1 is the start of the simulation, and a sample lands wherever its
    *time* puts it -- which is not generally an integer frame, and must not
    be rounded to one: at 0.05 s and 30 fps every third sample would land
    on the same frame and two of them would be discarded.
    """

    return 1.0 + (float(time_s) - float(start_s)) * float(fps)


def _wxyz(rotation_xyzw):
    """Trace order (xyzw) to Blender order (wxyz)."""

    x, y, z, w = (float(value) for value in rotation_xyzw)
    return [w, x, y, z]


def _continuous(quaternion, previous):
    """Flip ``quaternion`` into ``previous``'s hemisphere when it crossed.

    q and -q are the same orientation; the solver may return either, and
    _compact_placement normalizes without de-flipping. Interpolating across
    a flip takes the long way round the sphere.
    """

    if previous is None:
        return quaternion
    dot = sum(a * b for a, b in zip(quaternion, previous))
    if dot < 0.0:
        return [-value for value in quaternion]
    return quaternion


def solver_frames(frames):
    """Just the solved frames, in order.

    Frame 0 is ``frame_kind: "input"`` with no time: it is the pose the
    components already sit at, and it has nowhere to be keyed.
    """

    return [frame for frame in frames
            if frame.get("frame_kind") != "input"
            and frame.get("nominal_time_s") is not None]


def curves_for_component(frames, name, start_s, fps):
    """F-Curve samples for one component.

    Returns ``{(data_path, array_index): [frame, value, frame, value, ...]}``
    -- flat and interleaved, which is exactly what ``foreach_set("co", ...)``
    consumes, so nothing reshapes it later.
    """

    curves = {}
    for channel, count in CHANNELS:
        for index in range(count):
            curves[(channel, index)] = []

    previous = None
    for frame in solver_frames(frames):
        pose = (frame.get("component_placements") or {}).get(name)
        if pose is None:
            continue
        at = frame_of(frame["nominal_time_s"], start_s, fps)
        for index, value in enumerate(pose["position_mm"]):
            # 1 BU = 1 mm (modes.py), and both sides are Z-up
            # right-handed: no conversion, no scale.
            curves[("location", index)].extend((at, float(value)))
        quaternion = _continuous(_wxyz(pose["rotation_xyzw"]), previous)
        previous = quaternion
        for index, value in enumerate(quaternion):
            curves[("rotation_quaternion", index)].extend((at, value))
    return curves


def commands_table(trace, start_s, fps):
    """The policy's own outputs, indexed by Blender frame. None if absent.

    Returns ``{"channels": [...], "frames": [f, ...], "values": [flat]}``
    with ``values`` row-major over frames -- one row per frame that carries
    a command, ``len(channels)`` floats wide. Flat because that is what an
    IDProperty stores without turning 600 rows into 600 dictionaries.

    ``frames`` is stored rather than derived even though the mapping is
    exactly ``1 + k`` today: ``frame_interval_s`` is ``1 / frames_per_second``
    by construction in the engine, so the arithmetic is currently an
    identity, and a panel that silently depended on it would read the wrong
    row the first time that stopped being true rather than draw nothing.

    Frames before the first command -- the untimed ``input`` frame and the
    reset pose behind it -- are simply not rows. A policy has decided
    nothing yet there, and a row of zeros would claim it decided zero.
    """

    channels = trace.get("actuator_channels")
    if not channels:
        return None
    width = len(channels)
    frames = []
    values = []
    for frame in solver_frames(trace.get("frames") or []):
        commands = frame.get("actuator_commands")
        if not commands or len(commands) != width:
            continue
        frames.append(frame_of(frame["nominal_time_s"], start_s, fps))
        values.extend(float(value) for value in commands)
    if not frames:
        return None
    return {
        "channels": [
            {
                "label": str(channel.get("joint") or channel.get("actuator")),
                "unit": str(channel.get("unit") or ""),
                "low": float(channel.get("low") or 0.0),
                "high": float(channel.get("high") or 0.0),
            }
            for channel in channels
        ],
        "frames": frames,
        "values": values,
    }


def commands_at(table, frame):
    """The command row in effect at Blender frame ``frame``, or None.

    The row *at or before* the frame, which is what a zero-order hold is: a
    command is held until the next control step replaces it, so the value
    between two frames is the earlier one rather than an interpolation of
    the two. The viewport interpolates poses because a pose is a continuous
    quantity sampled discretely; a command is not, and drawing it as though
    it were would invent decisions the policy never made.
    """

    if not table:
        return None
    frames = table["frames"]
    width = len(table["channels"])
    values = table["values"]
    index = -1
    for position, at in enumerate(frames):
        if float(at) > float(frame):
            break
        index = position
    if index < 0:
        return None
    row = values[index * width:(index + 1) * width]
    return [float(value) for value in row] if len(row) == width else None


def frame_range(trace):
    """``(frame_start, frame_end)`` covering the whole run."""

    parameters = trace.get("parameters") or {}
    start = float(parameters.get("start_time_s") or 0.0)
    end = float(parameters.get("end_time_s") or 0.0)
    fps = int(parameters.get("frames_per_second") or 30)
    return 1, int(math.ceil(max(0.0, end - start) * fps)) + 1


# -- the bpy half -----------------------------------------------------------

def _simulation_entries(display_map):
    return sorted(
        name for name, entry in (display_map or {}).items()
        if (entry or {}).get("artifact_kind") == SIMULATION_KIND
        and (entry or {}).get("artifact_path")
    )


def _cadex_objects():
    from . import cadex_hydrate
    return cadex_hydrate._cadex_objects(cadex_hydrate._model_collection())


def fcurves_of(obj):
    """The F-Curves driving ``obj``, or [].

    Slotted-action navigation in one place: ``Action`` has no ``fcurves``
    attribute in this Blender, so every caller would otherwise have to walk
    layer -> strip -> channelbag itself.
    """

    animation = getattr(obj, "animation_data", None)
    action = getattr(animation, "action", None)
    if action is None:
        return []
    slot = getattr(animation, "action_slot", None)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            try:
                channelbag = strip.channelbag(slot)
            except Exception:
                continue
            if channelbag is not None:
                curves.extend(channelbag.fcurves)
    return curves


def _clear(objects):
    """Drop every baked action, and the actions themselves.

    Mirrors ``_replace_data``'s orphan-mesh removal: replacement is always
    clear-then-bake, never edit-in-place, so a shorter simulation cannot
    leave the tail of a longer one behind.
    """

    import bpy
    orphans = []
    for obj in objects:
        animation = obj.animation_data
        if animation is None:
            continue
        action = animation.action
        if action is not None and BAKED_SHA_PROP in action:
            orphans.append(action)
        obj.animation_data_clear()
    removed = 0
    for action in orphans:
        if action.users == 0:
            bpy.data.actions.remove(action)
            removed += 1
    return removed


def _forget(scene):
    """Drop the panels' flags. A model without a simulation shows neither."""

    for flag in (SCENE_FLAG, COMMANDS_FLAG):
        if flag in scene:
            del scene[flag]


def _bake_object(obj, curves, sha):
    import bpy
    # The default 'XYZ' leaves the quaternion channels inert.
    obj.rotation_mode = 'QUATERNION'
    if obj.animation_data is None:
        obj.animation_data_create()
    action = bpy.data.actions.new("{:s}{:s}".format(ACTION_PREFIX, obj.name))
    # Assign before ensuring curves: fcurve_ensure_for_datablock requires
    # the action to already belong to the datablock.
    obj.animation_data.action = action
    action[BAKED_SHA_PROP] = sha

    keyframes = 0
    for (data_path, index), flat in sorted(curves.items()):
        if not flat:
            continue
        count = len(flat) // 2
        fcurve = action.fcurve_ensure_for_datablock(obj, data_path, index=index)
        points = fcurve.keyframe_points
        points.add(count)
        # Bulk, never keyframe_insert: the engine's ceiling is 10 000
        # frames x 7 channels, and keyframe_insert is a Python call each.
        points.foreach_set("co", flat)
        points.foreach_set("interpolation", [LINEAR] * count)
        fcurve.update()
        keyframes += count
    return keyframes


def apply(payload):
    """Bake the accepted response's simulation, if it has one.

    Returns a report dict. Never raises for the ordinary cases -- a model
    with no simulation, or one that just lost its simulation, is not an
    error, it is the common case.
    """

    import bpy
    from . import cadex_hydrate

    display_map = payload.get("display") or {}
    names = _simulation_entries(display_map)
    objects = _cadex_objects()
    scene = bpy.context.scene

    if not names:
        _forget(scene)
        return {"baked": False, "cleared": _clear(objects)}

    if len(names) > 1:
        # Refused rather than silently picking one: two simulations mean two
        # timelines, and a scene has one.
        _forget(scene)
        return {
            "baked": False,
            "cleared": _clear(objects),
            "message": (
                "This script declares {:d} simulations ({:s}); a scene has "
                "one timeline, so none was baked. Keep one simulation "
                "output per script.".format(len(names), ", ".join(names))
            ),
        }

    entry = display_map[names[0]]
    trace, sha = read_trace(entry["artifact_path"])

    by_output = {}
    for obj in objects:
        output = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "")
        if output and not obj.name.endswith(cadex_hydrate.EDGE_SUFFIX):
            by_output[output] = obj

    component_names = [name for name in (trace.get("component_outputs") or [])
                       if name in by_output]

    # Unchanged trace, already baked: the poses cannot have moved, so the
    # curves cannot have either.
    if component_names and all(
        (by_output[name].animation_data is not None
         and by_output[name].animation_data.action is not None
         and by_output[name].animation_data.action.get(BAKED_SHA_PROP) == sha)
        for name in component_names
    ):
        return {"baked": False, "unchanged": True, "sha": sha,
                "components": len(component_names)}

    _clear(objects)

    parameters = trace.get("parameters") or {}
    start_s = float(parameters.get("start_time_s") or 0.0)
    fps = int(parameters.get("frames_per_second") or 30)
    frames = trace.get("frames") or []

    keyframes = 0
    for name in component_names:
        curves = curves_for_component(frames, name, start_s, fps)
        keyframes += _bake_object(by_output[name], curves, sha)

    scene.render.fps = max(1, fps)
    scene.frame_start, scene.frame_end = frame_range(trace)
    scene.frame_current = scene.frame_start
    scene[SCENE_FLAG] = {
        "fps": fps,
        "frames": len(solver_frames(frames)),
        "components": len(component_names),
        "seconds": float(parameters.get("end_time_s") or 0.0) - start_s,
    }

    # Set or dropped on every bake, never left behind: a rollout replaced by
    # an ordinary dynamics run must not keep showing the old policy's
    # commands against the new run's timeline.
    table = commands_table(trace, start_s, fps)
    if table is None:
        if COMMANDS_FLAG in scene:
            del scene[COMMANDS_FLAG]
    else:
        scene[COMMANDS_FLAG] = table

    return {
        "baked": True,
        "sha": sha,
        "components": len(component_names),
        "frames": len(solver_frames(frames)),
        "keyframes": keyframes,
        "fps": fps,
        "frame_end": scene.frame_end,
        "actuators": 0 if table is None else len(table["channels"]),
    }
