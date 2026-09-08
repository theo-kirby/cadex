# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project as a codebase: the three documents every project keeps.

A Cadex project directory is treated the way a good agent treats a
codebase (ADR-193, the lifecycle audit's row 10 in ``docs/MUJOCO.md`` §7c).
It carries the documents an engineer would keep beside the model, and they
are read on every visit and updated as the work goes:

- ``ARCHITECTURE.md`` — what the project is, what its script declares,
  how it trains (locally from the venv or ``--remote`` on the box, the
  same project-relative artifacts either way, cold runs only when remote —
  ADR-200), and where the domain docs are.
- ``DECISIONS.md`` — the project's own ADR log: what was chosen, over what,
  and why. Newest last.
- ``PROGRESS.md`` — one row per run the CLI accepted, with the numbers.
  Newest last. A number a previous row also carried is written **with its
  change against that row** — the comparison is one recorded row, not two
  a reader lines up by eye (ADR-194, row 9).

Longer notes go under ``docs/``, one file per subject, named by the subject
(``docs/gear-ratios.md``, ``docs/sensors.md``, ``docs/rejected.md``). They
land the same way a decision does — a closing line ``NOTE <subject>: …``
(ADR-245) — and are pasted back on the next visit, so the convention the
walk documents is one a design turn can actually reach.

**The CLI scaffolds and appends; the agent reads and decides.** The CLI's
agent runs with no built-in tools — its whole world is the engine (see
:mod:`cadex_cli.agent`) — so it cannot open a file. The three documents are
pasted into its system prompt instead, bounded, and what it decides comes
back through one convention rather than a new tool: a line of its closing
text that starts ``DECISION:`` lands in ``DECISIONS.md``. ``PROGRESS.md``
is written by the CLI after every accepted run, so it holds what actually
happened rather than what a model said would. The shell's own agent has
neither a file tool nor a shell (the Mesh tools are its whole world), so
with the GUI attached the three files are still the CLI's and a person's;
the shape is the same in every mode because the files are (ADR-201).

**Project-root git repositories** (ADR-194). Outside another work tree,
the CLI initializes a repository if needed and creates its default
``.gitignore`` only during initialization, only if absent. Existing root
repositories keep their ignore configuration. After every accepted run,
the CLI attempts to commit all working changes (``git add -A``), including
unrelated edits, with the ``PROGRESS.md`` row's words as the message.
A project nested beneath another repository root, without its own ``.git``,
gets documents and rows but no initialization or commit; the parent index
is untouched. Without ``git`` on ``PATH`` there is no automatic history.
The envelope reports a successful commit as ``committed <sha>.``.

The engine knows nothing about any of this: these are plain files beside
``script.json``, like ``agent.json``, and the store's restore pass ignores
them the way it ignores every file it did not write.
"""

from __future__ import annotations

import datetime as _datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
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

#: A closing line of a turn that starts with this is a domain note:
#: ``NOTE <subject>: <text>`` lands in ``docs/<subject>.md``. The same
#: convention as ``DECISION:``, for the notes too long for an ADR line.
NOTE_PREFIX = "NOTE"

#: Subjects under ``docs/`` the CLI writes itself. A note never appends to
#: a generated report, so ``inventory.md`` and ``clearance.md`` stay what
#: the last run measured.
GENERATED_DOC_STEMS = ("inventory", "clearance")

#: How much of each domain note the agent is shown back. Smaller than a
#: project document's share: there is one of each of those and there can
#: be many notes.
NOTE_DOC_LIMIT = 2_000

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

Purchased hardware: publish each catalog body and place purchased instances
as separate assembly components with `assembly.component`, separate from
printed solids. Transformed catalog bodies may also be clearance cutters;
a cutter does not imply another purchased part. Review the script alongside
placed inventory; its totals cannot identify hardware fused into other solids.

## Outputs

| Output | Kind | Who consumes it |
|---|---|---|

## Training

**Mode:** (`local` — the trainer runs from its venv on this machine, or
`remote` — `cadex train --remote` / `cadex walk --remote` run the same
leg on the box `training/remote_train.sh` names.) Fill in which, and
why; `{progress}` marks each remote row `(remote)`.

The shared mode artifacts table in `docs/CLI.md` is the walk contract.
`agent.json.updated_at` records changed session identity or model, not every
attempt. A refused turn still saves changed identity for resumption; unchanged
identity leaves that file untouched. Opening may refresh accepted restore
attempt metadata in `script.json`, even when the subsequent turn fails.
A refused walk does not roll that bookkeeping back or create a failure commit.
The walk's `{progress}` row and project commit subject name the output
relative to this project, or by basename for an external output, so the
recorded run label contains no absolute machine path.
Before the first leg, `walk.engine_source_comparison` in the JSON envelope
and stderr report matching, different or unavailable top-level Python bytes
against the checkout. Dev runs compare the binary prefix's `Mod/cadex`;
payload runs compare the manifest's module directory. Name lists stop at ten,
with full counts. This does not certify binary or loaded-module provenance,
determine which copy is newer, refuse a run, or rebuild the engine.
The artifacts are the same project-relative paths in both modes: the
bundle and the policy under `runs/<name>/train/`, the verified rollout
under `runs/<name>/rollout/`, the numbers in `runs/<name>/review.json`
and the generated `{docs}/inventory.md` component report (also summarized
in the review's `inventory` block). Catalog totals count placed instances;
they cannot identify hardware fused into other solids or infer purchases.
The review also writes `{docs}/clearance.md` and the
review's `clearance` block. Named front/top/right/iso previews and their
summary live in `review/render/<accepted-revision>/`; the `render` block
carries project-relative paths, revision/digest, approximation, limits and
acquisition/render timings. The walk refuses rendering failures or a revision
that differs from the rollout; old files are never a successful fallback.
`walk_seconds` measures the entry point through review (before final commit).
The `section` block carries the shared snapshot cut at world XZ, Y = 3.125 mm,
under `review/section/<accepted-revision>/XZ-3.125/` (SVG and JSON). It
retains status, availability, revision/digest, plane, units, approximation,
limits and acquisition/section timings. This interior plane cuts both reference
mechanisms without dispatch by mechanism. Empty cuts are available with no
contours; unsupported cuts are unavailable with per-object reasons. Section
errors and rollout digest mismatches fail the walk; retained old artifacts
never imply current success. Clearance covers only the initial solved pose,
at 0.1 mm minimum distance and 1e-6 mm³ maximum common volume. Its own
`{progress}` row carries offending, unknown and checked pair counts;
unavailable measurements stay unavailable. Training and rollout rows
retain their numbers, so rows
from either mode compare line for line. **Remote runs are cold runs only:** the dispatcher carries the
bundle and the model out and nothing else, so a warm start
(`--init-from`) trains locally. With the GUI attached the same commands
run from a terminal beside the open file, one at a time while no rebuild
is in flight; the shell's own agent cannot run them, and it sees an
accepted run on the next Rebuild Model or reopen. Rebuild Model or
reopen **before the next GUI edit** once a command has accepted a
script: stale mutations are refused without replay or revision adoption.
Review the refreshed source and values before retrying. Simultaneous
acceptance and concurrent rebuilds still require sequential use.

## Domain docs

Longer notes go under `{docs}/`, one file per subject, named by the
subject — `{docs}/gear-ratios.md`, `{docs}/sensors.md`,
`{docs}/actuators.md`, `{docs}/rejected.md` — and are linked from here.

A design turn writes one by ending a closing line with
`{note_prefix} <subject>: <text>`, which the CLI appends as a dated bullet
in `{docs}/<subject>.md`, the way a `{prefix}` line lands an ADR. Every
note is pasted back into the next turn's prompt, so a mechanism with
actuators or sensors should leave `{docs}/actuators.md` and
`{docs}/sensors.md` behind. `{docs}/inventory.md` and
`{docs}/clearance.md` are the CLI's generated reports, not note subjects.
"""

_DECISIONS_TEMPLATE = """\
# {name} — Decisions

One entry per decision that shaped the model or its training: what was
chosen, what it was chosen over, and why. Newest last. A `cadex -p` turn
that ends with a line starting `{prefix}` lands here as the next entry.

## ADR-001 — Project scaffolded ({date})

Created by the `cadex` CLI on first visit, with `{architecture}` and
`{progress}` beside it. Outside another work tree, the CLI initializes a
repository if needed and creates default ignore rules only if `.gitignore`
is absent at initialization. Existing repositories keep their ignore rules;
check them before generating checkpoints and traces. In a project-root
repository, accepted runs attempt to commit all working changes, including
unrelated edits. A project nested beneath another repository root, without
its own `.git`, gets no automatic commit and leaves the parent index untouched.
"""

_NOTE_TEMPLATE = """\
# {title}

One bullet per note, newest last. Written by the `cadex` CLI from a turn's
closing `NOTE {title}:` lines, and read back to the agent on its next
visit. Edit it freely; it is the project's, not the CLI's.
"""

_PROGRESS_TEMPLATE = """\
# {name} — Progress

One row per run the `cadex` CLI accepted, newest last. Written by the
CLI from what actually happened; read by the agent on every visit. A
number a previous row also carried shows its change against that row,
as `total_reward 127.8 (Δ -1602.1 vs 2996fb73 at 1729.9)`: the delta,
the digest of the run compared against, and that run's value. In a
project-root repository, the CLI attempts a commit after each accepted run;
`committed <sha>.` in the command's notes confirms success. Rows still land
without Git or when the project is nested beneath another repository root
without its own `.git`; those rows have no automatic commit.

For lifecycle comparisons, record iterations, environment count and seeds.
`total_reward` sums rewards over the verified rollout's `step_count`;
divide by that count for rollout reward per step. The trainer's
`reward/step` is its final training-batch mean, a different measurement.
Compare objectives only when reward expressions, weights, units and
episode lengths match; a larger reward after changing them is not progress.

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
        "note_prefix": NOTE_PREFIX,
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
    """The three documents and the domain notes as one prompt section.

    Each is bounded. Empty when none exist — a project that predates the
    scaffold and was never visited by a run that creates it says nothing
    rather than inventing headings. The notes are pasted with the
    documents because the agent has no file tool: a note it writes on one
    visit is only worth writing if it reads it on the next.
    """

    parts: list[str] = []
    for doc_name, path in project_doc_paths(root).items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        keep = "tail" if doc_name == PROGRESS_NAME else "head"
        parts.append(f"--- {doc_name} ---\n{_bounded(text.strip(), limit, keep=keep)}")
    for relative, path in domain_note_paths(root).items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        bounded = _bounded(text.strip(), NOTE_DOC_LIMIT, keep="tail")
        parts.append(f"--- {relative} ---\n{bounded}")
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


#: The numbers a row carries that a later row is compared against, as
#: they are spelled in the column: the label, then the value.
COMPARED_NUMBERS = ("total_reward", "reward/step")

_NUMBER_RE = {
    label: re.compile(re.escape(label) + r" (-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)")
    for label in COMPARED_NUMBERS
}
_ROW_RE = re.compile(r"^\| (\S+) \| (\S+) \| (\S+) \| (\S+) \| (.*) \| (.*) \|$")


def previous_numbers(root: Path | str) -> dict[str, tuple[float, str]]:
    """For each compared number, the last row that carried it: value and digest.

    Read from ``PROGRESS.md`` as written, so a person's hand-added row
    counts too. A row's own delta text (``at 1729.9``) is not a value; the
    first match on each row is the run's own. Empty when there is nothing
    to compare against.
    """

    path = Path(root) / PROGRESS_NAME
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    found: dict[str, tuple[float, str]] = {}
    for line in lines:
        match = _ROW_RE.match(line.strip())
        if not match or match.group(1).startswith(("When", "---")):
            continue
        digest, numbers = match.group(4), match.group(6)
        for label, pattern in _NUMBER_RE.items():
            hit = pattern.search(numbers)
            if hit:
                try:
                    found[label] = (float(hit.group(1)), digest)
                except ValueError:
                    pass
    return found


def _compared(
    label: str,
    value: float,
    spelled: str,
    previous: Mapping[str, tuple[float, str]],
) -> str:
    before = previous.get(label)
    if before is None:
        return f"{label} {spelled}"
    was, digest = before
    delta = value - was
    was_spelled = f"{was:.4g}" if label == "reward/step" else f"{was:.1f}"
    delta_spelled = f"{abs(delta):.4g}" if label == "reward/step" else f"{abs(delta):.1f}"
    # The sign of what is shown, not of the float: a change that rounds
    # to nothing is "±0.0", never "-0.0".
    if float(delta_spelled) == 0.0:
        sign = "±"
    else:
        sign = "+" if delta > 0 else "-"
    return f"{label} {spelled} (Δ {sign}{delta_spelled} vs {digest} at {was_spelled})"


def progress_numbers(
    *,
    training: Mapping[str, Any] | None,
    outputs: Iterable[ExportedOutput],
    previous: Mapping[str, tuple[float, str]] | None = None,
) -> str:
    """The numbers column: what this run measured, nothing inferred.

    With ``previous`` (from :func:`previous_numbers`), a number an earlier
    row also carried is written with its change against that row — the
    comparison as one recorded row (ADR-194).
    """

    items: list[str] = []
    previous = previous or {}
    reward = trace_total_reward(outputs)
    if reward is not None:
        items.append(_compared("total_reward", reward, f"{reward:.1f}", previous))
    if training:
        per_step = training.get("reward_per_step")
        if per_step is not None:
            try:
                value = float(per_step)
                items.append(_compared("reward/step", value, f"{value:.4g}", previous))
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


def _note_stem(subject: str) -> str:
    """``docs/<stem>.md`` for a note's subject, or ``""`` if it names none."""

    slug = re.sub(r"[^a-z0-9]+", "-", str(subject or "").lower()).strip("-")
    return slug[:48].strip("-")


def note_lines(text: str) -> list[tuple[str, str]]:
    """The ``NOTE <subject>:`` lines of a turn's closing text.

    Each is a ``(stem, body)`` pair, the stem slugged for
    ``docs/<stem>.md``. A line naming no subject, carrying no body, or
    aimed at a report the CLI generates itself is not a note.
    """

    found: list[tuple[str, str]] = []
    for line in str(text or "").splitlines():
        stripped = line.strip().lstrip("-*• ").strip()
        if stripped[: len(NOTE_PREFIX)].upper() != NOTE_PREFIX:
            continue
        rest = stripped[len(NOTE_PREFIX):]
        if rest[:1] not in (" ", "\t") or ":" not in rest:
            continue
        subject, body = rest.split(":", 1)
        stem, body = _note_stem(subject), body.strip()
        if stem and body and stem not in GENERATED_DOC_STEMS:
            found.append((stem, body))
    return found


def record_notes(root: Path | str, text: str) -> list[str]:
    """Land a turn's ``NOTE <subject>:`` lines under ``docs/``.

    One file per subject, each note appended as a dated bullet, the file
    created with a title when the subject is new. Returns the
    project-relative paths written, so a report can say so. Nothing to
    land, nothing touched.
    """

    notes = note_lines(text)
    if not notes:
        return []
    directory = Path(root) / DOMAIN_DOCS_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    date = _today()
    written: list[str] = []
    for stem, body in notes:
        path = directory / f"{stem}.md"
        if path.exists():
            existing = path.read_text(encoding="utf-8")
        else:
            existing = _NOTE_TEMPLATE.format(title=stem.replace("-", " "))
        if not existing.endswith("\n"):
            existing += "\n"
        path.write_text(f"{existing}\n- ({date}) {body}\n", encoding="utf-8")
        relative = f"{DOMAIN_DOCS_DIRNAME}/{path.name}"
        if relative not in written:
            written.append(relative)
    return written


def domain_note_paths(root: Path | str) -> dict[str, Path]:
    """The project's agent-authored domain notes, by project-relative path.

    The generated reports are excluded: they are the last run's
    measurements and the run that made them already reported their
    numbers.
    """

    directory = Path(root) / DOMAIN_DOCS_DIRNAME
    try:
        entries = sorted(directory.glob("*.md"))
    except OSError:
        return {}
    return {
        f"{DOMAIN_DOCS_DIRNAME}/{path.name}": path
        for path in entries
        if path.stem not in GENERATED_DOC_STEMS
    }


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


# -- the repository the project owns (ADR-194) ----------------------------

GITIGNORE_NAME = ".gitignore"

_GITIGNORE_TEMPLATE = """\
# Written by the cadex CLI on the project's first visit (ADR-194). Edit freely.
# What a rebuild recreates:
script_artifacts/
# What is bulk — frames and renders are outputs of the model, not the model:
frames/
*.mp4
*.png
# What a walk re-makes (ADR-199): the store keeps the policy a script names,
# review.json and PROGRESS.md keep the numbers; checkpoints and traces stay out.
*.cxpolicy
!assets/*.cxpolicy
*-trace.json
# What is transient:
.cadex-cli.lock
*.blend1
*.blend@
__pycache__/
"""

_GIT_IDENTITY = ("-c", "user.name=cadex", "-c", "user.email=cadex@localhost")


def _git(root: Path, *argv: str, identity: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(root)]
    if identity:
        command += list(_GIT_IDENTITY)
    command += ["-c", "commit.gpgsign=false", *argv]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _inside_a_work_tree(root: Path) -> bool:
    result = _git(root, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return False
    try:
        return Path(result.stdout.strip()).resolve() != root.resolve()
    except OSError:
        return False


def ensure_project_repo(root: Path | str) -> str:
    """Make the project root its own git repository; say what happened.

    Returns a note for the envelope on the first visit (``"initialised …"``
    or why not), and ``""`` when there is nothing to say: the repository
    already exists. Never initialises inside somebody else's work tree —
    a project checked into a larger repository is that repository's — and
    never fails a run: no ``git`` means no history, not no build.
    """

    base = Path(root)
    if (base / ".git").exists():
        return ""
    if shutil.which("git") is None:
        return "no git on PATH: the project keeps no history."
    if _inside_a_work_tree(base):
        return "inside an existing git work tree: not initialised, not committed."
    result = _git(base, "init", "-q")
    if result.returncode != 0:
        return f"git init failed: {result.stderr.strip() or result.returncode}"
    ignore = base / GITIGNORE_NAME
    if not ignore.exists():
        ignore.write_text(_GITIGNORE_TEMPLATE, encoding="utf-8")
    return "initialised a git repository in the project root."


def _has_identity(root: Path) -> bool:
    return bool(_git(root, "config", "--get", "user.email").stdout.strip())


def commit_project(root: Path | str, message: str) -> str:
    """Commit everything that changed; return the short sha, or ``""``.

    Only for a root that is its own repository (see
    :func:`ensure_project_repo`); an empty string means nothing to commit,
    no repository, or a commit that failed — the run has already
    succeeded and this is its record, so none of those is an error.
    """

    base = Path(root)
    if not (base / ".git").exists() or shutil.which("git") is None:
        return ""
    if _git(base, "add", "-A").returncode != 0:
        return ""
    if not _git(base, "status", "--porcelain").stdout.strip():
        return ""
    result = _git(
        base,
        "commit",
        "-q",
        "--no-verify",
        "-m",
        message or "cadex run",
        identity=not _has_identity(base),
    )
    if result.returncode != 0:
        return ""
    return _git(base, "rev-parse", "--short", "HEAD").stdout.strip()
