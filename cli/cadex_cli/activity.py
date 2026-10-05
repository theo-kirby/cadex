# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What the agent is doing: one line per ``cadex mcp`` tool call (orun3 V4, ADR-549).

The MCP server is the only place every call the owner's agent makes passes
through, so it is where they are written down: ``review/activity.jsonl`` in
the project, a directory the CLI already owns and the project's own git
ignores (ADR-194). Each line is one JSON object:

- ``t`` -- when the call finished, UTC, to the second;
- ``tool`` -- the tool's name;
- ``args`` -- a short summary of the arguments, never the arguments: a
  scalar is shown, a long or multi-line string only by its length, a list
  only by its size, an object only by its keys (:func:`summarize_arguments`);
- ``outcome`` -- ``ok`` or ``error``;
- ``detail`` -- the bridge's one-line summary of the reply, or the error;
- ``ms`` -- how long the call took.

Every field is bounded, so a line is too. The file is bounded as well: once
an append takes it past :data:`MAX_BYTES`, it is rewritten in place
(atomically) keeping the newest lines that fit in half of that. Writing
never fails the call it describes.

:func:`read_activity` is the read side, served in ``/api/project`` as
``activity``. The page only reads it (ADR-537).
"""

from __future__ import annotations

import datetime as _datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

ACTIVITY_PATH = Path("review") / "activity.jsonl"
#: The file's bound; a rotation keeps the newest lines within half of it.
MAX_BYTES = 64 * 1024
#: How many entries ``/api/project`` carries, newest first.
READ_LIMIT = 10
#: The longest ``args`` and ``detail`` may be, in characters.
FIELD_CHARS = 160
#: A string argument longer than this is shown only by its length.
VALUE_CHARS = 40


def activity_path(project_root: Path | str) -> Path:
    return Path(project_root).expanduser() / ACTIVITY_PATH


def _clip(text: str, limit: int = FIELD_CHARS) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _value(value: Any) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        if len(value) > VALUE_CHARS or "\n" in value:
            return f"<{len(value)} chars>"
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return f"[{len(value)}]"
    if isinstance(value, Mapping):
        # The names a call touched (which parameters a set_params set), not their values.
        names = ",".join(str(key) for key in value)
        return f"{{{names}}}" if len(names) <= VALUE_CHARS else f"{{{len(value)} keys}}"
    return f"<{type(value).__name__}>"


def summarize_arguments(arguments: Mapping[str, Any]) -> str:
    """``key=value`` per argument, sorted, each value shortened; never the whole."""

    return _clip(", ".join(f"{key}={_value(arguments[key])}" for key in sorted(arguments)))


def reply_error(reply: Mapping[str, Any]) -> str:
    """The reason in an error reply's first text block: its ``error`` when JSON."""

    for block in reply.get("content") or []:
        if isinstance(block, Mapping) and block.get("type") == "text":
            text = str(block.get("text") or "")
            try:
                parsed = json.loads(text)
            except ValueError:
                return _clip(text)
            if isinstance(parsed, Mapping):
                code = str(parsed.get("failure_code") or "")
                error = str(parsed.get("error") or "")
                return _clip(f"{code}: {error}" if code and error else code or error or text)
            return _clip(text)
    return ""


def append_activity(project_root: Path | str, tool: str, arguments: Mapping[str, Any], *,
                    ok: bool, detail: str, ms: float, now: float | None = None) -> None:
    """Append one call's line and keep the file under :data:`MAX_BYTES`. Never raises."""

    stamp = _datetime.datetime.fromtimestamp(
        now if now is not None else _datetime.datetime.now().timestamp(), _datetime.timezone.utc)
    entry = {
        "t": stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "tool": _clip(tool, 64),
        "args": summarize_arguments(arguments),
        "outcome": "ok" if ok else "error",
        "detail": _clip(detail),
        "ms": int(round(max(ms, 0.0))),
    }
    line = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
    path = activity_path(project_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as handle:
            handle.write(line)
            size = handle.tell()
        if size > MAX_BYTES:
            _rotate(path)
    except OSError:
        pass


def _rotate(path: Path) -> None:
    """Rewrite ``path`` keeping the newest whole lines that fit in half the bound."""

    lines = path.read_bytes().splitlines(keepends=True)
    kept: list[bytes] = []
    total = 0
    for line in reversed(lines):
        if total + len(line) > MAX_BYTES // 2:
            break
        kept.append(line)
        total += len(line)
    scratch = path.with_name(path.name + f".{os.getpid()}.tmp")
    scratch.write_bytes(b"".join(reversed(kept)))
    os.replace(scratch, path)


def read_activity(project_root: Path | str, limit: int = READ_LIMIT) -> dict[str, Any]:
    """The newest ``limit`` entries, newest first, or why there are none."""

    path = activity_path(project_root)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {"available": False, "entries": [],
                "reason": "no tool call through cadex mcp has been logged in this project"}
    except OSError as exc:
        return {"available": False, "entries": [], "reason": f"the activity log could not be read: {exc}"}
    entries: list[dict[str, Any]] = []
    for line in reversed(raw.splitlines()):
        try:
            entry = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue  # a line still being appended
        if isinstance(entry, dict) and entry.get("tool"):
            entries.append(entry)
            if len(entries) >= limit:
                break
    if not entries:
        return {"available": False, "entries": [], "reason": "the activity log has no entries"}
    return {"available": True, "entries": entries, "reason": ""}
