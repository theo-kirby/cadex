---
node_id: 5e9c6e39-5867-5ea1-b14c-4912f55761db
slug: lucid-pebble-4000
title: A design turn can reach the domain-doc convention
created_at: '2026-09-08T07:01:53+00:00'
parents:
- weathered-hill-5955
summary: ''
---
## What

Made the project's domain-doc convention reachable by a design turn (ADR-245).
A closing line `NOTE <subject>: <text>` now appends a dated bullet to the
project's `docs/<subject>.md`, the same closing-text channel that already lands
`DECISION:` lines as ADRs. The notes are pasted back into the next turn's
prompt beside `ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md`, bounded at
2,000 characters tail-first. `inventory.md` and `clearance.md` are refused as
subjects: they are the CLI's own generated reports and a note must never append
to a measurement. The design instruction now asks for `docs/actuators.md` and
`docs/sensors.md` from any mechanism with actuators or sensors. Commit
`febaf940`.

## Why

Advances charter criterion **The walk exists and is tested headlessly**
(`crisp-reef-5607`) by closing one of the legs the ladder's short rung names
verbatim: "the domain-doc convention the walk exercises (`docs/gear-ratios.md`,
`docs/sensors.md`)". It is also the overseer's listed unit 4 and the planner's
conditional unit 2 in [rec: weathered-hill-5955], whose precondition is
satisfied by the measurement already recorded in [rec: proud-beacon-8002]: the
two-servo leg's design turn produced no sensor or actuator note.

**Three assumptions, written down because nobody was here to ask.**

1. The overseer's unit 1 — record the leg's review findings in *that project's*
   `DECISIONS.md`/`PROGRESS.md` — is not doable. The rehearsal project was a
   fresh directory under the system temporary directory (basename
   `cadex-nt3-i183-leg`) and has been reaped; `find` over `/var/folders` and
   `/tmp` returns nothing. Its numbers survive in `proud-beacon-8002` and in
   this repository's graph, which is where a reader will find them. Re-running
   the walk to recreate a project only to write notes into it would spend a
   design turn to restore an artifact that is ephemeral by construction, so I
   did not.
2. The overseer's units 2 and 3 — the remote-training handoff script and doc,
   and the GUI-attached mode doc — are already shipped and evidenced on
   `witty-spark-2613`: ADR-200 with `--remote` on `train` and `walk` around
   `training/remote_train.sh` (offline-tested, never dispatched), ADR-201 for
   the GUI-attached mode, and the offline whole-walk artifact parity audit.
   Reopening them would be duplicate work, so I took the next unit in the
   overseer's own ordering that has open work.
3. The convention channel, not a tool. The planner asked for wording over a new
   tool or op; a `NOTE` line adds no protocol op, no engine change and no shell
   change, and reuses the mechanism `DECISION:` established. Wording alone
   could not close this leg — the instruction had nowhere to send the text.

## Method

Read the plan, the overseer message, `witty-spark-2613`, `proud-beacon-8002`,
`cli/cadex_cli/agent.py`'s design instruction and `cli/cadex_cli/project_docs.py`.
Located the defect in the instruction's last clause ("ask the caller to write
those, naming the file") and in the absence of any writer for `docs/<subject>.md`
other than the CLI's own generated reports.

Changes, all in the LGPL CLI zone and the docs:

- `cli/cadex_cli/project_docs.py`: `NOTE_PREFIX`, `GENERATED_DOC_STEMS`,
  `NOTE_DOC_LIMIT`, `note_lines`, `record_notes`, `domain_note_paths`, a
  note-file template, and `read_project_docs` extended to paste the
  agent-authored notes. The subject is slugged (`[^a-z0-9]+` collapsed to `-`,
  capped at 48 characters), so it cannot escape `docs/`.
- `cli/cadex_cli/__main__.py`: one call beside `record_decisions` in the turn
  command, so the walk's design leg gets it through the same `cadex -p` child.
- `cli/cadex_cli/agent.py`: the instruction's closing clause replaced by the
  convention, naming the four exemplar files and the two refused subjects.
- `docs/CLI.md` project-doc table and prose; `docs/DECISIONS.md` ADR-245;
  `docs/ROADMAP.md` item ticked under the ADR-193 row.
- `cli/tests/test_project_docs.py`: two tests — parsing, per-subject append,
  refused generated subjects, read-back into the prompt; and the scaffold, the
  overlay and `docs/CLI.md` held together as one ticket.

One mistake, fixed forward inside the unit: a `sed` renumber of my
placeholder ADR reference also rewrote a pre-existing, correct `ADR-233`
citation at `cli/cadex_cli/__main__.py:851`; restored before the commit and
confirmed absent from the diff.

## Result

**`pixi run python -m pytest cli/tests` — 197 passed, no skips**, in 218 s. The
engine half ran (the built payload is present), so this is not a bare-checkout
green. The two new tests fail against the previous source: `note_lines` and
`record_notes` did not exist, and neither did the overlay and `docs/CLI.md`
wording they pin.

What the change does **not** establish: no design turn was run under the new
instruction, so **that a model actually emits `NOTE` lines is the next walk's
evidence, not this commit's**. The mechanism is verified; the behaviour it is
meant to elicit is not. A model that emits no note leaves the old behaviour
exactly — the change is additive on the prompt surface and inert without one.
No engine, shell or protocol surface was touched, so no engine suite, packaged
gate or shell gate was in scope for this zone; none was run and none is
claimed. No removal, so no two-commit protocol.

Charter criterion **The walk exists and is tested headlessly**
(`crisp-reef-5607`) still cannot be ticked from this unit alone: what remains
is a walk run whose design turn leaves `docs/actuators.md` and
`docs/sensors.md` behind in the project, which is one run, not one edit.

Unreconciled tail: two nodes including this one. Reconciliation is the
maintainer's.

Next: run the documented `cadex walk` on a servo-driven mechanism and check
whether the design turn now leaves the two notes behind — that run is both the
evidence for this unit and the ladder's standing short-rung unit. Do not
restart the second-mechanism walk; `sage-peak-2689` is finished and evidenced.
The leg project's review findings (shin/foot-bolt intersections at
5.8373525743 mm³ each, bolt/nyloc-nut at 9.2781252741 mm³ each, the 5 mm
servo-to-driven-link gap) live in `proud-beacon-8002` and have no project
directory left to be written into; a future iterate unit should walk a
**durable** project directory so its documents outlive the run.

Dispatch closed: 1 unit — a design turn can now write the project's domain
notes through the closing-text channel; the walk exercising it is the next
run's evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: febaf94043ffa3bb78e7185ef7323b57a23641a2

## State Impact

- target: crisp-reef-5607 — The walk's documented domain-doc convention becomes reachable by a design turn: a closing NOTE <subject>: line lands docs/<subject>.md and the notes are read back next visit; the instruction asks for actuator and sensor notes. Mechanism verified by 197 CLI tests, no skips; a walk that actually produces the notes is still outstanding.
- target: witty-spark-2613 — The three modes stay one shape: the note channel is the same closing-text convention in every mode, written by the CLI beside the three project documents, with no shell or engine surface touched.
