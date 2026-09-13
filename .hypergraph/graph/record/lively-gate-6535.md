---
node_id: fa27bd5b-8836-58e9-8784-6195e16c408c
slug: lively-gate-6535
title: Run identity recorded before training and kept through failure; a pre-rollout run borrows the accepted model only at its own identity (ADR-289)
created_at: '2026-09-12T17:39:17+00:00'
parents:
- lucid-journey-6875
summary: ''
---
## What

A run is now the run of a revision from its first record (ADR-289, commit
`7a63fa63`). `cadex walk` starts `run.json` from the project manifest —
accepted revision, digest and parameter specs, with `identity_source` and
`specs_source` both `project manifest (script.json) at walk start` — so the
`running` record names the training input before the trainer writes its
first telemetry sample beside it. Every leg that reports an identity
(design, sweep, train, collect, declare, rollout) replaces it with `<leg>
leg envelope`; a design turn or sweep re-reads the manifest's specs and
re-lands `running` before the train leg; a failed or pending record keeps
the last identity learned; every write snapshots the project documents.
`not reached` now means only that there was no manifest and no leg spoke.
On the reading side, `run_model` draws a run that has not rolled out from
the accepted attempt's tessellation when — and only when — its recorded
revision and digest are both the accepted ones now, labelled as borrowed;
a historical run, a blank identity or a moved digest still show nothing,
with the reason.

## Why

The critic's message asked first for the reconcile pass, then for this
fix. The dispatch forbids the reconcile skill, `hypergraph update` and any
state edit in a work iteration without exception, so the reconcile was not
run; the unreconciled tail is now three records (`shady-bay-0771`,
`lucid-journey-6875`, this one) and the reconcile pass is due. The product
fix was taken exactly as named: the defect `lucid-journey-6875` recorded on
the real biped — `runs/probe1/run.json` saying `not reached` with null
revision and digest while the GPU trained and after the walk failed, the
page showing `RELATION UNKNOWN` and no model for the one run a reviewer
most wanted to identify. It advances D3 (`dawn-delta-4361`: the run being
trained is identified and drawn), D5 (`sharp-union-6036`: a failed run is
tied to its design), D8 (`cool-gate-3332`: failed-run identity persists,
browser-covered through failure) and D2 (`shy-meadow-0959`: the borrowed
model rule). The first-walk `policy_on` failure is left as the next product
fix, as the critic asked.

## Method

- `cli/cadex_cli/review_record.py`: `manifest_identity(root, moment)`
  returns the record kwargs a walk can claim from the manifest alone;
  `write_run_record` gains an explicit `identity_source` (the derived
  default is unchanged for callers that pass none).
- `cli/cadex_cli/__main__.py`: `known` starts from the manifest; a
  `learned(leg)` closure appends each successful leg and takes its
  reported identity; `land_record` snapshots docs on every write and no
  longer reads identity from `report`; `running` is re-landed before the
  train leg when design/sweep legs ran.
- `cli/cadex_cli/review_server.py`: `_model_before_rollout` — the
  path-None trace case is checked before the error case (an unrecorded
  reference resolves with error `not recorded`, which is what hid the
  first attempt).
- Tests: the fake `cadex` copies `run.json` to `run.json.at-train` when
  its train leg starts, so the test reads the record exactly as the trainer
  would have seen it; refusals at train and at declare keep the manifest's
  (`t…`) and the train leg's (`r…`) identity respectively, told apart by
  construction; a design turn moves the identity before training. An HTTP
  test borrows the accepted model for exactly one of four identities
  (current, historical, moved digest, blank). A headless-Chromium test
  selects a training run, reads revision, digest, identity source, specs
  and the borrowed model, watches telemetry arrive, then watches the
  trainer and the walk fail and asserts every identity is still on screen.
- Verification: `pixi run python -m pytest cli/tests` — 358 passed, 1
  skipped (the private-address test, `CADEX_REVIEW_HOST` unset); the
  engine suite's doc-keyed tests, 36 passed; `git diff --check` clean.
- Docs: `docs/CLI.md` run-record contract, ADR-289 in `docs/DECISIONS.md`,
  a roadmap entry, and the defect paragraph in
  `docs/HEADLESS-BIPED-REVIEW.md` rewritten as fixed.

## Result

True now: a walk's `running` record names the model being trained before
telemetry exists; a failed or pending run keeps its identity and its
document snapshot; the dashboard shows CURRENT, the revision, digest,
specs and a borrowed, labelled model for a run that is training or failed
before rollout at the accepted identity, and nothing but the reason for a
historical one. All evidence for this unit is fixture evidence: no real
walk ran, and `probe1`'s record was deliberately left as written —
records are not rewritten after the fact — so on the real project that
run still reads `not reached` until the next walk lands. The next real
walk (which needs the `policy_on` fix first, since the fresh script
declares no switch and the declare leg refuses without one) is what turns
this into real-artifact evidence for D3, D5 and D8. Assumption recorded:
borrowing the accepted model requires revision *and* digest to match; a
matching revision alone is not taken as the same geometry. Concern: the
dispatch-level ban on reconcile and the charter's three-record rule now
disagree on what the next unit is; this record says the tail is three and
leaves the call to the critic. No new dependency.

Dispatch closed: 1 unit — run identity recorded from the manifest before training and kept through failure, with the borrowed-model rule and browser coverage through failure (ADR-289, commit 7a63fa63).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 7a63fa63092988d25123580c6f977c73324b6f3d

## State Impact

- target: dawn-delta-4361 — The run being trained is now identified: run.json names the manifest's revision, digest and specs before the first telemetry sample, so the page shows CURRENT and a borrowed, labelled model instead of RELATION UNKNOWN while training (fixture-browser-tested; the real fresh-biped re-observation under the fix is still open).
- target: sharp-union-6036 — A failed or pending run keeps the last identity it learned (manifest at start, then each leg's envelope), a design turn re-lands the running record with the moved identity before training, and a historical run with no rollout shows no model with the reason; probe1's pre-fix record is left as written.
- target: cool-gate-3332 — Failed-run review is browser-covered through failure: a training run's revision, digest, specs and borrowed model stay on screen when telemetry and then the walk report failure (ADR-289); the real interrupted biped run and successful new attempt remain untested.
- target: shy-meadow-0959 — Borrowed-model rule: a run that retained no rollout is drawn from the accepted attempt only when its recorded revision AND digest equal the accepted ones now, labelled as borrowed; otherwise nothing is shown, with the reason.
