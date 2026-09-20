---
node_id: de5217d4-ae2b-52cb-a388-d6998164290e
slug: long-spark-1984
title: 'F4–F7: verify complete paginated measurement evidence'
created_at: '2026-09-14T22:27:53+00:00'
parents:
- blue-sky-2193
summary: ''
---
## What

Added two known-answer cases exercising the ot7 collector's real child_measure,
paginated inspect reader and product fit_summary together. Documented their
scope in the runner README. No new collection layer or product behavior.

## Why

Advances evidence confidence for F4–F7, particularly F4 (polished-forest-0215).
The critic requested the existing repair collector after the documented provider
reset, otherwise a concrete missing evidence test. At arrival the clock read
2026-09-14 18:17 America/New_York, before the documented 20:20 reset. I took
the prescribed test fallback without spending another provider call. Existing
runner tests fake the measurement executor; they did not exercise child_measure
with the real pagination and fit summary. Unrelated obsolete plan directions
remain outside this unit.

## Method

A synthetic inspect client returns a clear pair on the first pair page, then
248.2 mm³ overlap and 0.2 mm missed intended contact on the next. A world-plane
finding makes three expected failures. The fixture requires exact pair names,
distances and volumes, accepted revision, all three pairs, unchanged incomplete
sweep coverage with extrema, 30-degree first contact and 1.25-second timing,
and catalog inventory. Only inspect requests and restore=False are allowed.
A second case fails the later page: it must raise before any partial fit or
clearance file is written. The collector and product reader are unmodified.

A separate process-local mutation truncated the collected pairs to the first
page. The new success case failed as expected (1 failed / 18 deselected);
no repository source was changed for this mutation. This shows the added test
detects lost late findings rather than merely exercising the happy path.

## Result

Validation: full CLI suite exited 0, **705 passed / 1 skipped in 529.50 s**.
Focused runner suite: **19 passed in 0.36 s**. The deliberate mutation
failed exactly the new later-page case, as expected. Logs remain project-local:

- `cadex-projects/ot7-runner-validation/evidence/iteration27/cli-tests.log`
  SHA-256 `256c2a0b2636615195ca02c1ab5b5ab158c9f694484d1a1cf3cb62f54bfa6ee4`.
- `cadex-projects/ot7-runner-validation/evidence/iteration27/mutation.log`
  SHA-256 `b57fbb2d616d42c91a7288650fa5fe1421316610ee4c1c76c9079f373b62c1d4`.

`git diff --check` passed. Engine suite and packaged gate were not rerun:
only CLI tests and the collector README changed.

These fixtures are synthetic evidence-collection checks, not Heron measurements
or a successful repair. F4–F7 remain open. All frozen prompts, provider refusal
history, project scripts, parameters and accepted states are untouched. No
provider call, new dependency, engine/payload/protocol change, full build,
charter edit, dashboard change or state-graph edit. Assumption: the previously
documented provider reset remains the earliest appropriate retry time. Next
use the existing F4 repair collector after that reset; do not treat this test
as consuming the frozen repair turn.
Dispatch closed: 1 unit — pin paginated F4–F7 measurement evidence collection.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 7bf90b929ef901fdee5057274ca08d612939b981

## State Impact

- target: polished-forest-0215 — Real collector pagination and fit-summary integration now has known-answer and late-page-error fixtures; mutation detects lost failures. Provider reset remains ahead, no repair call ran, F4 remains open.
