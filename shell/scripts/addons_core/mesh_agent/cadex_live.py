# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live mode: a running mechanism you can push (ADR-109).

The shell half. It speaks three ops -- ``live_open``, ``live_step``,
``live_close`` -- and imports ``bpy``, three standard-library modules and
the client. **No mujoco and no CadexDynamics**, which is not a style rule but a
test (``test_the_shell_never_learns_about_mujoco``): physics is engine-side,
permanently, and what reaches here is poses.

**Why it is not a playback.** A recorded rollout is six seconds with one
drawn push. You cannot shove it from the other side, cannot shove it harder,
and cannot shove it twice -- and ADR-107 records what reading such a
recording through summary statistics cost twice in one day. Live mode makes
the machine a thing in the room.

**The shell owns the clock, and the worker thread is where that lives.**
``live_step`` grants N control steps and returns the N frames they made; the
engine's episode blocks for that credit rather than sleeping against a clock
of its own. So the pacing is here: :class:`_Session` runs one request at a
time on a daemon thread, asking for however many control steps of *wall
time* have passed since the last one. Pause is then simply not asking.

**One request in flight, one small queue**, exactly like ``cadex_backend``'s
drag pump: a stall in the engine -- a ``live_step`` queued behind an
in-flight rebuild, which is a read op doing what read ops do -- costs frames
and never blocks the UI. The timer draws the **newest** frame and drops the
rest, which is what a real-time view of a real-time simulation means.

**Poses are written directly**, not keyframed. ``cadex_animate`` bakes
F-Curves for a recorded trace, and a live session writing keys would fight
them; on stop, ``scene.frame_current`` is re-set so the baked action
reasserts the recorded pose and nothing is left displaced.

**A session you can analyse** (ADR-110). Three things, and they are one
thing:

- **Calm mode.** ``live_open`` takes ``variation``, and off is the episode
  ``evaluate_episode`` has always had for a caller that passes no seed: one
  nominal machine, at the pose the solve found, with nothing pushing it. The
  checkbox defaults **off** here — a baseline already falling over under
  four drawn forces is an instrument you cannot read a fifth force off.
- **The arrow is drawn from what the engine measured**, the ``xfrc_applied``
  a frame carries back, and never from the push this module asked for. An
  intention keeps drawing after the window lapses, after a clamp and after a
  refusal; ADR-103 and ADR-107 are both what that costs.
- **Hold to push.** The drag re-sends a short push every tick rather than
  arming one impulse on release, so the force lasts exactly as long as the
  mouse is down. The compass buttons stay one-shot impulses beside it,
  because a drag can never be repeated exactly and an ADR needs a number.

**These are the add-on's first draw handlers.** The rule that keeps the
headless gate green: ``gpu.shader.from_builtin`` raises *"requires the gpu
module to be initialized"* under ``--background``, so the shader is fetched
**inside** the callback and never at module scope. Handles are module-level
and removed in ``stop()`` *and* ``unregister()`` — a leaked handler draws
forever and raises on the next add-on reload.
"""

import math
import queue
import threading
import time

import bpy
from bpy.types import Operator, Panel

#: Timer period. 30 Hz is the display rate; the simulation runs at the task's
#: own control rate underneath and this only decides how often it is drawn.
TICK_SECONDS = 1.0 / 30.0

#: The most control steps one request may ask for. Caps the catch-up burst
#: after a stall, and matches what the engine will accept.
MAX_STEPS_PER_REQUEST = 32

#: How far behind real time the clock may fall before it is simply moved
#: forward. Past this, catching up second-for-second would play the whole
#: stall back at high speed, which is not what "live" means -- so the time
#: is dropped and the simulation resumes at now.
MAX_CATCHUP_SECONDS = 0.5

#: Frames held between the worker thread and the timer. Only the newest is
#: ever drawn, so this exists to bound memory rather than to buffer.
MAX_QUEUED_FRAMES = 512

#: The default shove, in newtons. mg-legs' task declares 0.15-0.90 N and
#: survives about half of it, so this is "a real push" for the machine that
#: motivated live mode -- an honest starting point rather than a round one.
DEFAULT_NEWTONS = 0.75

#: How long a live shove lasts. The same 0.12 s the task's own disturbances
#: use, so a pushed recovery and a drawn one are the same kind of event.
DEFAULT_DURATION_S = 0.12

#: How long each re-sent slice of a *held* push lasts. Longer than one 33 ms
#: tick plus a round trip, so the force cannot lapse between updates and the
#: machine feels a continuous shove; short enough that letting go stops it
#: within a frame or two rather than leaving it coasting. The engine needs
#: nothing for this: ``_arm_push`` replaces the pending push and resets its
#: window, so re-sending IS holding.
HELD_PUSH_SECONDS = 0.15

#: Millimetres of arrow per newton. 0.75 N — the default shove — draws about
#: 112 mm against a 300 mm machine: unmistakable without swallowing it.
DEFAULT_FORCE_SCALE_MM_N = 150.0

#: How long the last force seen keeps being drawn, fading over the tail. A
#: 0.12 s impulse at 30 Hz is four frames, which is a blink; this is what
#: makes a compass push something you can actually look at.
FORCE_HOLD_SECONDS = 0.6

#: Fraction of the shaft the four head segments run back along.
ARROW_HEAD_FRACTION = 0.2

#: The arrow, and the label beside it. Warm against a grey viewport, and the
#: same colour in both, because they are one annotation.
FORCE_COLOR = (1.0, 0.42, 0.12)

#: The eight compass buttons, as (label, degrees about **world +X**). The
#: engine has no concept of a machine's forward (ADR-107) and neither does
#: this: the labels are world directions and say so.
COMPASS = (
    ("+X", 0.0), ("+X+Y", 45.0), ("+Y", 90.0), ("-X+Y", 135.0),
    ("-X", 180.0), ("-X-Y", 225.0), ("-Y", 270.0), ("+X-Y", 315.0),
)


# ---------------------------------------------------------------------------
# The session
# ---------------------------------------------------------------------------

#: One live session per Blender, for the reason there is one timeline
#: (ADR-062): two running simulations would need two of something the
#: product deliberately has one of.
_session = None


class _Session:
    """One running episode: a worker thread, a frame queue, and the poses."""

    def __init__(self, project_root, opened, objects):
        self.project_root = project_root
        self.control_hz = max(1, int(opened.get("control_hz") or 1))
        self.components = [str(name) for name in opened.get("components") or ()]
        self.channels = list(opened.get("actuator_channels") or ())
        self.episode_seconds = float(opened.get("episode_seconds") or 0.0)
        self.objects = objects

        self.paused = False
        self.step = 0
        self.time_s = 0.0
        self.terminated = False
        self.termination = ""
        self.reset_count = 0
        self.commands = None
        self.last_push = ""
        self.dragging = ""
        self.error = ""

        #: The most recent **non-empty** ``applied_forces`` any frame carried,
        #: and when it arrived. Written by the pump, read by the draw
        #: handlers; a whole dict is swapped in at once rather than mutated,
        #: so the drawing side never sees half of one.
        self.forces = {}
        self.forces_seen = 0.0

        self._frames = queue.SimpleQueue()
        self._queued = 0
        self._pending_push = None
        self._held_push = None
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(
            target=self._pump, name="cadex-live-pump", daemon=True)
        self._thread.start()

    # -- the request side, on its own thread ----------------------------

    def _pump(self):
        from . import cadex_backend

        clock = time.monotonic()
        while self._running:
            if self.paused:
                # Not asking IS the pause, and the clock moves with it so
                # resuming does not owe the engine the paused seconds.
                clock = time.monotonic()
                time.sleep(0.05)
                continue
            now = time.monotonic()
            if now - clock > MAX_CATCHUP_SECONDS:
                # A stall -- a live_step queued behind a rebuild, a slow
                # redraw. Playing it back at speed is not "live", so the
                # time is dropped rather than owed.
                clock = now - MAX_CATCHUP_SECONDS
            owed = int((now - clock) * self.control_hz)
            if owed < 1:
                time.sleep(TICK_SECONDS / 3.0)
                continue
            steps = min(owed, MAX_STEPS_PER_REQUEST)
            clock += steps / float(self.control_hz)

            args = {"steps": steps}
            with self._lock:
                if self._held_push is not None:
                    # Re-sent every tick for as long as the mouse is down.
                    # Not consumed: letting go is what stops it.
                    args["push"] = dict(self._held_push)
                elif self._pending_push is not None:
                    args["push"] = self._pending_push
                    self._pending_push = None
            try:
                answer = cadex_backend.live_step(self.project_root, args)
            except Exception as exc:  # a dead engine must not kill the thread
                self.error = str(exc)
                self._running = False
                return
            if answer.get("ok") is not True or answer.get("live") is not True:
                self.error = str(answer.get("reason")
                                 or answer.get("error")
                                 or "the live session ended")
                self._running = False
                return
            self.step = int(answer.get("step") or 0)
            self.time_s = float(answer.get("time_s") or 0.0)
            self.terminated = bool(answer.get("terminated"))
            self.termination = str(answer.get("termination") or "")
            self.reset_count = int(answer.get("reset_count") or 0)
            for frame in answer.get("frames") or ():
                # **Every** frame, not just the newest one the timer will
                # draw poses from: a 0.12 s impulse is twelve frames and a
                # catch-up batch is thirty-two, so scanning only the last
                # would miss a short push entirely.
                applied = frame.get("applied_forces")
                if applied:
                    self.forces = applied
                    self.forces_seen = time.monotonic()
                if self._queued >= MAX_QUEUED_FRAMES:
                    try:
                        self._frames.get_nowait()
                        self._queued -= 1
                    except queue.Empty:
                        pass
                self._frames.put(frame)
                self._queued += 1

    # -- the draw side, on the timer ------------------------------------

    def newest_frame(self):
        """Drain the queue and hand back the last frame, or ``None``.

        The newest and not the next: the engine is producing at real time
        and this draws at 30 Hz, so the frames in between are not a backlog
        to work through -- they are the ones a 30 Hz eye never sees.
        """

        frame = None
        while True:
            try:
                frame = self._frames.get_nowait()
                self._queued -= 1
            except queue.Empty:
                break
        return frame

    def arm_push(self, newtons, azimuth_rad, body, duration_s=None):
        """One impulse, on the next request. The compass buttons' gesture."""

        with self._lock:
            self._pending_push = {
                "newtons": float(newtons),
                "azimuth_rad": float(azimuth_rad),
                "duration_s": float(duration_s or DEFAULT_DURATION_S),
                "body": str(body),
            }
        self.last_push = "{:.2f} N at {:.0f} deg on {:s}".format(
            float(newtons), math.degrees(float(azimuth_rad)) % 360.0,
            str(body))

    def hold_push(self, newtons, azimuth_rad, body):
        """Push until told to stop. The drag's gesture.

        ``last_push`` is deliberately **not** written: a drag changes its
        vector every mouse move, and a readout that said "last push" while
        reporting a number from 16 ms ago would be noise. It gets its own
        line instead, which says it is still happening.
        """

        with self._lock:
            self._held_push = {
                "newtons": float(newtons),
                "azimuth_rad": float(azimuth_rad),
                "duration_s": HELD_PUSH_SECONDS,
                "body": str(body),
            }
        self.dragging = "{:.2f} N at {:.0f} deg on {:s}".format(
            float(newtons), math.degrees(float(azimuth_rad)) % 360.0,
            str(body))

    def release_push(self):
        """Let go. The last slice lapses on its own within HELD_PUSH_SECONDS."""

        with self._lock:
            self._held_push = None
        self.dragging = ""

    def forces_to_draw(self):
        """The last measured forces and the alpha to draw them at.

        Held for :data:`FORCE_HOLD_SECONDS` past the frame that carried them
        and faded over the tail, because the thing being drawn is often
        shorter than the eye's dwell: a 0.12 s impulse at a 30 Hz display is
        four frames.
        """

        forces = self.forces
        if not forces:
            return {}, 0.0
        age = time.monotonic() - self.forces_seen
        if age >= FORCE_HOLD_SECONDS:
            return {}, 0.0
        solid = FORCE_HOLD_SECONDS * 0.5
        if age <= solid:
            return forces, 1.0
        return forces, max(0.0, 1.0 - (age - solid) / (FORCE_HOLD_SECONDS - solid))

    def close(self):
        self._running = False
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)


def session():
    return _session


def is_running():
    return _session is not None and _session._running


# ---------------------------------------------------------------------------
# Start, stop, and the guards
# ---------------------------------------------------------------------------

def _objects_by_output():
    from . import cadex_hydrate
    found = {}
    for obj in cadex_hydrate._cadex_objects(cadex_hydrate._model_collection()):
        output = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "")
        if output and not obj.name.endswith(cadex_hydrate.EDGE_SUFFIX):
            found[output] = obj
    return found


def start(context, seed=None):
    """Open a session on the accepted rollout. Returns ``(ok, message)``."""

    global _session
    if is_running():
        return False, "A live session is already running"
    if _session is not None:
        # A session whose pump died -- a dead engine, a refused step. Its
        # worker is gone but the engine may still hold the worker process,
        # so tear it down properly before opening another.
        stop(context)
    if context.screen is not None and context.screen.is_animation_playing:
        # Playback drives the same objects from baked F-Curves. Two writers
        # is a fight nobody wins, and the one that loses is silent.
        return False, ("Stop playback first — the timeline and a live "
                       "session drive the same objects")

    from . import cadex_backend
    root = cadex_backend.project_root(context.scene)
    # Always sent, never inferred: the op defaults to playing the task as the
    # bundle declares it, and the panel's checkbox defaults off, so exactly
    # one of the two is the default a user sees and it is the one they can
    # see (ADR-110).
    args = {"output": "",
            "variation": bool(getattr(context.scene,
                                      "cadex_live_variation", False))}
    if seed is not None:
        args["seed"] = int(seed)
    try:
        opened = cadex_backend.live_open(root, args)
    except Exception as exc:
        return False, str(exc)
    if opened.get("ok") is not True:
        return False, str(opened.get("error") or "the engine refused")
    if opened.get("live") is not True:
        return False, str(opened.get("reason") or "nothing to play")

    objects = _objects_by_output()
    missing = [name for name in opened.get("components") or ()
               if name not in objects]
    if missing:
        # Said rather than drawn as a partial mechanism: a component with no
        # object would simply stop moving, which reads as a physics result.
        cadex_backend.live_close(root)
        return False, ("The scene has no object for {:d} of the "
                       "mechanism's components ({:s}…)".format(
                           len(missing), missing[0]))

    _session = _Session(root, opened, objects)
    _ensure_timer()
    _add_draw_handlers()
    _tag_redraw()
    return True, "Live session running"


def stop(context):
    """Close the session and put the recorded pose back."""

    global _session
    live, _session = _session, None
    _remove_draw_handlers()
    if live is None:
        return False, "No live session"
    live.close()
    from . import cadex_backend
    try:
        cadex_backend.live_close(live.project_root)
    except Exception:
        pass  # the session is over either way; a failed close is the engine's

    # Re-set the frame so the baked action reasserts the recorded pose.
    # Without this every component is left wherever the last live frame put
    # it, which looks exactly like a corrupted bake.
    scene = context.scene if context is not None else bpy.context.scene
    if scene is not None:
        scene.frame_set(scene.frame_current)
    _tag_redraw()
    return True, "Live session stopped"


def _apply(frame, live):
    placements = frame.get("component_placements") or {}
    for name, pose in placements.items():
        obj = live.objects.get(name)
        if obj is None:
            continue
        position = pose.get("position_mm") or (0.0, 0.0, 0.0)
        rotation = pose.get("rotation_xyzw") or (0.0, 0.0, 0.0, 1.0)
        obj.location = (float(position[0]), float(position[1]),
                        float(position[2]))
        obj.rotation_mode = 'QUATERNION'
        # xyzw on the wire, wxyz in Blender -- the same reorder
        # ``cadex_animate._wxyz`` performs on a baked trace.
        obj.rotation_quaternion = (float(rotation[3]), float(rotation[0]),
                                   float(rotation[1]), float(rotation[2]))
    commands = frame.get("actuator_commands")
    if commands is not None:
        live.commands = [float(value) for value in commands]


def _tick():
    live = _session
    if live is None:
        return None
    if not live._running:
        # The pump stopped -- a dead engine, or a refused step. Leave the
        # session in place so the panel can show why, and stop the timer.
        _tag_redraw()
        return None
    frame = live.newest_frame()
    if frame is not None:
        _apply(frame, live)
    _tag_redraw()
    return TICK_SECONDS


def _ensure_timer():
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=TICK_SECONDS)


def _tag_redraw():
    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return
    for window in windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type in {'VIEW_3D', 'CADEX_LIVE'}:
                area.tag_redraw()


# ---------------------------------------------------------------------------
# The force overlay
# ---------------------------------------------------------------------------

#: The add-on's first draw handlers (ADR-110). Module-level because that is
#: what ``draw_handler_remove`` needs, and removed in both ``stop()`` and
#: ``unregister()``: a leaked handler keeps drawing against a session that is
#: gone and raises on the next add-on reload.
_draw_3d_handle = None
_draw_2d_handle = None

#: Fetched once, on the first draw, and never at module scope:
#: ``gpu.shader.from_builtin`` raises "requires the gpu module to be
#: initialized" under ``--background``, so a module-scope shader would break
#: every headless gate run. ``(shader, is_polyline)``.
_shader = None


def _line_shader():
    global _shader

    if _shader is None:
        import gpu

        for name in ('POLYLINE_UNIFORM_COLOR', 'UNIFORM_COLOR'):
            try:
                # The polyline one first: it is the only one that honours a
                # line width, and a one-pixel force arrow is a scratch.
                _shader = (gpu.shader.from_builtin(name),
                           name.startswith('POLYLINE'))
                break
            except Exception:
                continue
    return _shader or (None, False)


def _arrow(at_mm, newtons, scale):
    """One arrow, as ``(line segment endpoints, tip)`` in world millimetres.

    Hydrated objects are placed by ``matrix_world`` in raw millimetres 1:1
    (``cadex_hydrate``), so ``at_mm`` off the wire is already a Blender world
    coordinate and there is no conversion here to get wrong.
    """

    fx, fy, fz = (float(newtons[0]), float(newtons[1]), float(newtons[2]))
    magnitude = math.sqrt(fx * fx + fy * fy + fz * fz)
    if magnitude <= 0.0:
        return [], None, 0.0
    length = magnitude * float(scale)
    unit = (fx / magnitude, fy / magnitude, fz / magnitude)
    base = (float(at_mm[0]), float(at_mm[1]), float(at_mm[2]))
    tip = tuple(base[axis] + unit[axis] * length for axis in range(3))

    # Two directions across the shaft, from whichever world axis is least
    # parallel to it, so the head reads from any orbit.
    other = (0.0, 0.0, 1.0) if abs(unit[2]) < 0.9 else (1.0, 0.0, 0.0)
    across = _unit(_cross(unit, other))
    up = _unit(_cross(unit, across))

    back = length * ARROW_HEAD_FRACTION
    segments = [base, tip]
    for sx, sy in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)):
        segments.append(tip)
        segments.append(tuple(
            tip[axis]
            - unit[axis] * back
            + (across[axis] * sx + up[axis] * sy) * back * 0.5
            for axis in range(3)
        ))
    return segments, tip, magnitude


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length <= 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _force_scale(scene):
    return float(getattr(scene, "cadex_live_force_scale",
                         DEFAULT_FORCE_SCALE_MM_N))


def _drawable():
    """``(entries, alpha, scale)`` for this redraw, or ``None``."""

    live = _session
    if live is None:
        return None
    forces, alpha = live.forces_to_draw()
    if not forces or alpha <= 0.0:
        return None
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return None
    return forces, alpha, _force_scale(scene)


def _draw_forces_3d():
    """The arrows themselves, in the viewport's own space."""

    drawable = _drawable()
    if drawable is None:
        return
    forces, alpha, scale = drawable

    segments = []
    for entry in forces.values():
        made, _tip, _magnitude = _arrow(
            entry.get("at_mm") or (0.0, 0.0, 0.0),
            entry.get("newtons") or (0.0, 0.0, 0.0),
            scale)
        segments.extend(made)
    if not segments:
        return

    shader, polyline = _line_shader()
    if shader is None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    batch = batch_for_shader(shader, 'LINES', {"pos": segments})
    shader.bind()
    shader.uniform_float("color", FORCE_COLOR + (alpha,))
    if polyline:
        viewport = gpu.state.viewport_get()
        shader.uniform_float("viewportSize",
                             (float(viewport[2]), float(viewport[3])))
        shader.uniform_float("lineWidth", 3.0)
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    try:
        batch.draw(shader)
    finally:
        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('LESS_EQUAL')


def _draw_forces_2d():
    """The magnitude, in pixels, at the tip of each arrow."""

    drawable = _drawable()
    if drawable is None:
        return
    forces, alpha, scale = drawable

    region = getattr(bpy.context, "region", None)
    rv3d = getattr(bpy.context, "region_data", None)
    if region is None or rv3d is None:
        return
    import blf
    from bpy_extras import view3d_utils

    for name, entry in forces.items():
        _segments, tip, magnitude = _arrow(
            entry.get("at_mm") or (0.0, 0.0, 0.0),
            entry.get("newtons") or (0.0, 0.0, 0.0),
            scale)
        if tip is None:
            continue
        at = view3d_utils.location_3d_to_region_2d(region, rv3d, tip)
        if at is None:
            continue  # behind the camera
        try:
            blf.size(0, 13)
        except TypeError:
            blf.size(0, 13, 72)  # the three-argument form, on older builds
        blf.color(0, FORCE_COLOR[0], FORCE_COLOR[1], FORCE_COLOR[2], alpha)
        blf.position(0, float(at[0]) + 8.0, float(at[1]) + 8.0, 0.0)
        blf.draw(0, "{:.2f} N  {:s}".format(magnitude, str(name)))


def _add_draw_handlers():
    global _draw_3d_handle, _draw_2d_handle

    space = bpy.types.SpaceView3D
    if _draw_3d_handle is None:
        _draw_3d_handle = space.draw_handler_add(
            _draw_forces_3d, (), 'WINDOW', 'POST_VIEW')
    if _draw_2d_handle is None:
        _draw_2d_handle = space.draw_handler_add(
            _draw_forces_2d, (), 'WINDOW', 'POST_PIXEL')


def _remove_draw_handlers():
    """Guarded, and safe to call twice: it runs on every stop and on unload."""

    global _draw_3d_handle, _draw_2d_handle

    space = bpy.types.SpaceView3D
    for handle in (_draw_3d_handle, _draw_2d_handle):
        if handle is None:
            continue
        try:
            space.draw_handler_remove(handle, 'WINDOW')
        except Exception:
            pass
    _draw_3d_handle = None
    _draw_2d_handle = None


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class MESH_AGENT_OT_live_start(Operator):
    bl_idname = "mesh_agent.live_start"
    bl_label = "Start"
    bl_description = ("Run the accepted rollout's mechanism live, with its "
                      "policy driving it")

    def execute(self, context):
        ok, message = start(context)
        self.report({'INFO'} if ok else {'WARNING'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}


class MESH_AGENT_OT_live_stop(Operator):
    bl_idname = "mesh_agent.live_stop"
    bl_label = "Stop"
    bl_description = "End the live session and restore the recorded pose"

    def execute(self, context):
        ok, message = stop(context)
        self.report({'INFO'} if ok else {'WARNING'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}


class MESH_AGENT_OT_live_pause(Operator):
    bl_idname = "mesh_agent.live_pause"
    bl_label = "Pause"
    bl_description = "Stop granting control steps; the mechanism holds still"

    @classmethod
    def poll(cls, context):
        return is_running()

    def execute(self, context):
        live = _session
        live.paused = not live.paused
        _tag_redraw()
        return {'FINISHED'}


class MESH_AGENT_OT_live_reset(Operator):
    bl_idname = "mesh_agent.live_reset"
    bl_label = "Reset"
    bl_description = "Start a fresh episode at the next seed"

    @classmethod
    def poll(cls, context):
        return _session is not None

    def execute(self, context):
        # Close and reopen rather than a fourth op: a reset is a new
        # episode, an open is what makes one, and the engine already counts
        # resets of its own.
        seed = (_session.reset_count if _session is not None else 0) + 1
        stop(context)
        ok, message = start(context, seed=seed)
        self.report({'INFO'} if ok else {'WARNING'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}


class MESH_AGENT_OT_live_compass_push(Operator):
    bl_idname = "mesh_agent.live_compass_push"
    bl_label = "Push"
    bl_description = ("Shove the mechanism in a world direction with an "
                      "exactly known force")

    degrees: bpy.props.FloatProperty(name="Azimuth", default=0.0)

    @classmethod
    def poll(cls, context):
        return is_running()

    def execute(self, context):
        live = _session
        newtons = float(getattr(context.scene, "cadex_live_newtons",
                                DEFAULT_NEWTONS))
        body = str(getattr(context.scene, "cadex_live_body", "")
                   or (live.components[0] if live.components else ""))
        live.arm_push(newtons, math.radians(self.degrees), body)
        _tag_redraw()
        return {'FINISHED'}


class MESH_AGENT_OT_live_push(Operator):
    """Click a body and hold: it is pushed for as long as you hold it.

    The gesture follows ``cadex_pick``'s eyedropper -- ``modal_handler_add``,
    ``scene.ray_cast``, ``view3d_utils``, ESC and right-click to cancel --
    because the shell already has one way to point at the model with the
    mouse and a second one would be a second thing to learn.

    The drag vector is unprojected onto the **ground plane**: its direction
    is the azimuth (0 at world +X, ADR-107) and its length is the magnitude,
    at :data:`PIXELS_PER_NEWTON`.

    **Hold, not flick** (ADR-110). This used to arm one 0.12 s impulse on
    release, which is not what "pull it around" means and is over before you
    have seen it. Now the press starts a *held* push and every mouse move
    re-aims it; the engine needs nothing for this, because ``_arm_push``
    replaces the pending push and resets its window, so re-sending a short
    push every tick is a continuous force. Release stops it.

    Feedback is the header text **and** the force arrow the viewport now
    draws — which comes back from the engine as the ``xfrc_applied`` it
    actually applied, so it stops when the push really stops rather than when
    this operator thinks it did.

    A drag can never be repeated exactly, which is why the compass buttons
    exist beside it, still as one-shot impulses: an ADR needs a number.
    """

    bl_idname = "mesh_agent.live_push"
    bl_label = "Push"
    bl_description = ("Click a part of the mechanism and hold to shove it, "
                      "for as long as you hold")

    #: Drag pixels per newton. 200 px of drag is 1 N, so the whole of a
    #: typical viewport is a few newtons: enough to knock the machine over
    #: deliberately, not enough to do it by accident.
    PIXELS_PER_NEWTON = 200.0

    @classmethod
    def poll(cls, context):
        return is_running()

    def invoke(self, context, event):
        if context.window is None:
            return {'CANCELLED'}
        self._body = ""
        self._origin = None
        self._start = (event.mouse_x, event.mouse_y)
        context.window.cursor_modal_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _finish(self, context, header=None):
        """Let go of the machine, the cursor and the header, in that order.

        Releasing first and unconditionally: every exit from this operator
        runs through here, and one that forgot would leave the mechanism
        being shoved by a mouse that is no longer down.
        """

        live = _session
        if live is not None:
            live.release_push()
        context.window.cursor_modal_restore()
        area = context.area
        if area is not None:
            area.header_text_set(header)
        _tag_redraw()

    def modal(self, context, event):
        from . import cadex_pick

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self._finish(context)
            return {'CANCELLED'}

        if _session is None:
            # The session died under the drag -- a dead engine, a refused
            # step. There is nothing left to push.
            self._finish(context)
            return {'CANCELLED'}

        region = cadex_pick.viewport_region_at(
            context.window.screen.areas, event.mouse_x, event.mouse_y)

        if event.type == 'MOUSEMOVE' and self._body:
            newtons, degrees = self._vector(event)
            _session.hold_push(newtons, math.radians(degrees), self._body)
            if context.area is not None:
                context.area.header_text_set(
                    "Pushing {:s}: {:.2f} N at {:.0f}° from world +X "
                    "(release to stop)".format(self._body, newtons, degrees))
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if region is None:
                # Absorbs the press that landed on the button rather than
                # on the model, exactly as the eyedropper does.
                return {'RUNNING_MODAL'}
            body = self._pick(context, event, region)
            if not body:
                self.report({'INFO'}, "Nothing under the cursor")
                self._finish(context)
                return {'CANCELLED'}
            self._body = body
            self._start = (event.mouse_x, event.mouse_y)
            # Held from the press, at nothing: the drag has no length yet, so
            # this is a 0 N push that moves nothing and draws no arrow. It
            # exists so that holding is one state that begins where the
            # gesture begins rather than on the first mouse move.
            _session.hold_push(0.0, 0.0, body)
            if context.area is not None:
                context.area.header_text_set(
                    "Pushing {:s}: drag to aim, release to stop".format(body))
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if not self._body:
                return {'RUNNING_MODAL'}
            newtons, _degrees = self._vector(event)
            self._finish(context)
            if newtons <= 0.0:
                self.report({'INFO'}, "No drag, no push")
                return {'CANCELLED'}
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _pick(self, context, event, region):
        from bpy_extras import view3d_utils
        from . import cadex_hydrate

        rv3d = getattr(region, "data", None)
        if rv3d is None:
            return ""
        coord = (event.mouse_x - region.x, event.mouse_y - region.y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        depsgraph = context.evaluated_depsgraph_get()
        hit, _location, _normal, _index, obj, _matrix = (
            context.scene.ray_cast(depsgraph, origin, direction))
        if not hit or obj is None:
            return ""
        name = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "")
        live = _session
        if live is None or name not in live.objects:
            return ""
        return name

    def _vector(self, event):
        """The drag, as ``(newtons, degrees)`` in the world ground plane.

        Screen X is taken as world +X and screen Y as world +Y, which is
        true looking down the -Z axis and approximately true from any
        ordinary orbit above the floor. It is deliberately not view-exact:
        an aim that changed meaning as the camera moved would make two
        pushes from two angles incomparable, and comparing pushes is what
        the compass buttons beside this exist for.
        """

        dx = float(event.mouse_x - self._start[0])
        dy = float(event.mouse_y - self._start[1])
        length = math.hypot(dx, dy)
        newtons = length / self.PIXELS_PER_NEWTON
        degrees = math.degrees(math.atan2(dy, dx)) % 360.0 if length else 0.0
        return newtons, degrees


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

class CADEX_LIVE_PT_session(Panel):
    """Start, stop, and what the mechanism is doing right now."""

    bl_space_type = 'CADEX_LIVE'
    bl_region_type = 'WINDOW'
    bl_label = "Live Session"

    def draw(self, context):
        layout = self.layout
        live = _session
        scene = context.scene

        layout.prop(scene, "cadex_live_variation")
        note = layout.column(align=True)
        note.enabled = False
        if scene.cadex_live_variation:
            note.label(text="the declared episode: drawn shoves, a")
            note.label(text="wind, a lean, a drop and a stumble")
        else:
            note.label(text="nominal machine, solved pose,")
            note.label(text="nothing pushing it but you")

        row = layout.row(align=True)
        if live is None:
            row.operator(MESH_AGENT_OT_live_start.bl_idname, icon='PLAY')
        else:
            row.operator(MESH_AGENT_OT_live_stop.bl_idname, icon='SNAP_FACE')
            pause = row.operator(
                MESH_AGENT_OT_live_pause.bl_idname,
                text="Resume" if live.paused else "Pause",
                icon='PLAY' if live.paused else 'PAUSE')
            row.operator(MESH_AGENT_OT_live_reset.bl_idname, icon='LOOP_BACK')

        if live is None:
            note = layout.column(align=True)
            note.enabled = False
            note.label(text="Plays the accepted rollout's mechanism,")
            note.label(text="with its policy driving it — and lets")
            note.label(text="you push it while it answers.")
            return

        if live.error:
            alert = layout.row()
            alert.alert = True
            alert.label(text=live.error, icon='ERROR')

        box = layout.box().column(align=True)
        box.enabled = False
        box.label(text="{:.2f} s of {:.2f} s".format(
            live.time_s, live.episode_seconds),
            icon='TIME')
        box.label(
            text=("terminated: " + (live.termination or "yes"))
            if live.terminated else ("paused" if live.paused else "standing"),
            icon='ERROR' if live.terminated else 'CHECKMARK')
        box.label(text="{:d} reset{:s} so far".format(
            live.reset_count, "" if live.reset_count == 1 else "s"))
        # Two lines rather than one, because they are two different claims: a
        # held push is happening now and its number changes every mouse move;
        # an impulse happened once and its number is worth writing down.
        if live.dragging:
            box.label(text="dragging: " + live.dragging, icon='FORCE_FORCE')
        if live.last_push:
            box.label(text="last push: " + live.last_push, icon='FORCE_WIND')


class CADEX_LIVE_PT_push(Panel):
    """The shove: a drag for aim, eight buttons for a number.

    Both exist on purpose. A drag is how you find out what happens; a
    compass button is how you write it down, because a drag can never be
    repeated exactly and an ADR needs a number (ADR-109).
    """

    bl_space_type = 'CADEX_LIVE'
    bl_region_type = 'WINDOW'
    bl_label = "Push"

    @classmethod
    def poll(cls, context):
        return is_running()

    def draw(self, context):
        layout = self.layout
        live = _session
        scene = context.scene

        layout.prop(scene, "cadex_live_newtons", text="Force")
        row = layout.row()
        row.prop(scene, "cadex_live_body", text="Body")
        if not scene.cadex_live_body and live.components:
            note = layout.row()
            note.enabled = False
            note.label(text="empty is " + live.components[0])

        layout.operator(MESH_AGENT_OT_live_push.bl_idname,
                        text="Click and Hold in the Viewport",
                        icon='EYEDROPPER')
        note = layout.column(align=True)
        note.enabled = False
        note.label(text="it is pushed for as long as you hold;")
        note.label(text="drag to aim, release to stop")

        column = layout.column(align=True)
        column.label(text="…or an exactly known impulse:")
        for start in (0, 4):
            row = column.row(align=True)
            for label, degrees in COMPASS[start:start + 4]:
                op = row.operator(
                    MESH_AGENT_OT_live_compass_push.bl_idname, text=label)
                op.degrees = degrees
        note = column.row()
        note.enabled = False
        note.label(text="azimuth is about world +X (ADR-107)")

        layout.separator()
        layout.prop(scene, "cadex_live_force_scale")
        note = layout.column(align=True)
        note.enabled = False
        note.label(text="The arrow is what the engine measured, at")
        note.label(text="the body's centre of mass — and it is the")
        note.label(text="total, so with task forces on it is your")
        note.label(text="push and the task's wind as one vector.")


class CADEX_LIVE_PT_actuators(Panel):
    """What the policy is commanding, right now.

    The same bars the Policy editor draws off a recorded trace, through the
    same ``ui.draw_actuator_bars`` — the numbers mean the same thing and
    two copies of that loop would be two places for them to stop meaning it.
    """

    bl_space_type = 'CADEX_LIVE'
    bl_region_type = 'WINDOW'
    bl_label = "Policy Outputs"

    @classmethod
    def poll(cls, context):
        return is_running()

    def draw(self, context):
        from . import ui as ui_module
        live = _session
        ui_module.draw_actuator_bars(
            self.layout,
            [_channel_label(channel) for channel in live.channels],
            live.commands,
        )


def _channel_label(channel):
    """The trace's channel shape, which ``draw_actuator_bars`` reads.

    ``live_open`` hands back ``actuator_channels`` in the bundle's own shape
    (``actuator``/``joint``/``unit``/``low``/``high``); the recorded trace's
    table adds a display ``label``. One line here rather than a second
    drawing function.
    """

    row = dict(channel)
    row["label"] = str(channel.get("actuator") or channel.get("joint") or "?")
    return row


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    MESH_AGENT_OT_live_start,
    MESH_AGENT_OT_live_stop,
    MESH_AGENT_OT_live_pause,
    MESH_AGENT_OT_live_reset,
    MESH_AGENT_OT_live_compass_push,
    MESH_AGENT_OT_live_push,
    CADEX_LIVE_PT_session,
    CADEX_LIVE_PT_push,
    CADEX_LIVE_PT_actuators,
)

#: True when every class above registered. A Panel naming an unregistered
#: space type raises "Region not found in space type" and would otherwise
#: abort the whole loop -- which is how the top-bar menus once vanished
#: (ADR-036). The add-on can be loaded against a bundle older than it, so
#: this stands down rather than taking everything with it.
EDITOR_AVAILABLE = False


def _variation_changed(self, context):
    """Restart a running session on the new setting.

    A toggle that silently does nothing until the next Start is a toggle
    that lies, and this one changes what the episode *is* — it can only be
    chosen at ``live_open``. So the session is torn down and reopened, at
    the seed the next reset would have had, which is what Reset already
    does.
    """

    if _session is None:
        return
    seed = _session.reset_count + 1
    stop(context)
    start(context, seed=seed)


def register():
    global EDITOR_AVAILABLE
    bpy.types.Scene.cadex_live_newtons = bpy.props.FloatProperty(
        name="Force", description="How hard a compass push shoves, in newtons",
        default=DEFAULT_NEWTONS, min=0.0, max=20.0, soft_max=5.0, unit='NONE')
    bpy.types.Scene.cadex_live_body = bpy.props.StringProperty(
        name="Body",
        description="Which component a compass push acts on; empty is the "
                    "mechanism's root")
    # Off by default, and the engine's default is the opposite (ADR-110). The
    # op's job is to play the task as the bundle declares it; the panel's job
    # is to be an instrument, and an instrument opens with only the force you
    # are applying acting on the machine.
    bpy.types.Scene.cadex_live_variation = bpy.props.BoolProperty(
        name="Task forces and reset variation",
        description="Play the episode as the bundle declares it — randomised "
                    "masses, a varied starting pose, and the task's own "
                    "shoves. Off is one nominal machine at the solved pose, "
                    "so the only force acting is yours",
        default=False, update=_variation_changed)
    bpy.types.Scene.cadex_live_force_scale = bpy.props.FloatProperty(
        name="Arrow Scale",
        description="Millimetres of force arrow per newton",
        default=DEFAULT_FORCE_SCALE_MM_N, min=1.0, max=5000.0,
        soft_max=1000.0, unit='NONE')
    registered = []
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as exc:
            print("mesh_agent: live mode unavailable ({:s}: {!s})".format(
                cls.__name__, exc))
            for done in reversed(registered):
                bpy.utils.unregister_class(done)
            EDITOR_AVAILABLE = False
            return
        registered.append(cls)
    EDITOR_AVAILABLE = True


def unregister():
    global EDITOR_AVAILABLE, _shader
    if _session is not None:
        stop(None)
    # Again, and unconditionally: ``stop`` only runs when a session existed,
    # and a handler that outlives the module draws forever and raises on the
    # next reload.
    _remove_draw_handlers()
    _shader = None  # a GPU object must not survive the add-on that made it
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    if EDITOR_AVAILABLE:
        for cls in reversed(classes):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
    EDITOR_AVAILABLE = False
    for name in ("cadex_live_newtons", "cadex_live_body",
                 "cadex_live_variation", "cadex_live_force_scale"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
