# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A person's comments on a design, and how the next turn receives them.

A comment is the owner's light steering (orun2 D2, ADR-505): a sentence on
the whole design or on one part picked in the viewer, left while no turn is
asking for it. ``cadex comment`` writes it and the dashboard runs that same
command (A3: one write path); the next ``cadex -p`` turn on the project
receives every comment not yet delivered, ahead of its prompt, and once the
turn has run they are marked delivered so the turn after does not see them
again.

The file is ``comments.jsonl`` in the project root, append-only, one JSON
object per line, of two kinds::

    {"kind": "comment", "id": "c-…", "at": "…Z", "text": "…", "part": "post",
     "revision": "<accepted revision when it was left>"}
    {"kind": "delivered", "ids": ["c-…"], "at": "…Z", "session_id": "…"}

``part`` is empty for a comment on the whole design. Appending rather than
rewriting keeps a dashboard write and a turn's delivery from racing each
other into a lost line, and the file is the history: the project commit
after an accepted turn carries it, like the project's other documents. A
line that does not parse is skipped, never fatal.
"""

from __future__ import annotations

import datetime as _datetime
import json
import os
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

COMMENTS_NAME = "comments.jsonl"
#: Bound on one comment, in characters: a note, not a brief.
COMMENT_LIMIT = 4_000
#: Bound on a part name, in characters.
PART_LIMIT = 200
#: Bound on the file a reader parses, in bytes; past it the oldest lines go unread.
READ_LIMIT = 4 * 1024 * 1024


def _now() -> str:
    return _datetime.datetime.now(_datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def comments_path(root: Path | str) -> Path:
    return Path(root).expanduser() / COMMENTS_NAME


def _append(root: Path | str, entry: Mapping[str, Any]) -> None:
    path = comments_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(dict(entry), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    # One write of one line under O_APPEND: two writers interleave whole lines.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def add_comment(root: Path | str, text: str, *, part: str = "", revision: str = "") -> dict[str, Any]:
    """Append one comment and return it; ``ValueError`` when it is not one."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("a comment must be non-empty text.")
    text = text.strip()
    if len(text) > COMMENT_LIMIT or "\x00" in text:
        raise ValueError(f"a comment is at most {COMMENT_LIMIT} characters of text.")
    part = (part or "").strip()
    if len(part) > PART_LIMIT or "\x00" in part or "\n" in part:
        raise ValueError(f"a part name is one line of at most {PART_LIMIT} characters.")
    entry = {"kind": "comment", "id": "c-" + secrets.token_hex(6), "at": _now(),
             "text": text, "part": part, "revision": revision or ""}
    _append(root, entry)
    return {key: value for key, value in entry.items() if key != "kind"} | {"delivered": ""}


def read_comments(root: Path | str) -> list[dict[str, Any]]:
    """Every comment, oldest first, each with ``delivered`` (when, or empty)."""

    path = comments_path(root)
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            handle.seek(max(0, size - READ_LIMIT))
            raw = handle.read()
    except OSError:
        return []
    if size > READ_LIMIT:
        raw = raw.split(b"\n", 1)[-1]
    comments: dict[str, dict[str, Any]] = {}
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("kind") == "comment" and isinstance(entry.get("id"), str) \
                and isinstance(entry.get("text"), str):
            comments[entry["id"]] = {"id": entry["id"], "at": str(entry.get("at") or ""),
                                     "text": entry["text"], "part": str(entry.get("part") or ""),
                                     "revision": str(entry.get("revision") or ""), "delivered": ""}
        elif entry.get("kind") == "delivered" and isinstance(entry.get("ids"), list):
            for comment_id in entry["ids"]:
                if comment_id in comments and not comments[comment_id]["delivered"]:
                    comments[comment_id]["delivered"] = str(entry.get("at") or "")
    return list(comments.values())


def pending_comments(root: Path | str) -> list[dict[str, Any]]:
    """The comments no turn has received yet, oldest first."""

    return [comment for comment in read_comments(root) if not comment["delivered"]]


def mark_delivered(root: Path | str, comments: Iterable[Mapping[str, Any]], *, session_id: str = "") -> str:
    """Record that a turn received ``comments``; returns when, or empty for none."""

    ids = [str(comment["id"]) for comment in comments]
    if not ids:
        return ""
    at = _now()
    _append(root, {"kind": "delivered", "ids": ids, "at": at, "session_id": session_id})
    return at


def with_comments(prompt: str, comments: Iterable[Mapping[str, Any]]) -> str:
    """The prompt a turn is given: the owner's pending comments, then the prompt."""

    lines = []
    for comment in comments:
        where = f"on part {comment['part']}" if comment.get("part") else "on the whole design"
        lines.append(f"- ({where}) {comment['text']}")
    if not lines:
        return prompt
    return ("The owner left these comments on the design since the last turn; "
            "take them into account:\n" + "\n".join(lines) + "\n\n" + prompt)
