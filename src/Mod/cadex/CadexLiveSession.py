# SPDX-License-Identifier: LGPL-2.1-or-later

"""The resident live worker, from cadexd's side (ADR-109).

One per open project, owned by :class:`CadexdServer`, **spawned on the first
``live_open``** so a session that never starts one never pays for it. The
shape is :mod:`CadexWarmWorker`'s, deliberately and almost line for line:
spawn a ``FreeCADCmd --safe-mode`` out of the content-addressed bundle, read
its replies on a daemon thread, wait for a ``ready`` handshake, bound every
exchange with a deadline, and kill it whenever anything about the project
changes. That worker was the one existing pattern that threads the engine's
purity constraint, and live mode reuses it rather than inventing a second.

**What makes a resident process acceptable here** is what made it acceptable
there: it cannot affect the model. It never writes the project store, never
publishes, never moves a revision or a digest, and never emits a trace. A
live session is a *thing to watch* -- if it were reproducible it would be a
rollout, and a rollout already exists.

**This module imports no physics.** ``mujoco`` and :mod:`CadexDynamics` live
on the far side of the process boundary, in :mod:`cadex_live_worker`, which
is staged into the bundle by filename and is therefore outside cadexd's
import closure by construction. ``test_engine_purity_guardrails`` asserts
that closure *exactly*, so this file joining ``DECLARED_ENGINE_MODULES`` and
the worker not joining it is the whole architecture, stated as a test.

**The shell drives time.** A ``live_step`` grants N control steps and gets
the N frames they produced; the worker's episode loop blocks for that credit
rather than sleeping against a clock of its own. Pause is then the absence
of a request, which costs nothing and cannot drift.
"""

from __future__ import annotations

import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
from typing import Any, Mapping

#: A live step that has not answered by now is a wedged episode, not a slow
#: one: the measured cost is 344 us a control step, so even a 64-step batch
#: is 22 ms of physics. Generous by four orders of magnitude, and bounded
#: because this waits on cadexd's serial dispatch thread.
LIVE_DEADLINE_SECONDS = 10.0

#: The most control steps one request may ask for. At 100 Hz this is 2.5
#: seconds of simulation in one round trip, which is far past anything a
#: 30 Hz pump asks for and near enough the frame cap to matter: 64 frames of
#: 24 components is roughly 250 kB against the protocol's 8 MB.
MAX_STEPS_PER_REQUEST = 256

#: The staged entry module. A *name*, never an import -- exactly as
#: :data:`CadexWarmWorker.ENTRY_MODULE` is, and for the same reason: this
#: module is in cadexd's closure and that one deliberately is not.
ENTRY_MODULE = "cadex_live_worker"


class CadexLiveSession:
    """A resident ``FreeCADCmd`` playing one episode you can push."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = Path(project_root)
        self._process: subprocess.Popen | None = None
        self._replies: queue.SimpleQueue = queue.SimpleQueue()
        self._staging: Path | None = None
        self._open: dict[str, Any] | None = None
        self._sequence = 0

    # -- lifetime --------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._open is not None and self._process is not None

    def invalidate(self) -> None:
        """Drop the session. Free: it holds nothing the store needs.

        Called by every handler that can change the script, the parameters,
        the assets or the project -- the same list :class:`CadexWarmWorker`
        is invalidated on, and for a sharper reason. A preview answering
        from a stale generation shows the wrong poses; a live session
        answering from one plays a *mechanism that no longer exists* while
        the viewport says it does.
        """

        self.close()

    def close(self) -> dict[str, Any]:
        process, self._process = self._process, None
        self._open = None
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        for stream in (
            getattr(process, "stdin", None),
            getattr(process, "stdout", None),
        ):
            try:
                stream.close()
            except Exception:
                pass
        staging, self._staging = self._staging, None
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        return {"closed": True}

    # -- the two public operations ---------------------------------------

    def open(
        self,
        prepared: Mapping[str, Any],
        seed: int | None,
        variation: bool = True,
    ) -> dict[str, Any]:
        """Start a session on the accepted rollout's bundle.

        ``variation`` false is the **calm session** (ADR-110): the worker
        plays every episode unseeded, which is the state
        ``evaluate_episode`` has always had for a caller that passes no seed
        -- the nominal mechanism, at the pose the solve found, with nothing
        pushing it. The seed is still carried and still counts up per reset,
        because turning variation back on mid-session must not renumber the
        episodes; it is simply not used while this is false.
        """

        self.close()
        self._spawn(prepared)
        answer = self._exchange(
            {
                "op": "open",
                "request": {
                    # Names inside the staging directory, never host paths:
                    # the worker resolves against CADEX_LIVE_ROOT and can see
                    # nothing else, which is the same containment every other
                    # isolated worker runs under.
                    "model_file": "model.xml",
                    "task_file": "task.json",
                    "weights_file": "weights.cxpolicy",
                    "components": list(prepared["components"]),
                    # No longer coerced to 0 when absent: that coercion is
                    # what made the calm episode unreachable from live mode
                    # for as long as live mode existed.
                    "seed": seed if seed is None else int(seed),
                    "variation": bool(variation),
                },
            }
        )
        if answer.get("ok") is not True:
            self.close()
            raise LiveSessionFailure(
                str(answer.get("error") or "the live worker could not open a session")
            )
        self._open = {
            key: answer[key]
            for key in (
                "components",
                "control_hz",
                "frames_per_second",
                "actuator_channels",
                "episode_seconds",
            )
        }
        return dict(self._open)

    def step(self, steps: int, push: Any) -> dict[str, Any]:
        """Advance the episode by ``steps`` control steps and drain frames."""

        if not self.is_open:
            raise LiveSessionFailure("No live session is open; call live_open first.")
        count = int(steps)
        if not 1 <= count <= MAX_STEPS_PER_REQUEST:
            raise LiveSessionFailure(
                f"A live step advances 1 to {MAX_STEPS_PER_REQUEST} control "
                f"steps; this asked for {count}."
            )
        frame: dict[str, Any] = {"op": "step", "steps": count}
        if isinstance(push, dict):
            frame["push"] = dict(push)
        answer = self._exchange(frame)
        if answer.get("ok") is not True:
            # A failed step is a dead session rather than a dropped frame:
            # the episode thread is gone and every later step would report
            # the same corpse.
            error = str(answer.get("error") or "the live step failed")
            self.close()
            raise LiveSessionFailure(error)
        return {
            "frames": list(answer.get("frames") or ()),
            "step": int(answer.get("step") or 0),
            "time_s": float(answer.get("time_s") or 0.0),
            "terminated": bool(answer.get("terminated")),
            "termination": str(answer.get("termination") or ""),
            "reset_count": int(answer.get("reset_count") or 0),
        }

    # -- internals -------------------------------------------------------

    def _spawn(self, prepared: Mapping[str, Any]) -> None:
        from CadexScriptedRuntime import worker_environment

        staging = Path(tempfile.mkdtemp(prefix="cadex-live-"))
        self._staging = staging
        # Copies rather than hardlinks: the store's copy is the durable one
        # and a live session must not be able to reach it at all, let alone
        # through an inode it shares. Three files, ~250 kB.
        for name, key in (
            ("model.xml", "model_file"),
            ("task.json", "task_file"),
            ("weights.cxpolicy", "weights_file"),
        ):
            shutil.copyfile(str(prepared[key]), str(staging / name))
        bundle = str(prepared["bundle_dir"])
        code = (
            "import os,sys;"
            "sys.path.insert(0,os.getcwd());"
            f"sys.path.insert(0,{bundle!r});"
            f"import {ENTRY_MODULE} as _w;"
            "raise SystemExit(_w.main())"
        )
        environment = worker_environment(staging)
        environment["CADEX_LIVE_ROOT"] = str(staging)
        try:
            process = subprocess.Popen(
                [
                    str(prepared["freecadcmd_executable"]),
                    "--safe-mode",
                    "-c",
                    code,
                ],
                cwd=str(staging),
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise LiveSessionFailure(
                f"the live worker could not start: {exc}"
            ) from exc
        self._process = process
        self._replies = queue.SimpleQueue()
        threading.Thread(
            target=self._reader,
            args=(process, self._replies),
            name="cadex-live-reader",
            daemon=True,
        ).start()
        ready = self._receive()
        if str(ready.get("event", {}).get("event") or "") != "ready":
            raise LiveSessionFailure("the live worker did not announce itself.")

    @staticmethod
    def _reader(process: subprocess.Popen, replies: queue.SimpleQueue) -> None:
        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    frame = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    continue  # pre-hijack FreeCADCmd chatter
                if isinstance(frame, dict):
                    replies.put(frame)
        except (OSError, ValueError):
            pass
        finally:
            replies.put(None)  # the worker died: unblock whoever is waiting

    def _exchange(self, frame: dict[str, Any]) -> dict[str, Any]:
        process = self._process
        if process is None or process.poll() is not None:
            raise LiveSessionFailure("the live worker is not running.")
        self._sequence += 1
        payload = dict(frame, id=f"l{self._sequence}")
        try:
            process.stdin.write(
                json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
            )
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise LiveSessionFailure(
                f"the live worker closed its input: {exc}"
            ) from exc
        return self._receive()

    def _receive(self) -> dict[str, Any]:
        try:
            frame = self._replies.get(timeout=LIVE_DEADLINE_SECONDS)
        except queue.Empty:
            raise LiveSessionFailure(
                f"the live worker did not answer within "
                f"{LIVE_DEADLINE_SECONDS:g} seconds."
            ) from None
        if frame is None:
            raise LiveSessionFailure("the live worker exited.")
        return frame


class LiveSessionFailure(RuntimeError):
    """The session is unusable. Always ends in a kill and a refusal."""
