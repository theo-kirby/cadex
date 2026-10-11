---
node_id: 9c0c1c09-1d74-5722-ad5d-74bfcb8d7940
slug: winter-pond-1701
title: 'Wave-1 findings fixed: mount holes, T-nut slot, coupled regions, lids, definition cap'
created_at: '2026-10-11T10:13:55+00:00'
parents:
- violet-gate-4339
- civic-walrus-3405
summary: ''
---
## What

Five Cadex fixes from the first breadth wave's findings are merged and verified on main:

- machine parts publish mount holes (ADR-660);
- B-type slot and slide-in T-nuts (ADR-661);
- the regions check follows belts, screws and couplings (ADR-665);
- lids and walls close a frame with `closes=[...]` (ADR-666);
- the output-definition cap is 4 MiB (ADR-670).

## Why

The owner asked for findings 1-4 and 6 from the wave-1 review to be fixed. Finding 5 (slow linkage rebuilds) and finding 7 (catalog gaps) are deferred.

## Method

Two worktree agents were used, under a 25 GB memory cap for anything that starts FreeCADCmd. The definition cap was done directly, measured from wave1-printer's accepted attempt: 634 kB for 354 components and 295 joints, about 1.3 kB per joint. The branches were merged, with the ADR log kept in order, followed by build-engine and both full suites.

## Result

- Engine suite: 2859 passed, 61 skipped.
- CLI suite: 1261 passed, 1 skipped.

The wave-1 designs that use machine parts will drift geometrically on rebuild. That is expected, because the parts' geometry was corrected.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 22a8c1fe86fc9dd2f2d04d42e395feaa155fe77e

## State Impact

- target: brave-stone-9609 — one output definition may be 4 MiB (ADR-670); with ADR-660/661 machine parts mount and T-nuts fit their slots
