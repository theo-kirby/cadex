---
node_id: 80a120fa-3db2-5701-9b2d-69ea1ad02451
slug: fierce-bloom-1076
title: 'ot7 merge review: retain accepted artifacts through restore'
created_at: '2026-09-20T18:42:15+00:00'
parents:
- frosty-sea-6051
summary: ''
artifacts:
- src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
---
## What

The ot7 merge review found and fixed loss of accepted artifacts during repeated
restore. ADR-398 defers pruning until cadexd has settled the accepted pin.

## Why

The owner requested review, merge and the next run. A project could reopen
successfully through its remembered geometry digest while its accepted
attempt directory had been collected. That breaks retained evidence readers
and display availability, so it blocked merging ot7 unchanged.

## Method

Inspected the restore/lifecycle/store boundary and changed the real offset
lifecycle regression to require retained bytes rather than their deletion.
Ran that test before changing product code: 1 failed, 22 deselected, with
`restore pruned the pinned accepted artifacts`. The runtime now accepts an
internal `prune_artifacts=False` option for restore; cadexd collects after
comparison and pin rollback. Ordinary writes keep their existing behavior.
The changed-script lifecycle also repeats five refused opens and checks
retention of the original pin and result. No wire contract changed.

## Result

The initial targeted source tests passed (2 passed, 21 deselected). After
`pixi run build-engine` and `pixi run stage-engine`, the packaged lifecycle
suite passed all 23 tests in 22.47 s, including the strengthened five-refusal
test. Full-suite verification is recorded separately in the merge review.
The fix preserves accepted artifacts byte-for-byte, retains bounded recent
attempts, and keeps changed geometry refused. Historical projects whose
artifacts were already lost are not silently repaired or reaccepted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 73126d8cac5c14143946b1180153c6db4170f34c

## State Impact

- target: forest-wind-0342 — ADR-398 defers restore artifact collection until the accepted pin is settled; five repeated successful and refused opens retain accepted evidence, with 23 packaged lifecycle tests passing.
