# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What a design turn leaves for a person to read: its transcript and its
``look`` images (ADR-526).

``cadex -p`` keeps each turn under the project's ``turns/<id>/``:
``transcript.txt`` is everything the turn wrote to stderr -- the tool-call
lines and the model's prose, exactly what a terminal shows -- and each
picture the ``look`` tool handed the model is a ``look-NN-<view>.png``
beside it. ``turn.json`` says what the turn was and how it ended. The CLI
is the only writer; a turn started from the dashboard is a ``cadex -p``
child, so it lands here the same way, and the dashboard only reads (A3).

Bounded three ways: a transcript stops at :data:`TRANSCRIPT_LIMIT`
characters and says so, a turn keeps at most :data:`LOOKS_PER_TURN`
images, and a project keeps its last :data:`TURNS_KEPT` turns. The
directory ignores itself in the project's repository: a transcript is a
log, not the design.
"""

from __future__ import annotations

import contextlib
import datetime as _datetime
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import threading
from typing import Any, Callable, Iterator, Mapping

TURNS_DIRNAME = "turns"
RECORD_NAME = "turn.json"
TRANSCRIPT_NAME = "transcript.txt"
SCHEMA = "cadex-turn-v1"
#: Bound on the transcript kept for one turn, in characters; past it the
#: tail is dropped and the transcript says so. The dashboard holds a live
#: turn's transcript to the same bound.
TRANSCRIPT_LIMIT = 4 * 1024 * 1024
#: How many ``look`` images one turn keeps; later ones are counted, not kept.
LOOKS_PER_TURN = 24
#: How many turns a project keeps, newest first.
TURNS_KEPT = 20

#: What ``turn.json``'s ``reply`` keeps of the run's envelope: the keys the
#: dashboard's live turn reports when its child ends.
REPLY_KEYS = ("accepted_revision", "digest", "params", "error", "notes", "session_id", "attachments", "usage")

TURN_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{6}$")
LOOK_NAME = re.compile(r"^look-\d{2}-[a-z_]{1,16}\.png$")


def _now() -> str:
    return _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    scratch = path.with_name(path.name + ".tmp")
    scratch.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(scratch, path)


class TurnRecorder:
    """One turn's directory, written as the turn runs."""

    def __init__(self, project_root: Path | str, prompt: str, *,
                 attachments: list[dict[str, Any]] | None = None, resume: bool = False) -> None:
        base = Path(project_root) / TURNS_DIRNAME
        base.mkdir(parents=True, exist_ok=True)
        ignore = base / ".gitignore"
        if not ignore.exists():
            ignore.write_text("# Turn transcripts and look images (ADR-526): logs, not the design.\n*\n",
                              encoding="utf-8")
        stamp = _datetime.datetime.now(_datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.id = f"{stamp}-{secrets.token_hex(3)}"
        self.dir = base / self.id
        self.dir.mkdir()
        self._lock = threading.Lock()
        self._length = 0
        self._truncated = False
        self._transcript = (self.dir / TRANSCRIPT_NAME).open("w", encoding="utf-8")
        self.record: dict[str, Any] = {
            "schema": SCHEMA, "id": self.id, "prompt": prompt, "resume": bool(resume),
            "attachments": list(attachments or []), "started": _now(), "finished": None,
            "pid": os.getpid(), "state": "running", "looks": [], "looks_dropped": 0, "reply": None,
        }
        self._save()
        _prune(base, keep=self.id)

    def _save(self) -> None:
        _write_json(self.dir / RECORD_NAME, self.record)

    def write(self, text: str) -> None:
        """Append to the transcript, flushed so a reader sees it at once."""

        with self._lock:
            if self._truncated or self._transcript.closed or not text:
                return
            if self._length + len(text) > TRANSCRIPT_LIMIT:
                text = "\n[transcript truncated at %d characters]\n" % TRANSCRIPT_LIMIT
                self._truncated = True
            try:
                self._transcript.write(text)
                self._transcript.flush()
            except OSError:
                return
            self._length += len(text)

    def look(self, view: str, data: bytes) -> None:
        """Keep one picture the ``look`` tool gave the model."""

        with self._lock:
            looks = self.record["looks"]
            if len(looks) >= LOOKS_PER_TURN:
                self.record["looks_dropped"] += 1
            else:
                name = f"look-{len(looks) + 1:02d}-{re.sub(r'[^a-z_]', '', str(view).lower())[:16] or 'view'}.png"
                try:
                    (self.dir / name).write_bytes(data)
                except OSError:
                    return
                looks.append({"name": name, "view": str(view), "bytes": len(data)})
            self._save()

    def finish(self, report: Any, code: int) -> None:
        """Close the transcript and say how the turn ended."""

        with self._lock:
            if not self._transcript.closed:
                self._transcript.close()
            envelope = report.to_json()
            reply = {key: envelope[key] for key in REPLY_KEYS if key in envelope}
            reply.update(ok=bool(report.ok), exit=code)
            self.record.update(finished=_now(), state="done" if report.ok else "failed", reply=reply)
            self._save()

    @contextlib.contextmanager
    def capture(self) -> Iterator[None]:
        """Copy everything written to ``sys.stderr`` into the transcript."""

        original = sys.stderr
        sys.stderr = _Tee(original, self.write)
        try:
            yield
        finally:
            sys.stderr = original


class _Tee:
    """A text stream that writes through and hands each write to ``sink``."""

    def __init__(self, stream: Any, sink: Callable[[str], None]) -> None:
        self._stream, self._sink = stream, sink

    def write(self, text: str) -> int:
        written = self._stream.write(text)
        self._sink(text)
        return written

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


def _prune(base: Path, *, keep: str) -> None:
    ids = sorted((child.name for child in base.iterdir() if child.is_dir() and TURN_ID.match(child.name)),
                 reverse=True)
    for name in ids[TURNS_KEPT:]:
        if name != keep:
            shutil.rmtree(base / name, ignore_errors=True)


def _alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True
    return True


def latest_turn(project_root: Path | str) -> dict[str, Any] | None:
    """The project's newest stored turn's record, or ``None``.

    A record still ``running`` whose process is gone reads ``interrupted``:
    the turn was killed before it could say how it ended.
    """

    base = Path(project_root) / TURNS_DIRNAME
    if not base.is_dir():
        return None
    for name in sorted((child.name for child in base.iterdir() if TURN_ID.match(child.name)), reverse=True):
        try:
            record = json.loads((base / name / RECORD_NAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict) or record.get("id") != name:
            continue
        if record.get("state") == "running" and not _alive(record.get("pid")):
            record["state"] = "interrupted"
        return record
    return None


def read_transcript(project_root: Path | str, turn_id: str) -> str:
    if not TURN_ID.match(turn_id):
        return ""
    try:
        return (Path(project_root) / TURNS_DIRNAME / turn_id / TRANSCRIPT_NAME).read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return ""


def turn_file(project_root: Path | str, turn_id: str, name: str) -> Path | None:
    """A stored ``look`` image, when the names are the store's own and it is a file inside the project."""

    if not TURN_ID.match(turn_id) or not LOOK_NAME.match(name):
        return None
    root = Path(project_root).resolve()
    path = (root / TURNS_DIRNAME / turn_id / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path
