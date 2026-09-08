---
node_id: f02e0b2e-5529-5db4-9d02-f85e0e9cb081
slug: eager-lake-5745
title: The walk checks its domain-note convention against the model
created_at: '2026-09-08T17:10:30+00:00'
parents:
- strong-falcon-1463
summary: ''
---
## What

The walk's review now reads the domain-note convention back instead of only
offering it. After the rollout, `cadex walk` parses the MJCF it actually
trained on (`DIR/train/<name>-model.xml`) and takes each declared section as a
note subject through `DECLARED_NOTE_SUBJECTS`: an `<actuator>` section with
children asks the project for `docs/actuators.md`, a `<sensor>` section for
`docs/sensors.md`. `documentation_status` puts that beside the notes the
project keeps, `review.json` gains a `documentation` block (`notes`,
`expected`, `missing`, and the `model` read, relative to `DIR`), and the walk's
`PROGRESS.md` row carries the same finding after its clearance half — `docs
notes N, none missing` or `docs notes N, no actuators`. ADR-256,
`docs/CLI.md` §2, one ROADMAP bullet.

## Why

The overseer's order after the redirect was: maintainer pass (not a work
iteration's to run), the GUI-attached mode doc, then "the domain-doc convention
(`docs/gear-ratios.md`, `docs/sensors.md`) actually written and read by the
walk, not just described". The GUI limb is already documented and audited
current on `witty-spark-2613` (ADR-201, corrected by ADR-204, re-read by
`early-quill-3654`), so this iteration took the third item.

The gap it closes is on **Project as codebase**'s convention clause and the
review step of **The walk exists and is tested headlessly**: ADR-245 gave the
design turn a way to write a note without a file tool and pasted the notes back
next visit, and the authoring contract asks for `NOTE actuators:` and
`NOTE sensors:` by name — but nothing read the convention back. A walk on a
driven, observed mechanism whose turn wrote neither note produced a review
indistinguishable from one on a fully documented project, and the gap was
visible only to a person who opened `docs/` and knew what to expect there.

Assumption written down rather than asked: the check **reports and never
writes**. A CLI-authored `docs/actuators.md` would be invented content pasted
back into the next design turn's prompt as if it were knowledge, so a missing
note is a finding for the next turn, the way an offending clearance pair is a
finding rather than a walk failure (ADR-238). Read from the MJCF rather than
from the script for the same reason the trace carries the run's number: the
script is what was asked for, the exported model is what ran, so a declaration
behind a switch that evaluated false asks for no note.

## Method

`cli/` and `docs/` only. `documentation_status` in `project_docs.py` beside the
existing `domain_note_paths` (so the generated `inventory`/`clearance` reports
stay out, exactly as they already do in the prompt); `declared_note_subjects`
in `walk.py`, an `ElementTree` read of the train directory's `*-model.xml`;
`command_walk` wires the two and `write_review` relativizes the model path the
way it already relativizes the trace; `_documentation_cell` appends the half to
the walk's progress row.

Tests: `test_walk.py` pins the reader on an MJCF fixture (both sections, an
empty `<sensor/>`, a file that is not XML), the offline fake walk pins the
"no bundle, no finding" path, and the real-engine toy walk asserts the whole
finding end to end. `test_project_docs.py` pins `documentation_status` and the
`docs/CLI.md` sentence that documents which declaration asks for which note.

## Result

Full CLI gate green: `pixi run python -m pytest cli/tests` — **227 passed, 0
skipped** in 3:30, real engine and real CPU trainer, on the shared `cpu_training`
fixture with no outer backend override. Two failures on the first run were both
mine and both fixed before the commit: my new note ordered itself ahead of the
clearance bounds-check note in the offline envelope (now emitted after it, and
only when the model declared something), and the toy's staged model file is
`model-model.xml`, not `job-model.xml` (the assertion now derives the name).

On the real toy walk: the mechanism declares both subjects, the project carries
only `docs/sensors.md`, and `review.json`, the `PROGRESS.md` row and the run
notes all name `actuators` as the one with no note.

Criterion advanced: **Project as codebase** — its convention clause now has a
walk that exercises the convention rather than a document that describes it;
and the review step of **The walk exists and is tested headlessly** gains one
more eye. Still missing before *Project as codebase* can be called finished
here: no walk has yet produced a domain note from a real design turn's closing
text on this machine (every note in evidence was placed by hand or by a unit
test), so the write half of the convention is exercised only offline. That is
the next unit for this criterion, and it needs a model turn.

The unreconciled tail is now 2 nodes; a maintainer pass is due at 3.

Dispatch closed: 1 unit — the walk's review checks the domain-note convention against what the trained model declares (ADR-256), CLI gate 227 passed 0 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 8c71dc8d1fb2dc79c2e69be94710a7687353fe79

## State Impact

- target: crisp-reef-5607 — the walk's review gains a documentation eye: it reads the MJCF it trained on and names the note subjects the mechanism declares against the notes the project keeps (ADR-256), reported in review.json and the PROGRESS.md row, never written and never fatal; CLI gate 227 passed, 0 skipped
- target: calm-peak-5247 — the project-as-codebase domain-note convention (ADR-245) is now read back by the walk rather than only offered to the design turn; the write half is still exercised only by hand-placed notes and unit tests, so a real design turn authoring a note on this machine remains open
