# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Saved poses (ADR-969): a named set of joint values, kept in the project.

The dashboard's Pose editor poses the model by its joints and hands the pose
over as JSON (copied or downloaded: the page writes nothing, ADR-537);
``cadex pose save`` stores it as ``poses/<name>.json``, where the next build,
a person or a trainer can read it. A pose is joint values in MuJoCo's own
units (radians for a hinge, metres for a slide) keyed by the MJCF joint's
name, with the model it was posed on, so a reader can tell a pose from a
design that has since changed.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

POSE_SCHEMA = "cadex-pose-v1"
POSES_DIRNAME = "poses"
#: A pose's name is its file's stem.
POSE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
#: The most joints a pose may name, and the most poses a project lists.
POSE_MAXIMUM_JOINTS = 512
POSE_MAXIMUM_LISTED = 200
POSE_READ_LIMIT = 256 * 1024


class PoseError(ValueError):
    """A pose that cannot be stored or read, and why."""


def check_pose(raw: Any, *, name: str | None = None) -> dict[str, Any]:
    """The pose ``raw`` as stored: its schema, name, note, joints and model.

    ``name`` overrides the pose's own. Raises :class:`PoseError` on anything
    a reader could not trust: no joints, a value that is not a finite
    number, a name that is not a file stem.
    """

    if not isinstance(raw, Mapping):
        raise PoseError("a pose is a JSON object.")
    if raw.get("schema") not in (None, POSE_SCHEMA):
        raise PoseError(f"a pose's schema is {POSE_SCHEMA!r}, not {raw.get('schema')!r}.")
    chosen = str(name if name is not None else raw.get("name") or "")
    if not POSE_NAME.fullmatch(chosen):
        raise PoseError(f"a pose's name is letters, digits, '_', '.' or '-' (at most 64), not {chosen!r}.")
    joints = raw.get("joints")
    if not isinstance(joints, Mapping) or not joints:
        raise PoseError("a pose names at least one joint in 'joints'.")
    if len(joints) > POSE_MAXIMUM_JOINTS:
        raise PoseError(f"a pose names at most {POSE_MAXIMUM_JOINTS} joints.")
    values: dict[str, float] = {}
    for joint, value in joints.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise PoseError(f"joint {joint!r}: a value is a finite number (rad or m), not {value!r}.")
        values[str(joint)] = float(value)
    model = raw.get("model") if isinstance(raw.get("model"), Mapping) else {}
    pose = {"schema": POSE_SCHEMA, "name": chosen, "note": str(raw.get("note") or ""),
            "joints": values,
            "model": {key: str(model[key]) for key in ("source", "sha256") if model.get(key)}}
    if raw.get("saved_at"):
        pose["saved_at"] = str(raw["saved_at"])
    return pose


def write_pose(project_root: Path | str, raw: Any, *, name: str | None = None,
               replace: bool = False) -> tuple[dict[str, Any], Path]:
    """Store a pose as ``poses/<name>.json``; refuse to overwrite unless ``replace``."""

    root = Path(project_root).expanduser()
    pose = check_pose(raw, name=name)
    pose["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    folder = root / POSES_DIRNAME
    path = folder / f"{pose['name']}.json"
    if path.exists() and not replace:
        raise PoseError(f"a pose named {pose['name']!r} is already saved; --replace overwrites it.")
    folder.mkdir(exist_ok=True)
    path.write_text(json.dumps(pose, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pose, path


def pose_listing(project_root: Path | str) -> list[dict[str, Any]]:
    """Every readable pose under ``poses/``, by name; one that does not read is
    listed with its ``error`` and no joints."""

    folder = Path(project_root).expanduser() / POSES_DIRNAME
    if not folder.is_dir() or folder.is_symlink():
        return []
    rows = []
    for path in sorted(folder.glob("*.json"))[:POSE_MAXIMUM_LISTED]:
        stem = path.stem
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > POSE_READ_LIMIT:
                raise PoseError("not a regular file under the read limit")
            rows.append(check_pose(json.loads(path.read_text(encoding="utf-8")), name=stem))
        except (OSError, ValueError) as exc:
            rows.append({"schema": POSE_SCHEMA, "name": stem, "error": str(exc)})
    return rows
