# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The project's runs, in the Training editor (cadex ADR-450).

``cadex walk`` leaves one directory per run under ``<project>/runs/``: the
run record ``run.json`` (``cadex-run-record-v1``, docs/CLI.md "The run
record"), or only ``review.json`` for a run from before the record existed,
plus the trainer's ``train/progress.json`` and, once rendered, the policy
video's ``video.json``. The review dashboard (``cadex review``) shows those
files in a browser; this module shows the same files in the app, so a long
run can be watched from the editor that already shows a live one.

**It reads files, as the dashboard does, and nothing else.** No engine, no
rebuild, no network, and no code from ``cli/``: the files are the contract,
and this is a second reader of them written against docs/CLI.md. It is
deliberately the *smaller* reader. The dashboard also resolves every
recorded reference, checks video and snapshot digests and the policy store;
those need hashing, and a panel redraw must never hash a video. A run's
problems stay the dashboard's to report.

Every read is keyed on the file's ``(mtime, size)``, so an unchanged run
costs one stat per poll. A run directory that resolves outside
``<project>/runs`` (a symlink out of the project) is listed and never read.

The pure half -- everything above ``-- the bpy half --`` -- imports ``json``
and ``os`` only, and the no-engine suite exercises it.
"""

import json
import os

RUNS_DIRNAME = "runs"
RUN_RECORD_NAME = "run.json"
RUN_RECORD_SCHEMA = "cadex-run-record-v1"
REVIEW_NAME = "review.json"
VIDEO_NAME = "video.json"
VIDEO_SCHEMA = "cadex-run-video-v1"
PROGRESS_PATH = ("train", "progress.json")
#: The trainer's own report, the schema ``cadex_training`` reads from the
#: live mirror. One format, two places it lands.
PROGRESS_SCHEMA = "cadex-training-progress-v1"
MANIFEST_NAME = "script.json"
MANIFEST_SCHEMA = "cadex-project-script-v1"

#: Seconds between looks. A trainer reports at most once an iteration.
POLL_SECONDS = 2.0
#: Rows the panel draws; the rest are counted, not drawn.
PANEL_ROWS = 12

#: A record's ``status`` in words, as a reader who arrives later needs it.
#: ``running`` cannot tell a live walk from a killed one, so it says both.
OUTCOMES = {
    "running": "running, or interrupted",
    "ok": "completed",
    "failed": "failed",
    "pending": "training launched, not collected",
    "unrecorded": "legacy run (review.json only)",
    "unreadable": "record unreadable",
    "empty": "no record",
}

#: path -> ((mtime_ns, size), payload)
_cache = {}


def _read_json(path):
    """The JSON object at ``path``, or ``None``; re-read only when it moved."""
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
        return None  # mid-write: not cached, so the next look reads it
    if not isinstance(payload, dict):
        payload = None
    _cache[path] = (signature, payload)
    return payload


def accepted_revision(root):
    """The project's accepted revision now, from its manifest, or ``""``."""
    manifest = _read_json(os.path.join(root, MANIFEST_NAME)) or {}
    if manifest.get("schema") != MANIFEST_SCHEMA:
        return ""
    return str(manifest.get("accepted_revision") or "")


def _inside(base, path):
    base = os.path.realpath(base)
    return os.path.commonpath([base, os.path.realpath(path)]) == base


def read_run(root, name):
    """One run as the panel shows it: identity, outcome, live progress."""
    runs = os.path.join(root, RUNS_DIRNAME)
    directory = os.path.join(runs, name)
    run = {"run": name, "source": None, "status": "empty", "recorded_at": "",
           "mode": "", "revision": "", "params": {}, "policy": "",
           "total_reward": None, "error": "", "progress": None, "video": None}
    if not _inside(runs, directory):
        run.update(status="unreadable", error="run directory escapes the project")
        run["outcome"] = OUTCOMES["unreadable"]
        return run
    record = _read_json(os.path.join(directory, RUN_RECORD_NAME))
    review = None if record is not None else _read_json(os.path.join(directory, REVIEW_NAME))
    if record is not None:
        run["source"] = RUN_RECORD_NAME
        if record.get("schema") != RUN_RECORD_SCHEMA:
            run.update(status="unreadable",
                       error="unknown record schema {!r}".format(record.get("schema")))
        else:
            model = record.get("model") or {}
            params = record.get("params") or {}
            policy = record.get("policy") or {}
            rollout = record.get("rollout") or {}
            run.update(status=str(record.get("status") or ""),
                       recorded_at=str(record.get("recorded_at") or ""),
                       mode=str(record.get("mode") or ""),
                       revision=str(model.get("accepted_revision") or ""),
                       params=dict(params.get("values") or {}),
                       policy=str(policy.get("name") or ""),
                       total_reward=rollout.get("total_reward"),
                       error=str(record.get("error") or ""))
    elif review is not None:
        run.update(source=REVIEW_NAME, status="unrecorded",
                   params=dict(review.get("params") or {}),
                   policy=str(review.get("weights") or ""),
                   total_reward=review.get("total_reward"))
        for leg in reversed(review.get("legs") or []):
            if isinstance(leg, dict) and leg.get("accepted_revision"):
                run["revision"] = str(leg["accepted_revision"])
                break
    progress = _read_json(os.path.join(directory, *PROGRESS_PATH))
    if progress is not None and progress.get("schema") == PROGRESS_SCHEMA:
        run["progress"] = progress
    video = _read_json(os.path.join(directory, VIDEO_NAME))
    if video is not None and video.get("schema") == VIDEO_SCHEMA:
        videos = [v for v in video.get("videos") or [] if isinstance(v, dict)]
        run["video"] = {"state": str(video.get("state") or ""), "count": len(videos),
                        "path": str(videos[0].get("path") or "") if videos else ""}
    run["outcome"] = OUTCOMES.get(run["status"], "unknown status {!r}".format(run["status"]))
    return run


def read_runs(root):
    """``{"accepted", "runs"}``: every run under ``runs/``, newest first.

    Each run carries ``relation``: ``current`` when it ran on the accepted
    revision now, ``historical`` when on another, ``unknown`` when either
    side is not known -- the dashboard's three words for the same thing.
    """
    runs_dir = os.path.join(root or "", RUNS_DIRNAME)
    try:
        names = sorted(entry.name for entry in os.scandir(runs_dir) if entry.is_dir())
    except OSError:
        names = []
    accepted = accepted_revision(root) if names else ""
    runs = [read_run(root, name) for name in names]
    for run in runs:
        run["relation"] = ("unknown" if not (accepted and run["revision"]) else
                           "current" if run["revision"] == accepted else "historical")
    runs.sort(key=lambda run: (run["recorded_at"], run["run"]), reverse=True)
    return {"accepted": accepted, "runs": runs}


def video_file(root, run):
    """The newest recorded video of ``run`` as an absolute path, or ``""``.

    ``video.json`` lists the newest first (``cadex video``). The path is
    run-relative; one that leaves the run directory is never offered.
    """
    relative = ((run or {}).get("video") or {}).get("path") or ""
    if not relative or os.path.isabs(relative) or ".." in relative.split("/"):
        return ""
    directory = os.path.join(root, RUNS_DIRNAME, run["run"])
    path = os.path.join(directory, relative)
    return path if _inside(directory, path) and os.path.isfile(path) else ""


def is_live(run):
    progress = run.get("progress") or {}
    return run.get("status") == "running" and str(progress.get("state") or "") in {"starting", "training"}


def progress_line(run):
    """``"419 / 2000 · +0.391/step"`` for a run that reports, else ``""``."""
    progress = run.get("progress")
    if not progress:
        return ""
    done = int(progress.get("iteration", -1) or -1) + 1
    total = int(progress.get("total") or 0)
    reward = progress.get("reward_per_step")
    text = "{:d} / {:d}".format(max(done, 0), max(total, 0))
    if reward is not None:
        text += "  {:+.4g}/step".format(float(reward))
    return text


# -- the bpy half -------------------------------------------------------------

import bpy  # noqa: E402  (the pure half above must not need it)
from bpy.types import Operator, Panel  # noqa: E402

#: The run the panel shows in full. Session state on the WindowManager: a
#: selection is not something a file should remember.
SELECTED_PROP = "cadex_run_selected"


def _root(scene):
    from . import cadex_backend
    return cadex_backend.project_root(scene)


def _selected(context, runs):
    name = str(getattr(context.window_manager, SELECTED_PROP, "") or "")
    return next((run for run in runs if run["run"] == name), None)


class CADEX_TRAINING_OT_select_run(Operator):
    """Show this run's identity and parameters"""

    bl_idname = "mesh_agent.select_run"
    bl_label = "Select Run"
    bl_options = {'INTERNAL'}

    run: bpy.props.StringProperty()

    def execute(self, context):
        current = getattr(context.window_manager, SELECTED_PROP, "")
        setattr(context.window_manager, SELECTED_PROP, "" if current == self.run else self.run)
        _redraw()
        return {'FINISHED'}


class CADEX_TRAINING_OT_play_run_video(Operator):
    """Open this run's newest policy video in the system's player"""

    bl_idname = "mesh_agent.play_run_video"
    bl_label = "Play Video"
    bl_options = {'INTERNAL'}

    run: bpy.props.StringProperty()

    def execute(self, context):
        root = _root(context.scene)
        path = ""
        if os.path.basename(self.run) == self.run:
            path = video_file(root, read_run(root, self.run))
        if not path:
            self.report({'WARNING'}, "This run has no video on disk.")
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=path)
        return {'FINISHED'}


_ICONS = {"running": 'PLAY', "ok": 'CHECKMARK', "failed": 'ERROR', "pending": 'TIME',
          "unrecorded": 'FILE', "unreadable": 'ERROR', "empty": 'QUESTION'}


class CADEX_TRAINING_PT_runs(Panel):
    """Every ``cadex walk`` run of this project, newest first."""

    bl_space_type = 'CADEX_TRAINING'
    bl_region_type = 'WINDOW'
    bl_label = "Runs"

    @classmethod
    def poll(cls, context):
        return bool(read_runs(_root(context.scene))["runs"])

    def draw(self, context):
        layout = self.layout
        review = read_runs(_root(context.scene))
        runs = review["runs"]
        selected = _selected(context, runs)
        column = layout.column(align=True)
        for run in runs[:PANEL_ROWS]:
            row = column.row(align=True)
            icon = 'PLAY' if is_live(run) else _ICONS.get(run["status"], 'INFO')
            text = run["run"]
            if run["relation"] == "historical":
                text += "  (older design)"
            op = row.operator(CADEX_TRAINING_OT_select_run.bl_idname, text=text, icon=icon,
                              depress=selected is run, emboss=selected is run)
            op.run = run["run"]
            sub = row.row()
            sub.enabled = False
            sub.label(text=progress_line(run) or run["outcome"])
        if len(runs) > PANEL_ROWS:
            note = layout.row()
            note.enabled = False
            note.label(text="...and {:d} older".format(len(runs) - PANEL_ROWS))
        if selected is not None:
            _draw_run(layout.box(), selected)


def _draw_run(box, run):
    box.label(text=run["run"], icon=_ICONS.get(run["status"], 'INFO'))
    column = box.column(align=True)
    column.enabled = False
    column.label(text="outcome      " + run["outcome"])
    if run["error"]:
        alert = box.row()
        alert.alert = True
        alert.label(text=run["error"][:160], icon='ERROR')
    column.label(text="recorded     " + (run["recorded_at"] or "-"))
    if run["mode"]:
        column.label(text="mode         " + run["mode"])
    column.label(text="revision     {:s}  ({:s})".format(run["revision"][:12] or "-",
                                                         run["relation"]))
    if run["policy"]:
        column.label(text="policy       " + run["policy"])
    if run["total_reward"] is not None:
        column.label(text="reward       {:+.6g}".format(float(run["total_reward"])))
    if run["progress"]:
        column.label(text="training     {:s}  ({:s})".format(
            progress_line(run), str(run["progress"].get("state") or "?")))
    if run["video"]:
        column.label(text="video        {:s}, {:d} file(s)".format(
            run["video"]["state"] or "?", run["video"]["count"]))
        if run["video"].get("path"):
            op = box.operator(CADEX_TRAINING_OT_play_run_video.bl_idname, icon='PLAY')
            op.run = run["run"]
    if run["params"]:
        params = box.column(align=True)
        params.enabled = False
        params.label(text="Parameters", icon='PROPERTIES')
        for key in sorted(run["params"])[:24]:
            params.label(text="  {:s} = {!s}".format(str(key), run["params"][key]))


def _redraw():
    manager = getattr(bpy.context, "window_manager", None)
    for window in getattr(manager, "windows", ()) or ():
        for area in window.screen.areas:
            if area.type == 'CADEX_TRAINING':
                area.tag_redraw()


_last_signature = None


def poll():
    """The timer: redraw the Training editor when any run file moved."""
    global _last_signature
    try:
        review = read_runs(_root(bpy.context.scene))
    except Exception:
        return POLL_SECONDS
    signature = tuple((run["run"], run["status"], progress_line(run),
                       (run["video"] or {}).get("state")) for run in review["runs"])
    if signature != _last_signature:
        _last_signature = signature
        _redraw()
    return POLL_SECONDS


classes = (CADEX_TRAINING_OT_select_run, CADEX_TRAINING_OT_play_run_video,
           CADEX_TRAINING_PT_runs)


def register():
    setattr(bpy.types.WindowManager, SELECTED_PROP, bpy.props.StringProperty(
        name="Selected Run", default=""))
    for cls in classes:
        bpy.utils.register_class(cls)
    # Timers do not fire under --background; the gate drives read_runs.
    if not bpy.app.timers.is_registered(poll):
        bpy.app.timers.register(poll, first_interval=POLL_SECONDS, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(poll):
        bpy.app.timers.unregister(poll)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    delattr(bpy.types.WindowManager, SELECTED_PROP)
    _cache.clear()
