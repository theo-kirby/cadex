# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project as a codebase: the three documents every project keeps.

A Cadex project directory is treated the way a good agent treats a
codebase (ADR-193, the lifecycle audit's row 10 in ``docs/MUJOCO.md`` §7c).
It carries the documents an engineer would keep beside the model, and they
are read on every visit and updated as the work goes:

- ``ARCHITECTURE.md`` — what the project is, what its script declares,
  how it trains (locally from the venv or ``--remote`` on the box, the
  same project-relative artifacts either way, a warm start carried out to
  the box since ADR-268), and where the domain docs are.
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
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
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

#: How much of each document the agent is shown: architecture head,
#: decisions and progress tails, retaining the newest appended history.
PROMPT_DOC_LIMIT = 8_000

PROGRESS_HEADER = "| When (UTC) | Run | Revision | Digest | What | Numbers |"
PROGRESS_RULE = "|---|---|---|---|---|---|"

_ARCHITECTURE_TEMPLATE = """\
# {name} — Architecture

Read on every visit; keep it true. Maintained by the agent and the
`cadex` CLI (ADR-193 in the Cadex repository).
Prompt context keeps the first 8,000 characters of architecture and the last
8,000 of decisions and progress, plus an omission marker when shortened.
Domain notes keep their last 2,000 characters; full documents stay on disk.
Progress rows, decisions and domain-note updates replace their files only after
writing succeeds, so a failed update preserves the previous document. This is
per-file protection, not a transaction across documents or a power-loss guarantee.

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
On a leg timeout, the process group gets a full five-second SIGTERM cleanup
grace even if its direct child exits early, then an unconditional SIGKILL.
For toy CPU runs, use `JAX_PLATFORMS=cpu`; `training/SETUP.md` §b gives
the invocation and resource bounds, including for a CUDA-capable venv.
`agent.json.updated_at` records changed session identity or model, not every
attempt. A refused turn still saves changed identity for resumption; unchanged
identity leaves that file untouched. Opening may refresh accepted restore
attempt metadata in `script.json`, even when the subsequent turn fails.
A refused walk does not roll that bookkeeping back or create a failure commit.
After failed retraining, the accepted sweep stays applied with `policy_on=0`;
prior artifacts and history survive. Retry with a fresh `--out` and `--name`,
the last successful policy/parent task and an explicit task-change reason.
`docs/CLI.md` §2 gives the tested recovery command and comparison contract.
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
and the latest `{docs}/inventory.md` report. The review saves inventory counts
and its latest-report link; recover historical rows from the walk's Git commit
(see the CLI guide's walk review contract).
The review also writes `{docs}/clearance.md` and the
review's `clearance` block. Named front/top/right/iso previews and their
summary live in `review/render/<accepted-revision>/`; the `render` block
carries project-relative paths, revision/digest, approximation, limits and
acquisition/render timings. The walk refuses rendering failures or a revision
that differs from the rollout; old files are never a successful fallback.
`walk_seconds` measures the entry point through review (before final commit).
The `section` block carries the shared snapshot cut at world XZ, at an
offset derived from that snapshot's own bounds, under
`review/section/<accepted-revision>/XZ-<derived-offset>/` (SVG and JSON). It
retains status, availability, revision/digest, plane, units, approximation,
limits, acquisition/section timings, `offset_source` and the ordered
`offset_candidates_mm`. The plane crosses as many objects' bounds as one
plane can, so no mechanism needs its own constant. Empty cuts are available with no
contours; unsupported cuts are unavailable with per-object reasons. Section
errors and rollout digest mismatches fail the walk; retained old artifacts
never imply current success. Clearance covers only the initial solved pose,
at 0.1 mm minimum distance and 1e-6 mm³ maximum common volume. Its own
`{progress}` row carries offending, unknown and checked pair counts;
unavailable measurements stay unavailable. Training and rollout rows
retain their numbers, so rows
from either mode compare line for line. **A warm start travels (ADR-268):** the dispatcher carries the
bundle and the model out, and `--init-from`'s policy and its parent
bundle beside them, so an iterate has the same shape in either mode. With the GUI attached the same commands
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

The walk reads this convention back rather than only offering it
(ADR-256). After the rollout it parses the MJCF it trained on and takes
each declared section as a note subject: an `<actuator>` section with
children asks this project for `{docs}/actuators.md`, a `<sensor>`
section for `{docs}/sensors.md`. The `documentation` block in
`review.json` and the `{progress}` row report the notes kept here, the
subjects the model declares, and the ones with no note — `docs notes N,
none missing` or `docs notes N, no <subjects>`. A missing note is a
finding for the next design turn, never a walk failure, and the CLI never
writes the note itself: what drives a joint and what a sensor measures
are this project's to say, and an invented note would be pasted back as
if it were knowledge. A run that exported no model declares nothing and
reports nothing.
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
check them before generating checkpoints and traces. To keep a walk local,
append `/runs/<name>/`, `/review/`, and `/assets/<name>.cxpolicy` to the root
`.gitignore` AFTER `!assets/*.cxpolicy`; `.git/info/exclude` cannot override
that negation. Ignores affect untracked files only; existing tracked or
explicitly staged files still enter automatic commits. In a project-root
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
project-root repository, the CLI attempts a commit after each accepted run.
Only `committed <sha>.` in the command's notes confirms success; a row alone
does not prove a commit. Rows still land without Git or in a nested project
without its own `.git`; those rows have no automatic commit.

For lifecycle comparisons, record iterations, environment count and seeds.
Training `--seed` is a bounded unsigned 32-bit integer (default 0); it does
not change the rollout seed declared in the xscript. Train and walk rows record
`training_seed`, `rollout_seed` (unavailable for training alone), an objective
identity and the prior same-kind row's evidence. Missing historical evidence is
marked `unavailable (legacy row)`; no seed or objective is inferred retroactively.
A trace seed of `None` means an explicitly unseeded rollout, not missing evidence.

`training.comparison` and the walk's `review.json` comparison block retain the
objective metadata and full action rows. Objective `v1` is SHA-256 over compact,
key-sorted JSON of the exported task's `schema`, `observations` (including units),
`reward`, `termination`, `episode` and `functions`. List order and expression text
are significant. Model identity, actions, seeds, reset variation, randomisation,
disturbances and runtime versions are excluded; this identifies the declared
objective, not experimental equivalence or mathematical equivalence of formulas.
The separate `actions` hash in progress rows covers full action metadata; inspect
`comparison.actions` for physical bounds and units. The quill's 40 mm and 60 mm
action bounds have different scaling despite matching rewards and objectives.
Deltas remain descriptive, never evidence of improved learning or equal control
difficulty. Prior evidence refers to the previous train/walk row of that kind;
metric deltas still refer to the last row carrying each metric, which may differ.
Standalone rollout rows retain their existing numeric format.

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
        keep = "head" if doc_name == ARCHITECTURE_NAME else "tail"
        parts.append(f"--- {doc_name} ---\n{_bounded(text.strip(), limit, keep=keep)}")
    for relative, path in domain_note_paths(root).items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        bounded = _bounded(text.strip(), NOTE_DOC_LIMIT, keep="tail")
        parts.append(f"--- {relative} ---\n{bounded}")
    return "\n\n".join(parts)


#: The numbers cell is the one that carries several findings at once --
#: a walk row states its clearance, its motion in two channels and its
#: documentation check together -- so it gets more room than a cell that
#: holds one phrase. It was 160 and truncated the walk's documentation
#: half the day motion was added beside it (ADR-259).
PROGRESS_NUMBERS_LIMIT = 1024


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
#: they are spelled in the column: the label, then the value. The two
#: travel labels are why the motion cell is spelled with a label rather
#: than a unit (ADR-260): `motion 103.3 mm` is unparseable here, and a
#: walk row that carries no delta cannot say the travel held while the
#: reward fell — which is the one thing an iterate run is for.
#: ``clearance offending`` joins them for the same reason and reads back
#: off every row ever written, because the cell already spelled the label
#: before the count (ADR-271): a geometry iterate that answers a clearance
#: finding turns exactly this number, and a bare ``0`` cannot say that the
#: pair it replaced was there. ``unknown`` is deliberately not compared —
#: it is a coverage figure that only means anything beside ``pairs
#: checked``, and a delta on it alone would read as a verdict on the
#: mechanism rather than on what the check could reach.
COMPARED_NUMBERS = (
    "total_reward", "reward/step", "travel_mm", "travel_deg",
    "clearance offending",
)

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


def spelled_number(label: str, value: float) -> str:
    """How a compared number is written in the column.

    One decimal for a reward total, four significant figures for the
    rest — a travel of 0.0004 mm is not the same claim as a travel of 0.0,
    and a rounding that erased the difference would be the row lying.
    """

    return f"{value:.1f}" if label == "total_reward" else f"{value:.4g}"


def compared_number(
    label: str,
    value: float,
    previous: Mapping[str, tuple[float, str]],
) -> str:
    """One compared number, with its change against the last row that
    carried it (ADR-194). Without a previous row, the number alone."""

    spelled = spelled_number(label, value)
    before = previous.get(label)
    if before is None:
        return f"{label} {spelled}"
    was, digest = before
    delta = value - was
    was_spelled = spelled_number(label, was)
    delta_spelled = spelled_number(label, abs(delta))
    # The sign of what is shown, not of the float: a change that rounds
    # to nothing is "±0.0", never "-0.0".
    if float(delta_spelled) == 0.0:
        sign = "±"
    else:
        sign = "+" if delta > 0 else "-"
    return f"{label} {spelled} (Δ {sign}{delta_spelled} vs {digest} at {was_spelled})"


def task_comparison(path: Path | str) -> dict[str, Any]:
    """Objective v1 excludes model, actions and stochastic conditions (ADR-263)."""
    try:
        task = json.loads(Path(path).read_text(encoding="utf-8"))
        fields = ("schema", "observations", "reward", "termination", "episode", "functions")
        objective = {key: task[key] for key in fields}
        encoded = json.dumps(objective, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
        return {"objective_id": "v1:" + hashlib.sha256(encoded).hexdigest(),
                "objective": objective, "actions": task["actions"],
                "actions_id": hashlib.sha256(json.dumps(
                    task["actions"], sort_keys=True, separators=(",", ":"),
                    allow_nan=False).encode("utf-8")).hexdigest()}
    except (OSError, ValueError, KeyError, TypeError):
        return {"objective_id": None, "reason": "exported task metadata unavailable"}


def comparison_cell(root: Path | str, run: str, evidence: Mapping[str, Any]) -> str:
    """State current evidence and the last same-kind row's evidence, even legacy."""
    objective = evidence.get("objective_id") or "unavailable"
    def seed(key):
        return str(evidence[key]) if key in evidence else "unavailable"
    current = (f"objective {objective}; training_seed {seed('training_seed')}; "
               f"rollout_seed {seed('rollout_seed')}")
    prior = "none"
    try:
        for line in (Path(root) / PROGRESS_NAME).read_text(encoding="utf-8").splitlines():
            match = _ROW_RE.match(line.strip())
            if match and match.group(2) == run:
                found = re.search(r"objective (v1:[0-9a-f]{64}|unavailable); "
                                  r"training_seed ([^;]+); rollout_seed ([^;]+)",
                                  match.group(6))
                prior = found.group(0) if found else "unavailable (legacy row)"
    except OSError:
        pass
    return (f"; {current}; actions {evidence.get('actions_id') or 'unavailable'}; "
            f"previous evidence: {prior}; deltas are descriptive; "
            "matching objectives do not establish equivalent control difficulty")


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
        items.append(compared_number("total_reward", reward, previous))
    if training:
        per_step = training.get("reward_per_step")
        if per_step is not None:
            try:
                value = float(per_step)
                items.append(compared_number("reward/step", value, previous))
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


def _replace_document(path: Path, text: str) -> None:
    """Keep the previous document intact until its replacement is complete."""

    path = path.resolve()  # Preserve an existing document symlink.
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    scratch = Path(name)
    try:
        os.close(handle)
        scratch.write_text(text, encoding="utf-8")
        if path.exists():
            shutil.copymode(path, scratch)
        os.replace(scratch, path)
    finally:
        scratch.unlink(missing_ok=True)


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
        numbers=_cell(numbers, PROGRESS_NUMBERS_LIMIT),
    )
    text = path.read_text(encoding="utf-8")
    if PROGRESS_HEADER not in text:
        text = text.rstrip("\n") + f"\n\n{PROGRESS_HEADER}\n{PROGRESS_RULE}\n"
    if not text.endswith("\n"):
        text += "\n"
    _replace_document(path, text + row + "\n")
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
        _replace_document(path, f"{existing}\n- ({date}) {body}\n")
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


#: The note subjects a mechanism's own declaration asks for, by the MJCF
#: section that declares them (ADR-256). The CLI never writes these notes --
#: what drives a joint and what a sensor measures are the design turn's to
#: say -- but a walk can read what the model it trained on declares and
#: report which of those subjects the project keeps no note for.
DECLARED_NOTE_SUBJECTS = {"actuator": "actuators", "sensor": "sensors"}


def documentation_status(
    root: Path | str, expected: Iterable[str] = ()
) -> dict[str, Any]:
    """The project's domain notes, and the subjects its model asks for.

    ``expected`` is what the mechanism declares, as note subjects
    (:data:`DECLARED_NOTE_SUBJECTS`). ``missing`` is the subjects with no
    ``docs/<subject>.md`` -- a finding for the next design turn, which
    reads the notes back in its prompt, and never a failure: the CLI does
    not write a note whose content it would have to invent.
    """

    notes = domain_note_paths(root)
    stems = {Path(relative).stem for relative in notes}
    wanted = list(dict.fromkeys(str(subject) for subject in expected if subject))
    return {
        "notes": list(notes),
        "expected": wanted,
        "missing": [subject for subject in wanted if subject not in stems],
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
    _replace_document(path, existing + "".join(chunks))
    return entries


# -- the repository the project owns (ADR-194) ----------------------------

GITIGNORE_NAME = ".gitignore"

_GITIGNORE_TEMPLATE = """\
# Written by the cadex CLI on the project's first visit (ADR-194). Edit freely.
# What a rebuild recreates:
script_artifacts/
# What is bulk — frames and renders are outputs of the model, not the model:
frames/
/review/
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
