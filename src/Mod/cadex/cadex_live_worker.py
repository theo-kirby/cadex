# SPDX-License-Identifier: LGPL-2.1-or-later

"""Resident live worker: one running episode you can push (ADR-109).

The other end of :mod:`CadexLiveSession`, and the same shape as
:mod:`cadex_preview_worker`: a ``FreeCADCmd --safe-mode`` process out of the
same content-addressed bundle, answering NDJSON on a private fd, writing
nothing. It is in the bundle rather than beside ``cadexd`` for the reason
every domain worker is — the service may not import :mod:`CadexDynamics`,
and ``test_engine_purity_guardrails`` asserts the closure exactly.

**Why it exists.** A recorded rollout is six seconds with one drawn push.
You cannot shove it from the other side, cannot shove it harder, and cannot
shove it twice, so "does it recover" is a question the recording can never
be asked (ADR-107 records what reading such a recording through summary
statistics cost). Live mode makes the machine a thing in the room. It is
cheap: 344 us per control step on this Mac against a 10 ms control interval,
which is 29x real time.

**No fifth episode loop.** This project already carries four implementations
of one RNG contract and M9's hazard 19 is what happened when two of them
disagreed unnoticed. So the episode here *is*
:func:`CadexDynamics.evaluate_episode`, run on a thread, through the seams
it already had -- ``actions`` and ``sample`` -- plus the one that had to be
added, ``forces``, because ``apply_disturbance`` rewrites ``xfrc_applied``
from zero every step and would erase a push written from outside.

**The shell drives time**, and this is the whole reason the loop blocks
rather than sleeps. ``actions`` waits for *credit*, granted one unit per
control step by a ``step`` frame. Three consequences, all of them wanted:

- pause is free (grant nothing) and needs no state in the physics;
- a ``step`` frame's round trip measures plumbing rather than a sleep, so
  the latency lane in ``cadexd_latency_integration.py`` measures something
  that moves when the batch size moves (M9 hazard 18);
- the 29x headroom is thrown away by the one component that owns a real
  clock -- the shell's 30 Hz timer -- instead of by a sleep in here
  guessing at one.

**Calm mode** (ADR-110) is not a fourth thing this file knows how to do. It
is ``seed=None``, which is the branch ``evaluate_episode`` already guards
randomisation, reset variation and the drawn shoves behind -- the nominal
mechanism at the pose the solve found. Live mode simply never asked for it,
because the host coerced a missing seed to ``0``.

**Frames report the force that made them.** ``xfrc_applied`` is still live
when ``sample`` runs, so a frame can carry what was actually pushing each
body rather than what somebody meant to push it with; see
:meth:`_Session._applied_forces`.

**An episode ends when the machine falls, and otherwise not at all**
(ADR-136). The task's ``max_steps`` is the horizon it was *trained* at, and
nothing physical happens there: the policy's observation is sensor channels
and carries no clock, so it cannot tell step 301 from step 5. Truncating at
it is a trainer's need, not a viewer's, so this passes ``endless=True`` and
watches a session for as long as it stands. ``record_steps=False`` goes with
it and is what keeps that bounded -- see :func:`CadexDynamics.evaluate_episode`.

**Auto-reset.** A terminated episode holds for
:data:`TERMINATION_HOLD_SECONDS` of wall time so the fall is visible, then
starts again at a fresh seed and reports ``reset_count``. Credit granted
during the hold is dropped rather than banked, so the new episode starts at
the shell's pace instead of sprinting through whatever piled up.

**It never writes.** No trace, no artifact, no store. A live session is a
thing to watch, not a thing to reproduce -- and nothing it does is a digest
input, which is what keeps it outside every determinism guarantee the engine
makes rather than quietly inside one.
"""

from __future__ import annotations

import json
import math
import os
import queue
import sys
import threading
import time
import traceback
from typing import Any

SCHEMA = "cadex-live-worker-v1"

#: The directory the host stages this session's model, task and weights
#: into. Owned by the host, read-only in practice: the worker never writes.
ROOT_ENV = "CADEX_LIVE_ROOT"

#: How long a terminated episode stays terminated before the next one
#: starts. A fall that resets instantly is a fall nobody saw.
TERMINATION_HOLD_SECONDS = 1.0

#: A ``step`` frame waits this long for the episode thread to produce the
#: frames its credit paid for. Generous against 344 us a step, and bounded
#: so a wedged episode answers with what it has rather than hanging the
#: service's dispatch thread.
STEP_DEADLINE_SECONDS = 5.0

#: Frames the queue holds before the oldest are dropped. The shell drains
#: every tick; anything this far behind is a shell that stopped ticking, and
#: showing it stale poses later is worse than showing it none.
MAX_QUEUED_FRAMES = 2048

#: How often a waiting ``step`` looks up to see whether the episode it is
#: waiting on has ended. Short against the deadline, long against 344 us a
#: step, so it costs nothing on the path that is producing frames.
_POLL_SECONDS = 0.02


class _Stop(BaseException):
    """Raised inside the episode hooks to unwind a session being closed.

    ``BaseException`` on purpose: ``evaluate_episode`` is a long arithmetic
    loop with no ``except Exception`` in it, but the reward and termination
    evaluators around it are defensive, and a close must not be swallowed by
    something catching broadly.
    """


class _Session:
    """One model, one task, one policy, and the episode thread playing them."""

    def __init__(self, request: dict[str, Any], root: Any) -> None:
        import CadexDynamics

        self._dyn = CadexDynamics
        self._root = root
        self._closing = False
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._credit = 0
        self._frames: queue.SimpleQueue = queue.SimpleQueue()
        self._queued = 0
        # Set between episodes: from the moment one terminates until the
        # next one has taken its first step. A ``step`` waiting on credit
        # this episode will never spend reads it and gives up early.
        self._boundary = threading.Event()
        self._boundary.set()
        #: Bumped once per episode. A ``step`` records it before granting
        #: credit and stops waiting when it moves, which is what stops the
        #: credit-drop below from stranding a request for a full deadline.
        self._episode = 0

        self._push: dict[str, Any] | None = None
        self._step = 0
        self._time_s = 0.0
        self._reset_count = 0
        self._terminated = False
        self._termination = ""
        self._failure = ""

        self._task = json.loads(
            (root / str(request["task_file"])).read_text(encoding="utf-8")
        )
        self._model_xml = (root / str(request["model_file"])).read_bytes()
        self._container = self._dyn.decode_policy(
            (root / str(request["weights_file"])).read_bytes()
        )
        self._components = [str(name) for name in request["components"]]
        self._seed = int(request.get("seed") or 0)
        # Whether anything is drawn at all, which is not what the word means
        # thirty lines into ``evaluate_episode``: there, ``variation`` is the
        # *drawn* dict. Here it is the question that produces one. False is
        # the calm session (ADR-110) -- the unseeded episode, which is the
        # nominal mechanism at the solved pose with nothing pushing it, so
        # that the only force acting is the one the user is applying.
        self._variation = bool(request.get("variation", True))

        episode = self._task["episode"]
        self._control_hz = int(episode["control_hz"])
        self._control_interval = float(episode["control_interval_s"])
        self._max_steps = int(episode["max_steps"])

        # Compiled once and reused across every reset: the model is reloaded
        # per episode for the reason ``compare.py`` reloads it (ADR-103
        # section 9) -- ``apply_randomisation`` multiplies into the model in
        # place with no baseline kept, so a model reused across episodes
        # compounds every draw it has ever been given.
        model = self._dyn.load_model(self._model_xml)
        self._body_ids = self._resolve_bodies(model)

        self._thread = threading.Thread(
            target=self._run, name="cadex-live-episode", daemon=True
        )
        self._thread.start()

    # -- the two facts the host asks for at open -------------------------

    def opened(self) -> dict[str, Any]:
        return {
            "components": list(self._components),
            "control_hz": self._control_hz,
            # One frame per control step, by construction: a step frame
            # grants N steps and gets N frames, and any other ratio would
            # make "steps" and "frames" two numbers the shell has to
            # reconcile. So these two are the same number here -- the field
            # exists because the shell's pump reads it off a recorded trace
            # and off a live session with the same code.
            "frames_per_second": self._control_hz,
            "actuator_channels": [
                {
                    "actuator": str(action["actuator"]),
                    "joint": str(action["joint"]),
                    "motion_type": str(action["motion_type"]),
                    "kind": str(action["kind"]),
                    "unit": str(action["unit"]),
                    "low": float(action["low"]),
                    "high": float(action["high"]),
                }
                for action in self._task["actions"]
            ],
            # The horizon the policy was TRAINED at, not one this session
            # stops at -- a live episode runs until it falls (ADR-136). It
            # is still worth sending, because "you are now 40 s into a
            # machine trained on 6 s episodes" is the interesting thing a
            # viewer can be told, and the shell says exactly that.
            "episode_seconds": self._max_steps * self._control_interval,
        }

    def _resolve_bodies(self, model: Any) -> dict[str, int]:
        mujoco = self._dyn._mujoco_module()
        ids: dict[str, int] = {}
        for name in self._components:
            found = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name))
            if found < 0:
                raise ValueError(
                    f"The model this session plays carries no body named "
                    f"{name!r}, so its pose cannot be streamed."
                )
            ids[name] = found
        return ids

    # -- the request-loop side -------------------------------------------

    def step(self, steps: int, push: Any) -> dict[str, Any]:
        """Grant ``steps`` control steps and return the frames they made."""

        if isinstance(push, dict):
            self._arm_push(push)
        wanted = max(0, min(int(steps), MAX_QUEUED_FRAMES))
        with self._wake:
            self._credit += wanted
            self._wake.notify_all()

        frames: list[dict[str, Any]] = []
        generation = self._episode
        if wanted:
            deadline = _now() + STEP_DEADLINE_SECONDS
            while len(frames) < wanted:
                remaining = deadline - _now()
                if remaining <= 0.0:
                    break
                try:
                    frames.append(
                        self._frames.get(timeout=min(remaining, _POLL_SECONDS))
                    )
                except queue.Empty:
                    # An episode that terminated mid-batch will never spend
                    # the rest of this credit -- it is holding, and then it
                    # drops what is left so the next one starts at the
                    # shell's pace. Waiting out the deadline for frames that
                    # are never coming turned a 21 ms batch into a 5 s one,
                    # which is the whole of why this is a poll rather than a
                    # single blocking get.
                    #
                    # Both conditions are needed and the second was found by
                    # measuring rather than by reading. `_boundary` covers
                    # the hold; the *generation* covers the one-step window
                    # where credit granted a moment ago has just been
                    # dropped by the episode that replaced it. Without it a
                    # push landing near a fall stalled the shell's pump for
                    # a full 5 s deadline -- long enough to swallow the next
                    # three pushes, and invisible from either side.
                    if self._boundary.is_set() or self._episode != generation:
                        break
        # Whatever else arrived while we were assembling: a reset frame, or
        # the tail of a terminated episode. Dropping it would put a gap in
        # the pose stream and Blender would interpolate across it, which is
        # hazard 5 in a different costume.
        while True:
            try:
                frames.append(self._frames.get_nowait())
            except queue.Empty:
                break
        with self._lock:
            self._queued = max(0, self._queued - len(frames))
            state = {
                "step": self._step,
                "time_s": self._time_s,
                "terminated": self._terminated,
                "termination": self._termination,
                "reset_count": self._reset_count,
            }
        if self._failure:
            raise RuntimeError(self._failure)
        return {"frames": frames, **state}

    def _arm_push(self, push: dict[str, Any]) -> None:
        """Hold one live shove until the episode loop reads it."""

        newtons = float(push.get("newtons") or 0.0)
        azimuth = float(push.get("azimuth_rad") or 0.0)
        duration = float(push.get("duration_s") or 0.0)
        body = str(push.get("body") or "")
        if not math.isfinite(newtons) or not math.isfinite(azimuth):
            raise ValueError("A live push needs a finite magnitude and azimuth.")
        if not (0.0 < duration <= 5.0):
            raise ValueError(
                "A live push lasts between 0 and 5 seconds; anything longer "
                "is a wind, and a wind is a task declaration."
            )
        if body not in self._body_ids:
            raise ValueError(
                f"A live push names {body!r}, which is not a component this "
                f"session plays."
            )
        with self._lock:
            self._push = {
                "body": self._body_ids[body],
                # Horizontal, in the WORLD frame, at the body's centre of
                # mass -- the same three choices ``apply_disturbance`` makes,
                # because a push the user aims and a push the task draws must
                # be the same kind of thing or the comparison is worthless.
                # 0 rad is world +X (ADR-107): the engine does not know which
                # way the mechanism faces and this is not the place to start.
                "force": [
                    newtons * math.cos(azimuth),
                    newtons * math.sin(azimuth),
                    0.0,
                ],
                "until_s": None,
                "duration_s": duration,
                "newtons": newtons,
                "azimuth_rad": azimuth,
            }

    def close(self) -> None:
        with self._wake:
            self._closing = True
            self._credit = 0
            self._wake.notify_all()
        self._thread.join(timeout=5.0)

    # -- the episode-thread side -----------------------------------------

    def _run(self) -> None:
        try:
            while True:
                with self._lock:
                    if self._closing:
                        return
                    # Credit banked during a hold is dropped, not spent: the
                    # new episode starts at the shell's pace rather than
                    # sprinting through the queue that piled up while the
                    # last one lay on the floor. Anybody waiting on that
                    # credit is released by the generation bump beside it.
                    self._credit = 0
                    self._episode += 1
                    # ``None`` is not "seed zero": it is the branch every
                    # per-episode draw is guarded behind, so a calm session
                    # is the same machine every episode and the push you
                    # applied is the only thing that moved it.
                    seed = (
                        (self._seed + self._reset_count)
                        if self._variation
                        else None
                    )
                    self._step = 0
                    self._time_s = 0.0
                    self._terminated = False
                    self._termination = ""
                    self._push = None
                self._boundary.clear()
                episode = self._dyn.evaluate_episode(
                    self._dyn.load_model(self._model_xml),
                    self._task,
                    actions=self._actions,
                    sample=self._sample,
                    forces=self._forces,
                    seed=seed,
                    # An episode ends when the machine falls, and otherwise
                    # not at all (ADR-136). ``record_steps`` is what makes
                    # that affordable: the per-step history this returns is
                    # read by nobody here and would be the whole memory cost
                    # of a session left running.
                    endless=True,
                    record_steps=False,
                )
                with self._lock:
                    self._terminated = episode["terminated_step"] is not None
                    self._termination = str(episode["termination"] or "")
                    self._reset_count += 1
                self._boundary.set()
                self._hold()
        except _Stop:
            return
        except BaseException as exc:  # reported on the next step frame
            self._failure = f"{exc.__class__.__name__}: {exc}"
        finally:
            # However this ended, nothing is coming: unblock anybody waiting
            # on frames rather than making them find out by deadline.
            self._boundary.set()

    def _hold(self) -> None:
        """Wall time with the machine left where it fell."""

        deadline = _now() + TERMINATION_HOLD_SECONDS
        with self._wake:
            while not self._closing:
                remaining = deadline - _now()
                if remaining <= 0.0:
                    break
                self._wake.wait(timeout=remaining)
            if self._closing:
                raise _Stop()

    def _actions(self, step: int, observation: Any) -> list[float]:
        with self._wake:
            while self._credit <= 0 and not self._closing:
                self._wake.wait(timeout=0.25)
            if self._closing:
                raise _Stop()
            self._credit -= 1
        return self._dyn.policy_forward(
            self._container["header"],
            self._container["weights"],
            observation,
            context="this live session",
        )

    def _forces(self, _step: int, data: Any, time_s: float) -> None:
        with self._lock:
            push = self._push
            if push is None:
                return
            if push["until_s"] is None:
                push["until_s"] = float(time_s) + float(push["duration_s"])
            if float(time_s) >= float(push["until_s"]):
                self._push = None
                return
            body, force = int(push["body"]), list(push["force"])
        for axis in range(3):
            data.xfrc_applied[body, axis] += float(force[axis])

    def _applied_forces(self, data: Any) -> dict[str, Any]:
        """What is actually pushing each body, right now (ADR-110).

        Measured, not intended. ``data.xfrc_applied`` is still live when this
        runs -- it is written before ``mj_step`` and cleared only by the
        *next* step's ``apply_disturbance`` -- so this is the force that
        produced the frame being emitted. A shell drawing its own armed push
        instead would keep drawing it after the window lapsed, after a clamp
        and after a refusal, which is ADR-103's and ADR-107's lesson applied
        before it bites rather than after.

        It is the **total** on that body, because ``xfrc_applied`` is a sum:
        in a session playing the declared episode, a user's shove and the
        task's wind on the same body are one arrow. That is the right thing
        to draw and the panel says so; in a calm session the arrow is purely
        the user's, which is the whole point of the switch beside it.

        Reported at ``data.xipos``, the body's centre of mass in world
        coordinates -- where ``xfrc_applied`` acts, and not ``xpos``, which
        is the frame origin. ``vector_mm`` is reused rather than spelled
        again: ``test_dynamics_units`` greps this module for a third
        conversion.
        """

        forces: dict[str, Any] = {}
        for name, body in self._body_ids.items():
            vector = [float(value) for value in data.xfrc_applied[body][:3]]
            if not any(vector):
                continue
            forces[name] = {
                "newtons": vector,
                "at_mm": self._dyn.vector_mm(data.xipos[body]),
            }
        return forces

    def _sample(
        self, step: int, data: Any, final: bool, action: Any
    ) -> None:
        # The reset pose carries no action and is streamed anyway: it is
        # where the machine starts, and the shell needs a pose for every
        # component in every frame or Blender interpolates the gap and a
        # part that stopped moving looks like a physics result (hazard 5).
        record: dict[str, Any] = {
            "frame_index": step,
            "frame_kind": "input" if step == 0 else "solver_output",
            "nominal_time_s": step * self._control_interval,
            "component_placements": {
                name: {
                    "position_mm": self._dyn.vector_mm(data.xpos[body]),
                    "rotation_xyzw": self._dyn.quaternion_xyzw_from_wxyz(
                        self._dyn.quaternion_normalised(data.xquat[body])
                    ),
                }
                for name, body in self._body_ids.items()
            },
        }
        if action is not None:
            record["actuator_commands"] = [float(value) for value in action]
        applied = self._applied_forces(data)
        if applied:
            record["applied_forces"] = applied
        with self._lock:
            self._step = int(step)
            self._time_s = step * self._control_interval
            if self._queued >= MAX_QUEUED_FRAMES:
                try:
                    self._frames.get_nowait()
                    self._queued -= 1
                except queue.Empty:
                    pass
            self._queued += 1
        self._frames.put(record)
        # Nothing is returned to ``evaluate_episode``: its ``samples`` list
        # would otherwise grow without bound for a session that never ends,
        # and the frames have already left on the queue.
        return None


def _now() -> float:
    return time.monotonic()


def _handle(
    frame: dict[str, Any], root: Any, session: _Session | None
) -> tuple[dict[str, Any], _Session | None]:
    """Answer one frame; returns the reply and the session to keep."""

    op = str(frame.get("op") or "")
    if op == "open":
        request = frame.get("request")
        if not isinstance(request, dict):
            raise ValueError("An open frame needs a request.")
        if session is not None:
            session.close()
        session = _Session(request, root)
        return {"ok": True, **session.opened()}, session

    if op == "step":
        if session is None:
            raise ValueError("This worker has no open live session.")
        return (
            {"ok": True, **session.step(int(frame.get("steps") or 0),
                                        frame.get("push"))},
            session,
        )

    if op == "close":
        if session is not None:
            session.close()
        return {"ok": True, "closed": True}, None

    raise ValueError(f"Unsupported live worker op: {op!r}.")


def main() -> int:
    module_root = os.path.dirname(os.path.abspath(__file__))
    if module_root not in sys.path:
        sys.path.insert(0, module_root)

    protocol_fd = os.dup(1)
    os.dup2(2, 1)
    protocol_out = os.fdopen(protocol_fd, "wb", buffering=0)

    def send(frame: dict[str, Any]) -> None:
        protocol_out.write(
            json.dumps(
                frame,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                default=str,
            ).encode("utf-8")
            + b"\n"
        )

    from pathlib import Path

    root = Path(os.environ[ROOT_ENV]).resolve()
    send({"id": None, "event": {"event": "ready", "schema": SCHEMA,
                                "pid": os.getpid()}})

    session: _Session | None = None
    for line in sys.stdin.buffer:  # EOF: the host died — self-exit.
        line = line.strip()
        if not line:
            continue
        request_id = None
        try:
            frame = json.loads(line.decode("utf-8"))
            if not isinstance(frame, dict):
                raise TypeError("A live worker frame must be an object.")
            request_id = frame.get("id")
            reply, session = _handle(frame, root, session)
        except BaseException as exc:  # a bad frame must not kill the worker
            reply = {
                "ok": False,
                "exception_type": exc.__class__.__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=20),
            }
        send({"id": request_id, **reply})
    if session is not None:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
