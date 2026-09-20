---
node_id: e6746f41-929d-540d-adf2-00cdb6f08e98
slug: true-wolf-3979
title: 'F4: preserve later nested swept measurement pages'
created_at: '2026-09-14T22:39:58+00:00'
parents:
- long-spark-1984
summary: ''
---
## What

Added one known-answer nested swept-pagination test to the ot7 measurement
collector suite and documented it in the runner README.

## Why

Advances F4 evidence collection (polished-forest-0215), also used by F5–F7.
The critic requested the existing seeded repair after the provider reset,
or this specific nested-pagination test before it. At arrival the clock read
2026-09-14 22:29 UTC (18:29 America/New_York), before the documented 20:20
reset. I took that prescribed fallback; no provider call or design edit ran.
The preceding unit checked static pair pagination but its sweep was inline.

## Method

The real child_measure and recursive inspect reader collect a synthetic sweep
whose joints occupy two pages. The later joint has its own two-page pair
array. Its later pair alone carries the worst overlap, 12 mm³, with a zero
minimum distance and first contact at 30 degrees. The test requires the exact
whole sweep, both joints and pairs, 0.5/1.25-second timings and every expected
page request. It permits only inspect requests with restore=False.

A separate process-local mutation stops pagination specifically at the nested
pair path. The new test fails because the collision row disappears (1 failed,
19 deselected). No repository implementation was changed by the mutation.

## Result

Focused runner suite: 20 passed in 0.37 s. The deliberate pagination mutation
failed as expected. Full CLI suite result and log hashes follow below.

Full CLI suite exited 0: **706 passed / 1 skipped in 528.73 s**.
Logs remain outside the checkout:

- `cadex-projects/ot7-runner-validation/evidence/iteration28/cli-tests.log`,
  SHA-256 `f2035131c518d23a5268cf80c1fa6e15d01f5d70203217a8b27f5e1e021084f1`.
- `cadex-projects/ot7-runner-validation/evidence/iteration28/mutation.log`,
  SHA-256 `95fff3978d492e97ed0e66d519517c67dc29fb1c236cc5a6fcfd395084e4beaa`.

`git diff --check` passed. No engine or payload change, so no engine suite,
packaged gate or build was required for this test-only unit. No new dependency,
product behavior change, design edit, prompt change, provider call, dashboard
change, charter edit or state-graph edit. This fixture is not design evidence:
F4–F7 remain open. Assumption: the previously documented reset is the earliest
appropriate retry time. After it, run the existing F4 repair collector against
the preserved seed and retain before/after measurements and transcript digests.
Dispatch closed: 1 unit — verify later nested swept pages retain collision evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d2a85da16d962f50d2f96bfb5e5685e4e10f7b94

## State Impact

- target: polished-forest-0215 — Nested joint and pair pagination now has a known-answer collector test; deliberate truncation loses the late collision and fails. CLI suite 706 passed, 1 skipped. No provider call before reset; F4 remains open.
