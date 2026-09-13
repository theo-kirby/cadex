---
node_id: 0ba87d24-d2aa-56ef-953a-7812f0057b96
slug: wild-cove-4437
title: Run record contract and read-only project review reader (ADR-285)
created_at: '2026-09-12T15:19:16+00:00'
parents:
- lucky-comet-0031
summary: ''
---
## What

Delivered the run recording contract and its reader (ADR-285): `cadex walk`
now lands `runs/<name>/run.json` (schema `cadex-run-record-v1`) beside
`review.json`, and `cli/cadex_cli/review_record.py` reads a project back —
accepted identity now, every run then — with every artifact reference
resolved under a containment check. New module, walk wiring in
`cli/cadex_cli/__main__.py`, `cli/tests/test_review_record.py` (22 tests), two
extended walk tests, a `docs/CLI.md` section on the contract, retention and
copying, and ADR-285.

## Why

The critic named this unit: the smallest project/run recording contract and a
tested reader for D2 and D5, preserving accepted revision identity, historical
model/spec inputs and project-local artifact references, testing missing
artifacts and path isolation, documenting retention and copying. It is the
first rung of the charter's short-term ladder. PLAN.md's clearance and section
bets were not followed; the charter (ADR-284) supersedes them.

Advances D2 (`shy-meadow-0959`) and D5 (`sharp-union-6036`) under the ot5
umbrella (`crisp-sun-1239`). Neither is ticked: both need a browser.

## Method

Read the project store layout, the walk's review writer and the trainer's
progress schema, then measured what a real completed run (`ot4-carriage`,
outside this checkout) actually retains: `review.json` carries the accepted
revision only inside its `legs` block, no parameter specs, no snapshot of the
documents the run was designed under, and nothing at all for a walk killed
mid-way. Designed the record from what the walk already holds — no new source
of truth — and made the reader read-only by construction.

The record is written three times per walk: `running` at start (so a killed
walk leaves a file saying it never finished), then `ok`, `failed` (with the
leg and its error) or `pending`. It carries the rollout leg's accepted
revision and digest; the parameter values and the specs read with
`inspect scope=script` while the engine still held that revision; the task
bundle and sha256; the trainer's receipt figures and the requested flags; the
policy name, digest and stored asset; the trace, review references, legs,
and an empty `videos` list as the D4 slot. `runs/<name>/project-docs/` holds
`ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md` and `docs/*.md` with
sha256s, bounded at 32 files of 256 KB. Every path is relative to the run or
the project root; a file outside both is `null`, never absolute.

The reader labels each run `current`/`historical`/`unknown` against the
accepted revision now, gives its outcome in words, and lists `problems`:
missing references, snapshot pages whose digest moved, and references that
escape their base by `..`, an absolute path or a symlink — reported, never
opened. Pre-ADR runs are read from `review.json` and labelled `unrecorded`.

Test changes to the walk fake: its `inspect scope=script` pages, and its
`train --put` now stores the policy under `assets/` as the real leg does —
the reader caught that the fake never had, by reporting the asset missing.

Verification:

```
pixi run python -m pytest cli/tests/test_review_record.py cli/tests/test_walk.py -q
pixi run python -m pytest cli/tests -q
git diff --check
```

Reader exercised read-only against the real legacy project
`~/cadex-projects/ot4-carriage`: accepted revision available, 6 decisions,
three runs listed as `unrecorded`, relations historical/historical/current
against the accepted revision, no problems.

## Result

Committed as 28dd31b8 on ouroboros/ot5. `cadex walk` writes
`runs/<name>/run.json` and `runs/<name>/project-docs/`; the reader in
`cli/cadex_cli/review_record.py` reads a project back without an engine.
`pixi run python -m pytest cli/tests -q`: 323 passed in 229.92 s (baseline
301; the 22 new tests are the difference). `git diff --check` clean. No
engine-zone files changed, so the engine suite was not rerun; the packaged
gate does not apply (no protocol or payload change). The reader read the
real `ot4-carriage` project correctly: three legacy runs labelled
`unrecorded`, relations historical/historical/current, no problems.

Assumptions the next iteration must know:

- The reader reads `script.json` directly for the accepted identity now
  (schema-checked, read-only). `docs/ARCHITECTURE.md` says the store layout is
  not part of the cadexd contract; this is the one read the review client
  makes of it, documented in `docs/CLI.md`. If that becomes untenable, the
  alternative is the engine's `inspect` surface, which needs an engine.
- Specs at the accepted revision come from `inspect scope=script` during the
  walk's review session; the walk records `unavailable: …` rather than
  failing if that read raises.
- No CLI subcommand for the reader yet; it is a module import. `cadex train`
  alone (outside a walk) writes no record — the charter's lifecycle runs
  through the walk.
- Legacy runs in the ot4 projects are readable but carry no specs or
  snapshot; nothing is inferred for them.

Evidence gaps that remain for D2 and D5: no browser exists yet, so no
displayed identity has been compared with a recorded one; no fresh biped
project exists yet, so no record has been written by a real walk (the
record's real-walk evidence is the fake-leg suite and the read of the ot4
projects). The next rung is the one-project server and headless browser test
(D1, D2) on top of this reader.

Dispatch closed: 1 unit — run record contract (`runs/<name>/run.json` + document snapshot) written by the walk, and a read-only, containment-checked project review reader with tests and docs (ADR-285).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 28dd31b8bf73606272a3ef0034e86bf7965cc334

## State Impact

- target: shy-meadow-0959 — The recording half of D2 exists: runs/<name>/run.json carries the rollout's accepted revision and digest, the parameter values and the specs read at that revision, and a bounded snapshot of the project documents; the reader labels each run current/historical/unknown against the accepted revision now, read-only, never rebuilding. Still open: no browser shows any of it, and no fresh biped run has written a record.
- target: sharp-union-6036 — The retention half of D5 exists: each run keeps its model/script revision, specs, task and training configuration, policy identity and review references in its own record, with videos as an empty slot; the reader resolves every reference under a containment check and names missing or escaping ones. Still open: no design change and retraining have been recorded on a fresh project, and no browser assertion exists.
- target: chilly-union-8972 — cadex walk writes a run record three times (running/ok|failed|pending) beside review.json (ADR-285); cadex_cli.review_record is the read-only project review reader. Pre-record runs read as unrecorded. No new subcommand; cadex train alone writes no record.
