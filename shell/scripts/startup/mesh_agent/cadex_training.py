# SPDX-License-Identifier: GPL-2.0-or-later

"""The shell's view of a training run that is happening somewhere else.

**No ssh, no protocol change, no engine change, and above all no mujoco.**
``test_the_shell_never_learns_about_mujoco`` pins that this side may never
import it, and nothing here comes close: what this module knows is how to
read one JSON file off the local disk and how often to look at it.

The file is ``training-progress.json`` in the project root, and
``training/remote_train.sh watch`` is what puts it there -- it polls the box
over rsync and writes the copy that lands beside the project. So the chain
is: the trainer writes ``progress.json`` on a GPU machine, ``watch`` mirrors
it, and this reads the mirror. Three processes, one file format, and the
only one that has to be running for this panel to be correct is the trainer.

Why a file rather than a connection. The shell has no ssh credentials, no
business having any, and a panel that opened a network connection would be
a panel that blocks Blender's main thread the first time a box is slow. A
file is already the contract ADR-098 chose for the same reason on the other
side, and reading one is a stat.

Nothing here parses a log. ADR-093's finding was that a receipt taken from a
stream is a receipt something else can write into -- MuJoCo without the
optional ``warp`` backend prints two lines to stdout, and that cost a 3 h
49 m run's dispatch. ``progress.json`` is written atomically by the trainer
precisely so this side can read it without ever seeing half of one.
"""

from __future__ import annotations

import json
import os

import bpy

#: What ``remote_train.sh watch`` writes beside the project. Named here and
#: in the dispatch script, and a test asserts the two spellings match --
#: this is the whole interface between them.
PROGRESS_NAME = "training-progress.json"

#: The schema the trainer stamps. A file that does not carry it is not this
#: file, and the panel says so rather than drawing zeros.
PROGRESS_SCHEMA = "cadex-training-progress-v1"

#: The states a run reports. ``starting`` and ``training`` are live -- the
#: timer keeps looking; ``done`` and ``failed`` are terminal, and the panel
#: keeps showing the last thing that happened rather than disappearing,
#: because "it finished" is information and an empty panel is not.
LIVE_STATES = frozenset({"starting", "training"})
TERMINAL_STATES = frozenset({"done", "failed"})

#: How often the timer looks. A training run publishes at most one update
#: per iteration and an iteration is seconds; polling faster would be a stat
#: per redraw for a number that has not changed.
POLL_SECONDS = 2.0

#: path -> (mtime, size, payload). One stat per poll, and a re-read only
#: when the file actually moved.
_cache: dict[str, tuple] = {}


def progress_path(scene) -> str:
    """Where this scene's run would report, whether or not it does."""

    from . import cadex_backend

    return os.path.join(cadex_backend.project_root(scene), PROGRESS_NAME)


def read_progress(scene):
    """The run's last report, or ``None`` if there is not one.

    ``None`` for absent, unreadable, half-written and wrong-schema alike.
    The panel's job is to be invisible when there is no run, and a partial
    read is indistinguishable from no run for exactly as long as it takes
    the writer's ``replace`` to land.
    """

    path = progress_path(scene)
    try:
        stat = os.stat(path)
    except OSError:
        _cache.pop(path, None)
        return None
    signature = (stat.st_mtime_ns, stat.st_size)
    cached = _cache.get(path)
    if cached is not None and cached[0] == signature:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        # Not cached: a file mid-write becomes readable a moment later, and
        # caching the failure would make the panel wait for the *next*
        # write to notice.
        return None
    if not isinstance(payload, dict) or payload.get("schema") != PROGRESS_SCHEMA:
        return None
    _cache[path] = (signature, payload)
    return payload


def is_live(payload) -> bool:
    return bool(payload) and str(payload.get("state") or "") in LIVE_STATES


def format_eta(seconds) -> str:
    """Seconds as something you can read at a glance.

    Runs here are minutes to hours, so seconds alone stop meaning anything
    around the point you actually want to know -- ``76 min`` is the number
    the mg-legs run was described by, not ``4560 s``.
    """

    try:
        value = float(seconds or 0.0)
    except (TypeError, ValueError):
        return "-"
    if value <= 0.0:
        return "-"
    if value < 90.0:
        return "{:.0f} s".format(value)
    if value < 5400.0:
        return "{:.0f} min".format(value / 60.0)
    return "{:.1f} h".format(value / 3600.0)


def _redraw():
    """Tag the parameters editor, which is where the panel lives."""

    manager = getattr(bpy.context, "window_manager", None)
    for window in getattr(manager, "windows", ()) or ():
        for area in window.screen.areas:
            if area.type == 'CADEX_TRAINING':
                area.tag_redraw()


def poll():
    """The timer body: notice the file changed, ask for a redraw.

    Deliberately does no work beyond a stat. Blender draws a panel when it
    is told to and not otherwise, so without this a live run's numbers only
    move when the user moves the mouse over the editor -- which reads as a
    frozen run.
    """

    try:
        scene = bpy.context.scene
    except Exception:
        return POLL_SECONDS
    if scene is None:
        return POLL_SECONDS
    path = progress_path(scene)
    before = _cache.get(path)
    payload = read_progress(scene)
    if payload is not None and _cache.get(path) is not before:
        _redraw()
    return POLL_SECONDS


def register():
    # `bpy.app.timers` do not fire under `--background`, which is what the
    # gate runs in -- so everything above is written to be callable directly
    # and the gate calls it. The timer is the interactive convenience, not
    # the mechanism.
    if not bpy.app.timers.is_registered(poll):
        bpy.app.timers.register(poll, first_interval=POLL_SECONDS,
                                persistent=True)


def unregister():
    if bpy.app.timers.is_registered(poll):
        bpy.app.timers.unregister(poll)
    _cache.clear()
