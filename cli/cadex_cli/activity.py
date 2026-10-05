# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What the agent is doing: one line per ``cadex mcp`` tool call (orun3 V4, ADR-549).

The MCP server is the only place every call the owner's agent makes passes
through, so it is where they are written down: ``review/activity.jsonl`` in
the project, a directory the CLI already owns and the project's own git
ignores (ADR-194). Each line is one JSON object:

- ``t`` -- when the call finished, UTC, to the second (when it started, on
  an in-flight line);
- ``tool`` -- the tool's name;
- ``args`` -- a short summary of the arguments, never the arguments: a
  scalar is shown, a long or multi-line string only by its length, a list
  only by its size, an object only by its keys (:func:`summarize_arguments`);
- ``outcome`` -- ``ok`` or ``error``, or ``running`` on an in-flight line;
- ``detail`` -- the bridge's one-line summary of the reply, or the error;
- ``ms`` -- how long the call took;
- ``call`` -- which call the line belongs to.

A call writes two lines (ADR-553): :func:`begin_activity` an in-flight one
(``outcome: running``, with the server's ``pid``) when it starts, and
:func:`append_activity` the finished one, with the same ``call``, when it
returns. Reading newest first, a finished line hides its in-flight line, so
a call is one entry; an in-flight line whose process has gone is read as
``lost``, since that call will never return.

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
import itertools
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

_CALLS = itertools.count(1)


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


def _stamp(now: float | None) -> str:
    stamp = _datetime.datetime.fromtimestamp(
        now if now is not None else _datetime.datetime.now().timestamp(), _datetime.timezone.utc)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def begin_activity(project_root: Path | str, tool: str, arguments: Mapping[str, Any], *,
                   now: float | None = None) -> str:
    """Write a call's in-flight line as it starts, and return the ``call`` that
    :func:`append_activity` finishes it with (ADR-553). Never raises."""

    call = f"{os.getpid()}-{next(_CALLS)}"
    _write(project_root, {"t": _stamp(now), "tool": _clip(tool, 64), "args": summarize_arguments(arguments),
                          "outcome": "running", "detail": "", "ms": 0, "call": call, "pid": os.getpid()})
    return call


def append_activity(project_root: Path | str, tool: str, arguments: Mapping[str, Any], *,
                    ok: bool, detail: str, ms: float, now: float | None = None, call: str = "") -> None:
    """Append one call's line and keep the file under :data:`MAX_BYTES`. Never raises."""

    entry = {
        "t": _stamp(now),
        "tool": _clip(tool, 64),
        "args": summarize_arguments(arguments),
        "outcome": "ok" if ok else "error",
        "detail": _clip(detail),
        "ms": int(round(max(ms, 0.0))),
    }
    if call:
        entry["call"] = _clip(call, 32)
    _write(project_root, entry)


def _write(project_root: Path | str, entry: Mapping[str, Any]) -> None:
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


def _alive(pid: Any) -> bool:
    """Whether ``pid`` is a running process on this machine; unsure reads as alive."""

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


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
    finished: set[str] = set()
    for line in reversed(raw.splitlines()):
        try:
            entry = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue  # a line still being appended
        if isinstance(entry, dict) and entry.get("tool"):
            call = entry.get("call")
            if entry.get("outcome") == "running":
                if call in finished:
                    continue  # its finished line, newer, already stands for the call
                if not _alive(entry.get("pid")):
                    entry["outcome"] = "lost"
                    entry["detail"] = "the cadex mcp process ended before this call returned"
            elif isinstance(call, str):
                finished.add(call)
            entries.append(entry)
            if len(entries) >= limit:
                break
    if not entries:
        return {"available": False, "entries": [], "reason": "the activity log has no entries"}
    return {"available": True, "entries": entries, "reason": ""}
