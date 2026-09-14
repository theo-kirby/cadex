---
node_id: 7bc703b6-eb49-5cf1-8ba9-434893e45adf
slug: tidy-journey-9462
title: 'F1/F9: build replies read every fit page or report unavailable'
created_at: '2026-09-14T21:40:47+00:00'
parents:
- still-raven-7629
summary: ''
artifacts:
- cli/tests/test_clearance.py
- docs/CLI.md
- docs/probes/ot7/fit-paging.json
---
## What

Added a known-answer regression for paged fit measurements in the product agent's successful build reply, including an unreadable later page. Documented the existing all-pages-or-unavailable behavior in docs/CLI.md. No production code or design changed.

## Why

This advances F1 (wild-horizon-5461) and F9 (eager-summit-3153) by covering the build-reply paging boundary, previously tested only in the written clearance report. The critic asked to resume F4 after the provider's reported reset, otherwise address an uncovered checker/tool behavior. At orientation the clock was 2026-09-14 21:28:43 UTC (17:28:43 America/New_York); the retained refusal says reset at 20:20 local, still 2h51m away. I deferred the invocation instead of making another premature retry, and selected the requested regression fallback. There was no new refusal, no provider call, and no actor edit to the retained seed. F4 remains open with its prior evidence unchanged.

## Method

The real Bridge.call(write_script) reads the real CadexInspection bounded pager through a fixture client. Sixty known pair measurements put 57 clear pairs first, then an unmeasured pair with its kernel reason, a 248.2 mm³ intersection and a missed contact at 0.2 mm; one world-geometry finding accompanies them. The assertions require all four named failures and their numbers, matching bridge history and last-fit state, with successful acceptance and its revision preserved. In the second case the client refuses the later /pairs page: fit must be unavailable with the actual read error, never a verdict on the readable prefix, while the build still succeeds. This fixture represents published measurements, not a new geometric experiment or an unassisted design.

Negative control: a separate external Python runner replaces inventory._ask in memory to discard the /pairs continuation offset. Both new cases fail as expected. No source mutation is left behind. Logs and the runner are project-local under cadex-projects/ot7-fit-paging/evidence; the compact committed receipt gives their digests. Initial fixture setup failures (missing model_state and a path without its leading slash) were corrected before verification; neither was a product defect.

## Result

Both new cases pass; the negative control produces 2 expected failures. Full CLI suite: 686 passed, 1 skipped in 529.26 seconds. Receipt: docs/probes/ot7/fit-paging.json. git diff --check passes. There is no newly discovered product bug, new dependency, behavior change, removal or direction change, so no ADR or build is needed. No engine/protocol/payload/shell change: engine suite and packaged gate were not rerun; their preceding green evidence remains the baseline. No dashboard files or service were changed.

F1's regression evidence now covers complete paged build replies and later-page failure handling; F9's CLI suite remains green. F4 still needs the unchanged frozen repair invocation after the reported provider reset. No claim is made about repair outcome or any design's fit. Three records will now be pending; reconciliation belongs to a separately authorized pass because this dispatch expressly forbids it.

Dispatch closed: 1 unit — paged measured-fit build-reply regression while F4 awaits the provider reset.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: cc4d9cc59b38e2d1e5e9af2635168a211795cf9a

## State Impact

- target: wild-horizon-5461 — Known-answer bridge regression covers late-page intersection, missed contact, unknown and world findings, plus unavailable fit on later read failure without refusing acceptance.
- target: eager-summit-3153 — CLI suite 686 passed, 1 skipped; paged fit negative control fails both new cases as expected. No product or payload change.
