# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A passed evaluation's shove video (ADR-571): the policy pushed, each push marked.

:mod:`film` draws what an evaluation's seeds did and knows no behaviour.
This draws one episode the evaluation child played after a pass, under the
shoves the task was trained against (``evaluate_runner.shove_task``), with
:mod:`film`'s solids, materials, stage and video. Everything written beside
the video -- each push's force, direction and start, the recovery from it
and how the episode ended -- is read from that episode's draws and the
engine's measurement of it, never assumed: a design that falls is filmed
and reported falling.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import video as studio_video
from .film import (
    FilmError,
    _Stage,
    _pixel,
    _require,
    _video,
    film_digest,
    materials,
    read_trace,
    retained_solids,
)
from .studio import STUDIO as studio_render

SHOVE_VIDEO = "shove.webm"
#: The episode's trace, beside the evaluation's; ``*-trace.json`` stays out
#: of the project's history.
SHOVE_TRACE = "shove-trace.json"
SHOVE_SCHEMA = "cadex-shove-film-v1"
#: A push is marked from when it lands for at least this long, so a tenth of
#: a second of force is seen at ten frames a second. The colour is the
#: dashboard's ``--warn``; the arrow's length grows with the push.
SHOVE_MARK_S = 0.6
SHOVE_COLOUR = (255, 224, 138)
SHOVE_ARROW = (0.07, 0.09)


def trained_shoves(task: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The shoves a task bundle trained its policy against: its non-sustained disturbances."""

    return [entry for entry in task.get("disturbance") or ()
            if isinstance(entry, Mapping) and not entry.get("sustained")]


def shove_pushes(measured: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each push the shove episode applied, read from the episode itself.

    The force, direction and start are what the seed drew; the duration and
    the body are the spec entry's; the recovery is the engine's reading of
    the frames, seconds from the push's end to the first full rest, or
    ``None`` for a push the design never came to rest after inside the
    episode. ``recovered`` is ``None`` where recovery was not read at all (a
    mechanism with no floating base).
    """

    row = measured["seeds"][0]
    entries = list((measured.get("spec") or {}).get("disturbance") or [])
    draws = list((row.get("drawn") or {}).get("disturbance") or [])
    _require(len(entries) == len(draws), "the shove episode drew a push its spec does not declare")
    detail = row.get("detail") or {}
    read = "recovery_s" in detail
    times = list(detail.get("recovery_s") or [])
    pushes = []
    for entry, draw in zip(entries, draws):
        if entry.get("sustained"):
            continue
        start, duration = float(draw["start_s"]), float(entry["duration_s"])
        recovery = times[len(pushes)] if read and len(pushes) < len(times) else None
        pushes.append({
            "number": len(pushes) + 1, "label": str(draw.get("label") or entry.get("label") or ""),
            "body": str(entry["body"]), "newtons": float(draw["newtons"]),
            "newtons_range": [float(entry["newtons_low"]), float(entry["newtons_high"])],
            "azimuth_deg": math.degrees(float(draw["azimuth_rad"])),
            "force_n": [float(value) for value in draw["force_n"]],
            "start_s": start, "duration_s": duration, "end_s": start + duration,
            "recovery_s": recovery, "recovered": (recovery is not None) if read else None,
        })
    return pushes


def shove_outcome(measured: Mapping[str, Any], pushes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """How the shove episode ended, from the episode: whether the design was
    still up at the horizon, and how many pushes it came to rest after."""

    episode = measured["seeds"][0].get("episode") or {}
    horizon = float(((measured.get("spec") or {}).get("episode") or {}).get("episode_seconds")
                    or episode.get("duration_s") or 0.0)
    termination = str(episode.get("termination") or "")
    landed = [push for push in pushes if push["start_s"] < float(episode.get("duration_s") or 0.0)]
    read = all(push["recovered"] is not None for push in pushes)
    return {
        "stayed_up": not termination, "termination": termination or None,
        "duration_s": float(episode.get("duration_s") or 0.0), "horizon_s": horizon,
        "pushes_landed": len(landed),
        "recovered": sum(1 for push in pushes if push["recovered"]) if read else None,
    }


def shove_caption(seed: int, pushes: Sequence[Mapping[str, Any]], outcome: Mapping[str, Any]) -> str:
    """One line beside the video: every push, its recovery, and the ending."""

    parts = [f"seed {seed}"]
    for push in pushes:
        if push["start_s"] >= outcome["duration_s"]:
            parts.append("push {:d} never landed: the episode had ended".format(push["number"]))
            continue
        after = ("" if push["recovered"] is None else
                 ", recovered in {:.2f} s".format(push["recovery_s"]) if push["recovered"] else
                 ", not settled")
        parts.append("push {:d}: {:.2f} N at {:.2f} s{:s}".format(
            push["number"], push["newtons"], push["start_s"], after))
    parts.append("stayed up for the whole {:.1f} s".format(outcome["horizon_s"]) if outcome["stayed_up"]
                 else "fell: {:s} at {:.2f} s".format(str(outcome["termination"]), outcome["duration_s"]))
    return " · ".join(parts)


def _arrow(canvas, tip: tuple[float, float], unit: tuple[float, float], length: float,
           colour, width: int) -> None:
    """An arrow ``length`` px long pointing along ``unit`` with its head at ``tip``."""

    (x, y), (ux, uy) = tip, unit
    canvas.line(x - ux * length, y - uy * length, x, y, colour, width)
    for turn in (0.5, -0.5):
        c, s = math.cos(math.pi - turn), math.sin(math.pi - turn)
        head = 0.3 * length
        canvas.line(x, y, x + (ux * c - uy * s) * head, y + (ux * s + uy * c) * head, colour, width)


def shove_marks(stage: _Stage, frames: Sequence[Mapping[str, Any]], times: Sequence[float],
                pushes: Sequence[Mapping[str, Any]], outcome: Mapping[str, Any]):
    """``draw(index, pixels, size, bounds)`` for the shove video.

    From when a push lands, for :data:`SHOVE_MARK_S` or the push, whichever
    is longer: an arrow in the push's direction ending at the pushed body's
    centre, with its force beside it. All along, top left, one line per push
    that has landed, with its recovery once the design has come to rest; on
    the last frame, how the episode ended.
    """

    basis = studio_render.HERO
    right, up = basis[0], basis[1]
    top = max(push["newtons_range"][1] for push in pushes) or 1.0
    last = len(times) - 1

    def draw(at: int, pixels: bytearray, size: int, bounds) -> bool:
        canvas = studio_render.Canvas(size, size, (0, 0, 0))
        canvas.pixels = pixels
        now = times[at]
        marked = False
        for push in pushes:
            if not push["start_s"] <= now + 1e-9 < push["start_s"] + max(SHOVE_MARK_S, push["duration_s"]):
                continue
            force = push["force_n"]
            across = sum(f * r for f, r in zip(force, right))
            above = sum(f * u for f, u in zip(force, up))
            norm = math.hypot(across, above)
            unit = (across / norm, -above / norm) if norm > 1e-9 else (1.0, 0.0)
            tip = _pixel(size, basis, bounds, stage.centre(frames[at]["component_placements"], push["body"]))
            length = size * (SHOVE_ARROW[0] + SHOVE_ARROW[1] * push["newtons"] / top)
            _arrow(canvas, tip, unit, length, SHOVE_COLOUR, 3)
            label = "{:.2f} N".format(push["newtons"])
            tail = (tip[0] - unit[0] * length, tip[1] - unit[1] * length)
            x = tail[0] - (studio_render.text_width(label, 2) + 6 if unit[0] > 0 else -6)
            canvas.text(round(x), round(tail[1] - 7), label, 2, SHOVE_COLOUR)
            marked = True
        y = 14
        for push in pushes:
            if push["start_s"] > now + 1e-9:
                break
            line = "push {:d}  {:.2f} N  at {:.2f} s".format(push["number"], push["newtons"], push["start_s"])
            if push["recovered"] and now + 1e-9 >= push["end_s"] + push["recovery_s"]:
                line += "  ·  recovered in {:.2f} s".format(push["recovery_s"])
            elif push["recovered"] is False and at == last:
                line += "  ·  not settled"
            canvas.text(14, y, line, 2, studio_render.PALETTE["ink"])
            y += 22
        if at == last:
            ending = ("stayed up" if outcome["stayed_up"] else
                      "fell: {:s}".format(str(outcome["termination"])))
            canvas.text(14, y, ending, 2, studio_render.PALETTE["ink"] if outcome["stayed_up"] else SHOVE_COLOUR)
        return marked

    return draw


def film_shoves(root: Path, out: Path, report: Mapping[str, Any], measured: Mapping[str, Any],
                inventory: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The shove episode as a studio video, every push marked when it lands.

    Drawn from the episode's own trace, the file the engine measured, with
    the accepted attempt's retained solids and materials, as the
    evaluation's own video is.
    """

    row = measured["seeds"][0]
    pushes = shove_pushes(measured)
    outcome = shove_outcome(measured, pushes)
    flats, sources, world = retained_solids(root, str(report.get("model_output") or ""))
    try:
        meshes, _geometry = studio_video.drawn_meshes(
            {name: flat for name, flat in flats.items() if name not in world})
    except ValueError as exc:
        raise FilmError(str(exc)) from exc
    looks, source = materials(sources, list(meshes), str(report.get("accepted_revision") or ""), inventory)
    stage = _Stage(meshes, looks, {name: flats[name] for name in world})
    missing = sorted({push["body"] for push in pushes} - set(stage.names))
    _require(not missing, "a pushed body is not one of the solids drawn: " + ", ".join(missing))
    frames, times, _target = read_trace(out / str(row["trace"]["file"]), str(row["trace"]["sha256"]),
                                        list(flats))
    floor, _floor_source = stage.floor(frames, (measured.get("rig") or {}).get("floor_mm"))
    world_meshes = {name: [tuple(tuple(flat[k + 3*c:k + 3*c + 3]) for c in range(3))
                           for k in range(0, len(flat), 9)] for name, flat in flats.items() if name in world}
    try:
        studio_video.ffmpeg()
    except ValueError as exc:
        raise FilmError(f"video: {exc}") from exc
    video = _video(stage.names + sorted(world), looks, source, {**meshes, **world_meshes}, frames, times,
                   out, int(row["seed"]), floor, name=SHOVE_VIDEO,
                   draw=shove_marks(stage, frames, times, pushes, outcome))
    return {**video, "style_sha256": film_digest(), "materials": source,
            "marks": "an arrow in --warn ending at the pushed body's centre, in the push's direction, "
                     "its length growing with the force, from when it lands for {:g} s; top left, each "
                     "push that has landed and its recovery once at rest; the ending on the last "
                     "frame".format(SHOVE_MARK_S)}
