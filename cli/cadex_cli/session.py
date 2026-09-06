# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project a CLI run works on: its lock, and the CLI's own state file.

Two things live here that the engine deliberately knows nothing about.

**The lockfile.** ``cadexd`` is one process per project, and a pipeline that
sweeps parameters will run several of these at once. Two engines opening the
same store would each restore it, each rebuild it, and each write
``script.json``. An advisory ``flock`` on ``<project_root>/.cadex-cli.lock``
turns that from silent corruption into a refusal with a readable message.

**``agent.json``.** The conversation's ``session_id`` and the model that
produced it have to survive between runs for ``--resume`` to mean anything.
They are the CLI's business and not the engine's, so they go in a
CLI-owned *sibling* of ``script.json``: the CLI reads the engine's state
file through ``inspect`` and never writes it. Keeping the two files apart is
what stops a CLI version bump from being able to break a project that the
shell also opens.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import datetime as _datetime
import errno
import json
import os
from pathlib import Path
from typing import Any, Iterator

#: The CLI's state file, beside the engine's ``script.json``.
AGENT_STATE_NAME = "agent.json"
AGENT_STATE_SCHEMA = "cadex-cli-agent-v1"
LOCK_NAME = ".cadex-cli.lock"


class ProjectBusy(RuntimeError):
    """Another Cadex CLI run holds this project."""


@dataclass(frozen=True)
class AgentState:
    """What the CLI remembers about a project between runs."""

    session_id: str = ""
    model: str = ""
    updated_at: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": AGENT_STATE_SCHEMA,
            "session_id": self.session_id,
            "model": self.model,
            "updated_at": self.updated_at,
        }


def agent_state_path(project_root: Path | str) -> Path:
    return Path(project_root) / AGENT_STATE_NAME


def read_agent_state(project_root: Path | str) -> AgentState:
    """Read ``agent.json``; an absent or unreadable file is simply empty.

    Unreadable is not an error on purpose. The worst a corrupt state file may
    do is cost one conversation's continuity — refusing to model over it
    would be a far bigger failure than the one it is reporting.
    """

    path = agent_state_path(project_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return AgentState()
    if not isinstance(payload, dict) or payload.get("schema") != AGENT_STATE_SCHEMA:
        return AgentState()
    return AgentState(
        session_id=str(payload.get("session_id") or ""),
        model=str(payload.get("model") or ""),
        updated_at=str(payload.get("updated_at") or ""),
    )


def write_agent_state(
    project_root: Path | str, *, session_id: str, model: str
) -> AgentState:
    """Persist the conversation id and the model that produced it."""

    state = AgentState(
        session_id=str(session_id or ""),
        model=str(model or ""),
        updated_at=_datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    )
    path = agent_state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written whole and renamed into place: a pipeline that kills a run
    # mid-write must not leave a half-file that read_agent_state has to
    # forgive.
    scratch = path.with_name(path.name + ".partial")
    scratch.write_text(
        json.dumps(state.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(scratch, path)
    return state


@contextmanager
def project_lock(project_root: Path | str, *, wait: bool = False) -> Iterator[Path]:
    """Hold an advisory lock on the project for the duration of the block.

    POSIX ``flock``, which the kernel releases on process death — so a
    killed pipeline step does not leave a project locked forever, and there
    is no stale-lock heuristic to get wrong. Windows is out of scope
    (ADR-061).
    """

    import fcntl

    root = Path(project_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / LOCK_NAME
    handle = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        flags = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
        try:
            fcntl.flock(handle, flags)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise ProjectBusy(
                    f"{root} is held by another Cadex CLI run ({path}). "
                    "One engine per project: wait for it, or use a different "
                    "--project."
                ) from exc
            raise
        try:
            os.ftruncate(handle, 0)
            os.write(handle, f"{os.getpid()}\n".encode("utf-8"))
        except OSError:
            pass
        yield path
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(handle)


# -- reading the engine's script state, whole ----------------------------
#
# ``open_project`` hands back the complete ``script`` block; ``inspect
# scope="script"`` does not. Inspect exists to be *bounded* — it pages
# mappings and arrays, truncates strings, and replaces any value over 1 KiB
# with a stub naming the path to fetch it from. That is right for an agent
# reading a page at a time and wrong for a CLI that has to print a whole
# script or report every parameter, and it fails in the worst way: a short
# script comes back verbatim and a long one comes back as
# ``{"type": "string", "characters": 1574, "inspect_path": "/source"}``.
# So every read here follows the paths and the ``next_offset`` chain to the
# end.

#: The engine caps `inspect` at 50 per page and shrinks it further to stay
#: under its 32 KiB result cap; `next_offset` reports what it actually did.
_PAGE_LIMIT = 50


def _inspect_script(client: Any, path: str, offset: int, limit: int) -> dict[str, Any]:
    reply = client.request(
        "inspect",
        {"scope": "script", "path": path, "offset": offset, "limit": limit},
    )
    if reply.get("ok") is not True:
        raise RuntimeError(
            f"inspect scope=script path={path} failed: "
            f"{reply.get('error') or reply.get('failure_code')}"
        )
    return reply


def _paged(client: Any, path: str) -> list[Any]:
    """Every page of ``path``, in order, as the engine returned them."""

    pages: list[Any] = []
    offset = 0
    while True:
        reply = _inspect_script(client, path, offset, _PAGE_LIMIT)
        pages.append(reply.get("value"))
        next_offset = (reply.get("page") or {}).get("next_offset")
        if not isinstance(next_offset, int) or next_offset <= offset:
            return pages
        offset = next_offset


def read_project_assets(client: Any) -> list[dict[str, Any]]:
    """The project store's whole asset listing, however many pages it is.

    ``inspect scope=assets`` pages the list like everything else; the store
    holds at most 64 files, so this is one or two pages, but the chain is
    followed rather than assumed.
    """

    entries: list[dict[str, Any]] = []
    offset = 0
    while True:
        reply = client.request(
            "inspect",
            {"scope": "assets", "path": "/assets", "offset": offset, "limit": _PAGE_LIMIT},
        )
        if reply.get("ok") is not True:
            raise RuntimeError(
                "inspect scope=assets failed: "
                f"{reply.get('error') or reply.get('failure_code')}"
            )
        value = reply.get("value")
        if isinstance(value, list):
            entries.extend(dict(item) for item in value if isinstance(item, dict))
        next_offset = (reply.get("page") or {}).get("next_offset")
        if not isinstance(next_offset, int) or next_offset <= offset:
            return entries
        offset = next_offset


def read_script_source(client: Any) -> str:
    """The whole project script, however long it is."""

    return "".join(page for page in _paged(client, "/source") if isinstance(page, str))


def read_script_state(client: Any) -> dict[str, Any]:
    """The script block, reassembled to the shape ``open_project`` returns.

    Same shape either way, so :func:`cadex_cli.report.params_from_script`
    reads an opened project and a re-read one with no special case.
    """

    specs: list[Any] = []
    for page in _paged(client, "/params/specs"):
        if isinstance(page, list):
            specs.extend(page)
    values: dict[str, Any] = {}
    for page in _paged(client, "/params/values"):
        if isinstance(page, dict):
            values.update(page)
    revisions: dict[str, Any] = {}
    for page in _paged(client, "/revisions"):
        if isinstance(page, dict):
            revisions.update(page)
    return {
        "source": read_script_source(client),
        "params": {"specs": specs, "values": values},
        "revisions": revisions,
    }


def read_working_revision(client: Any) -> str:
    """The revision the next write must be guarded with."""

    revision = ""
    for page in _paged(client, "/revisions"):
        if isinstance(page, dict) and page.get("working_revision") is not None:
            revision = str(page["working_revision"] or "")
    return revision
