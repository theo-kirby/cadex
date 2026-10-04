# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project a CLI run works on: its lock, and the CLI's own state file.

Two things live here that the engine deliberately knows nothing about.

**The lockfile.** ``cadexd`` is one process per project, and a pipeline that
sweeps parameters will run several of these at once. Two engines opening the
same store would each restore it, each rebuild it, and each write
``script.json``. An advisory ``flock`` on ``<project_root>/.cadex-cli.lock``
turns that from silent corruption into a refusal with a readable message.

**``agent.json``.** The CLI's own state file, a *sibling* of
``script.json``: the CLI reads the engine's state file through ``inspect``
and never writes it, so a CLI version bump cannot break a project. Since
Cadex stopped running its own agent (ADR-538) it holds one thing, **the
project's engine budgets** (ADR-517): the wall-clock
seconds and the memory ceiling one engine script run may spend,
``open_project``'s ``budgets``. A project that needs a longer rebuild says
so once, ``cadex budgets --set timeout_seconds=900``, and every later run —
an MCP session, a ``cadex params``, a walk's legs — opens with it. ``--engine-timeout`` and
``--engine-memory`` override them for one call. An unset budget is absent,
never zero, and the engine fills it from its own default per field.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import datetime as _datetime
import errno
import json
import math
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

#: The CLI's state file, beside the engine's ``script.json``.
AGENT_STATE_NAME = "agent.json"
AGENT_STATE_SCHEMA = "cadex-cli-agent-v1"
LOCK_NAME = ".cadex-cli.lock"


#: The project's engine budgets, by ``open_project`` key, with each one's type.
BUDGET_KEYS: dict[str, type] = {"timeout_seconds": float, "memory_limit_mb": int}
#: Bounds a stored or overriding budget must fall within: an hour of
#: wall-clock, 128 GiB of memory — the shell's preference ranges.
BUDGET_LIMITS: dict[str, float] = {"timeout_seconds": 3600.0, "memory_limit_mb": 131072}


class ProjectBusy(RuntimeError):
    """Another Cadex CLI run holds this project."""


@dataclass(frozen=True)
class AgentState:
    """What the CLI remembers about a project between runs."""

    updated_at: str = ""
    #: The project's engine budgets (ADR-517); only the ones it sets.
    budgets: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        payload = {
            "schema": AGENT_STATE_SCHEMA,
            "updated_at": self.updated_at,
        }
        if self.budgets:
            payload["budgets"] = dict(self.budgets)
        return payload


def budget_value(key: str, value: Any) -> float | int:
    """One budget, checked: a positive number within its bound, or 0 to unset.

    Raises :class:`ValueError` with the words a person needs; the CLI turns
    that into a usage error.
    """

    if key not in BUDGET_KEYS:
        raise ValueError(f"not a budget: {key!r} (one of {', '.join(BUDGET_KEYS)})")
    kind = BUDGET_KEYS[key]
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number, not {value!r}") from None
    if not math.isfinite(number) or number < 0 or number > BUDGET_LIMITS[key]:
        raise ValueError(f"{key} must be within [0, {BUDGET_LIMITS[key]:g}]; 0 unsets it")
    if kind is int and number != int(number):
        raise ValueError(f"{key} is a whole number of megabytes, not {value!r}")
    return kind(number)


def _stored_budgets(raw: Any) -> dict[str, Any]:
    """The budgets a file holds; anything out of range is simply not set."""

    budgets: dict[str, Any] = {}
    if not isinstance(raw, dict):
        return budgets
    for key in BUDGET_KEYS:
        if key not in raw or isinstance(raw[key], bool):
            continue
        try:
            value = budget_value(key, raw[key])
        except ValueError:
            continue
        if value > 0:
            budgets[key] = value
    return budgets


def effective_budgets(stored: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """The budgets one call opens with: each positive override over the stored one."""

    budgets = dict(stored)
    for key, value in overrides.items():
        if value:
            budgets[key] = budget_value(key, value)
    return budgets


def agent_state_path(project_root: Path | str) -> Path:
    return Path(project_root) / AGENT_STATE_NAME


def read_agent_state(project_root: Path | str) -> AgentState:
    """Read ``agent.json``; an absent or unreadable file is simply empty.

    Unreadable is not an error on purpose. The worst a corrupt state file may
    do is cost the stored budgets — refusing to model over it would be a far
    bigger failure than the one it is reporting. A file an older CLI wrote,
    with a conversation's ``session_id`` and ``model`` beside the budgets, is
    read for its budgets alone.
    """

    path = agent_state_path(project_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return AgentState()
    if not isinstance(payload, dict) or payload.get("schema") != AGENT_STATE_SCHEMA:
        return AgentState()
    return AgentState(
        updated_at=str(payload.get("updated_at") or ""),
        budgets=_stored_budgets(payload.get("budgets")),
    )


def _write_agent_file(project_root: Path | str, state: AgentState) -> None:
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


def _now() -> str:
    return (_datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def write_agent_budgets(project_root: Path | str, changes: Mapping[str, Any]) -> AgentState:
    """Store the project's engine budgets: each change sets one, 0 unsets it."""

    stored = read_agent_state(project_root)
    budgets = dict(stored.budgets)
    for key, value in changes.items():
        value = budget_value(key, value)
        if value > 0:
            budgets[key] = value
        else:
            budgets.pop(key, None)
    state = AgentState(updated_at=_now(), budgets=budgets)
    _write_agent_file(project_root, state)
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
