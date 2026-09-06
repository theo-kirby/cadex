# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project as a codebase: the three documents every project keeps.

A Cadex project directory is treated the way a good agent treats a
codebase (ADR-193, the lifecycle audit's row 10 in ``docs/MUJOCO.md`` §7c).
It carries the documents an engineer would keep beside the model, and they
are read on every visit and updated as the work goes:

- ``ARCHITECTURE.md`` — what the project is, what its script declares, and
  where the domain docs are.
- ``DECISIONS.md`` — the project's own ADR log: what was chosen, over what,
  and why. Newest last.
- ``PROGRESS.md`` — one row per run the CLI accepted, with the numbers.
  Newest last.

Longer notes go under ``docs/``, one file per subject, named by the subject
(``docs/gear-ratios.md``, ``docs/sensors.md``, ``docs/rejected.md``).

**The CLI scaffolds and appends; the agent reads and decides.** The CLI's
agent runs with no built-in tools — its whole world is the engine (see
:mod:`cadex_cli.agent`) — so it cannot open a file. The three documents are
pasted into its system prompt instead, bounded, and what it decides comes
back through one convention rather than a new tool: a line of its closing
text that starts ``DECISION:`` lands in ``DECISIONS.md``. ``PROGRESS.md``
is written by the CLI after every accepted run, so it holds what actually
happened rather than what a model said would. A shell-attached agent has
file tools of its own and edits the same three files directly; the shape is
the same in both modes because the files are.

The engine knows nothing about any of this: these are plain files beside
``script.json``, like ``agent.json``, and the store's restore pass ignores
them the way it ignores every file it did not write.
"""

from __future__ import annotations

import datetime as _datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .export import ExportedOutput

ARCHITECTURE_NAME = "ARCHITECTURE.md"
DECISIONS_NAME = "DECISIONS.md"
PROGRESS_NAME = "PROGRESS.md"
PROJECT_DOC_NAMES = (ARCHITECTURE_NAME, DECISIONS_NAME, PROGRESS_NAME)

#: Where a project's longer notes live, one file per subject.
DOMAIN_DOCS_DIRNAME = "docs"

#: A closing line of a turn that starts with this is a decision.
DECISION_PREFIX = "DECISION:"

#: How much of each document the agent is shown. The head for the two it
#: reasons from, the tail for the log, because the latest rows are the ones
#: that matter and the header is repeated in the prompt's own text.
PROMPT_DOC_LIMIT = 8_000

PROGRESS_HEADER = "| When (UTC) | Run | Revision | Digest | What | Numbers |"
PROGRESS_RULE = "|---|---|---|---|---|---|"

_ARCHITECTURE_TEMPLATE = """\
# {name} — Architecture

Read on every visit; keep it true. Maintained by the agent and the
`cadex` CLI (ADR-193 in the Cadex repository).

## What this project is

(One paragraph: the part or mechanism, and what it is for.)

## The script

`script.py` is the whole model — one parametric xscript program. The
parameters it declares and why each exists:

| Parameter | Unit | Why it exists |
|---|---|---|

## Outputs

| Output | Kind | Who consumes it |
|---|---|---|

## Domain docs

Longer notes go under `{docs}/`, one file per subject, named by the
subject — `{docs}/gear-ratios.md`, `{docs}/sensors.md`,
`{docs}/actuators.md`, `{docs}/rejected.md` — and are linked from here.
"""

_DECISIONS_TEMPLATE = """\
# {name} — Decisions

One entry per decision that shaped the model or its training: what was
chosen, what it was chosen over, and why. Newest last. A `cadex -p` turn
that ends with a line starting `{prefix}` lands here as the next entry.

## ADR-001 — Project scaffolded ({date})

Created by the `cadex` CLI on first visit, with `{architecture}` and
`{progress}` beside it.
"""

_PROGRESS_TEMPLATE = """\
# {name} — Progress

One row per run the `cadex` CLI accepted, newest last. Written by the
CLI from what actually happened; read by the agent on every visit. A
comparison between two runs is two rows with their numbers.

{header}
{rule}
"""


def project_doc_paths(root: Path | str) -> dict[str, Path]:
    base = Path(root)
    return {name: base / name for name in PROJECT_DOC_NAMES}


def _today() -> str:
    return _datetime.datetime.now(_datetime.timezone.utc).date().isoformat()


def _now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def scaffold_project_docs(root: Path | str) -> list[str]:
    """Create whichever of the three documents are missing; name what was.

    Idempotent, and never overwrites: a document a person or an agent has
    already written is the one the project keeps. Returns the names
    created, in the order they are listed, so a first visit can say so.
    """

    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    name = base.resolve().name or "project"
    fill = {
        "name": name,
        "docs": DOMAIN_DOCS_DIRNAME,
        "prefix": DECISION_PREFIX,
        "date": _today(),
        "architecture": ARCHITECTURE_NAME,
        "progress": PROGRESS_NAME,
        "header": PROGRESS_HEADER,
        "rule": PROGRESS_RULE,
    }
    templates = {
        ARCHITECTURE_NAME: _ARCHITECTURE_TEMPLATE,
        DECISIONS_NAME: _DECISIONS_TEMPLATE,
        PROGRESS_NAME: _PROGRESS_TEMPLATE,
    }
    created: list[str] = []
    for doc_name, template in templates.items():
        path = base / doc_name
        if path.exists():
            continue
        path.write_text(template.format(**fill), encoding="utf-8")
        created.append(doc_name)
    return created


def _bounded(text: str, limit: int, *, keep: str) -> str:
    if len(text) <= limit:
        return text
    if keep == "tail":
        return f"[… {len(text) - limit} earlier characters omitted …]\n" + text[-limit:]
    return text[:limit] + f"\n[… {len(text) - limit} more characters omitted …]"


def read_project_docs(root: Path | str, *, limit: int = PROMPT_DOC_LIMIT) -> str:
    """The three documents as one prompt section, each bounded.

    Empty when none exist — a project that predates the scaffold and was
    never visited by a run that creates it says nothing rather than
    inventing headings.
    """

    parts: list[str] = []
    for doc_name, path in project_doc_paths(root).items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        keep = "tail" if doc_name == PROGRESS_NAME else "head"
        parts.append(f"--- {doc_name} ---\n{_bounded(text.strip(), limit, keep=keep)}")
    return "\n\n".join(parts)


def _cell(text: Any, limit: int = 160) -> str:
    """One table cell: single line, pipes escaped, bounded."""

    flat = re.sub(r"\s+", " ", str(text or "")).strip().replace("|", "\\|")
    if len(flat) > limit:
        flat = flat[: limit - 1].rstrip() + "…"
    return flat


def trace_total_reward(outputs: Iterable[ExportedOutput]) -> float | None:
    """``policy.total_reward`` from an exported rollout trace, if one was.

    The trace is the one artifact a run's number lives in (``docs/MUJOCO.md``
    §7c, row 7); a run that exported none has no number, and says so with
    ``None`` rather than a zero.
    """

    for output in outputs:
        for path in output.files.values():
            if not path.endswith(".json") or "trace" not in Path(path).name:
                continue
            try:
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            policy = payload.get("policy") if isinstance(payload, Mapping) else None
            if isinstance(policy, Mapping) and policy.get("total_reward") is not None:
                try:
                    return float(policy["total_reward"])
                except (TypeError, ValueError):
                    return None
    return None


def progress_numbers(
    *, training: Mapping[str, Any] | None, outputs: Iterable[ExportedOutput]
) -> str:
    """The numbers column: what this run measured, nothing inferred."""

    items: list[str] = []
    reward = trace_total_reward(outputs)
    if reward is not None:
        items.append(f"total_reward {reward:.1f}")
    if training:
        per_step = training.get("reward_per_step")
        if per_step is not None:
            try:
                items.append(f"reward/step {float(per_step):.4g}")
            except (TypeError, ValueError):
                pass
        wall = training.get("wall_time_s")
        if wall is not None:
            try:
                items.append(f"{float(wall):.1f} s")
            except (TypeError, ValueError):
                pass
        sha = str(training.get("sha256") or "")
        if sha:
            items.append(f"sha256 {sha[:8]}")
    return ", ".join(items)


def append_progress_row(
    root: Path | str,
    *,
    run: str,
    what: str,
    revision: str = "",
    digest: str = "",
    numbers: str = "",
) -> str:
    """Append one row to ``PROGRESS.md`` and return it.

    Scaffolds first if the file is missing, so a row is never lost to a
    project that predates the convention.
    """

    base = Path(root)
    path = base / PROGRESS_NAME
    if not path.exists():
        scaffold_project_docs(base)
    row = "| {when} | {run} | {rev} | {digest} | {what} | {numbers} |".format(
        when=_now(),
        run=_cell(run, 40),
        rev=_cell(revision[:8] if revision else "—", 12),
        digest=_cell(digest[:8] if digest else "—", 12),
        what=_cell(what),
        numbers=_cell(numbers),
    )
    text = path.read_text(encoding="utf-8")
    if PROGRESS_HEADER not in text:
        text = text.rstrip("\n") + f"\n\n{PROGRESS_HEADER}\n{PROGRESS_RULE}\n"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + row + "\n", encoding="utf-8")
    return row


def decision_lines(text: str) -> list[str]:
    """The ``DECISION:`` lines of a turn's closing text, stripped of the prefix."""

    found: list[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip().lstrip("-*• ").strip()
        if stripped.upper().startswith(DECISION_PREFIX):
            body = stripped[len(DECISION_PREFIX):].strip()
            if body:
                found.append(body)
    return found


def _next_adr_number(text: str) -> int:
    numbers = [int(match) for match in re.findall(r"^## ADR-(\d+)", text, re.MULTILINE)]
    return (max(numbers) + 1) if numbers else 1


def record_decisions(root: Path | str, text: str) -> list[str]:
    """Land a turn's ``DECISION:`` lines in ``DECISIONS.md`` as ADR entries.

    Each becomes ``## ADR-NNN — <first sentence> (<date>)`` with the whole
    line as the body, numbered after the last entry present. Returns the
    entries written, so a report can say so. Nothing to land, nothing
    touched.
    """

    lines = decision_lines(text)
    if not lines:
        return []
    base = Path(root)
    path = base / DECISIONS_NAME
    if not path.exists():
        scaffold_project_docs(base)
    existing = path.read_text(encoding="utf-8")
    number = _next_adr_number(existing)
    date = _today()
    entries: list[str] = []
    chunks: list[str] = []
    for line in lines:
        title = _cell(line.split(". ", 1)[0].rstrip("."), 96)
        chunks.append(f"\n## ADR-{number:03d} — {title} ({date})\n\n{line.strip()}\n")
        entries.append(f"ADR-{number:03d}")
        number += 1
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + "".join(chunks), encoding="utf-8")
    return entries
