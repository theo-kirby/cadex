---
node_id: 4f06843e-c395-5f6b-a7d2-fda9ba3a6846
slug: chilly-glacier-9294
title: The project scaffold documents the walk's documentation review
created_at: '2026-09-08T17:16:33+00:00'
parents:
- eager-lake-5745
summary: ''
---
## What

The generated `ARCHITECTURE.md` scaffold now describes the walk's
documentation review, not only the authoring half of the convention. Its
"Domain docs" section says which declared section asks for which note (an
`<actuator>` section with children asks for `docs/actuators.md`, a `<sensor>`
section for `docs/sensors.md`), that the finding lands in `review.json`'s
`documentation` block and the `PROGRESS.md` row as `docs notes N, none missing`
or `docs notes N, no <subjects>`, and that a missing note neither fails the
walk nor gets written by the CLI. ADR-256 carries an amendment; its ROADMAP
bullet says the scaffold says so too.

## Why

This closes the critic's rejection of `eager-lake-5745`, verbatim: "Update the
generated ARCHITECTURE.md scaffold in cli/cadex_cli/project_docs.py to describe
the walk's documentation review: actuator/sensor declarations imply expected
notes, missing notes are reported without failing or inventing content. Extend
the scaffold test to cover this behavior and run the CLI gate."

The rejection was right about the shape of the gap. ADR-256 made the walk read
the convention back and documented it in `docs/CLI.md` §2 — the Cadex repo's
guide — but the document a *project's* next agent opens on every visit still
described only how to write a note. The charter's **Project as codebase**
criterion is about what the project directory carries for its own agent, so a
review step documented only in the tool's repo is documented in the wrong
place: the finding would arrive in `review.json` and the `PROGRESS` row with
nothing in the project explaining what asked for it or why the CLI left the
note unwritten.

Charter criterion advanced: **The walk exists and is tested headlessly**
(`crisp-reef-5607`), review-step clause, and the convention clause of **Project
as codebase**. Still missing before the walk criterion ticks: nothing here —
the criterion's own gap is the end-to-end run, and this unit is the rejection's
must-fix, not a new leg.

## Method

`cli/` and `docs/` only, one commit. Four sentences appended to
`_ARCHITECTURE_TEMPLATE`'s "Domain docs" section, using the existing `{docs}`
and `{progress}` fills so the text names the real filenames. The wording is
taken from `docs/CLI.md` §2 and ADR-256 rather than reworded, so the three
descriptions of one behaviour do not drift.

`test_the_scaffold_and_the_overlay_ask_for_the_notes_the_walk_exercises` in
`cli/tests/test_project_docs.py` — the existing scaffold test the rejection
named — gained four assertions on the rendered scaffold: the
declaration-to-note mapping, where the finding lands, the two row forms, and
the never-fails/never-writes clause.

## Result

Full CLI gate green: `pixi run python -m pytest cli/tests` — **227 passed, 0
skipped** in 3:30, real engine and real CPU trainer, on the shared
`cpu_training` fixture with no outer backend override. Same count as before the
change; no test changed status. Commit `55ed03dd`.

No behaviour change: template text, a test, an ADR amendment and a ROADMAP
line. No engine, protocol, payload or `shell/` diff.

The unreconciled tail is now three nodes (`strong-falcon-1463`,
`eager-lake-5745`, this one), past the charter's three-node trigger — the
maintainer pass is next, and the overseer already asked for it.

Dispatch closed: 1 unit — the project scaffold documents the walk's
documentation review, closing the critic's rejection of `eager-lake-5745`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 55ed03ddaeeb3b27171560978719d6faf1eaae46

## State Impact

- target: crisp-reef-5607 — the review step's domain-note finding is documented where a project's own agent reads it: the generated ARCHITECTURE.md scaffold names the declaration-to-note mapping, the review.json/PROGRESS landing places, and the reported-never-written-never-fatal rule. Closes the critic rejection of eager-lake-5745. CLI gate 227 passed / 0 skipped.
