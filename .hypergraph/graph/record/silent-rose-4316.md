---
node_id: 3271ed65-5a8d-52da-8685-409b98b493bb
slug: silent-rose-4316
title: Operator review follows the current run and dispatched project
created_at: '2026-09-19T18:12:16+00:00'
parents:
- crimson-gate-0087
summary: ''
---
## What

Owner-directed operator dashboard following, implemented in
`tools/operator_review.py` and deployed as the persistent user review service.
The existing URL now serves ot7 Plover rather than ot6 Heron (ADR-387).

## Why

A fixed project argument left the website showing an old run despite ongoing
product-agent work. The owner requested that the current run always be shown.

## Method

Read the run from config and identity-checked attempt receipts; select the latest
explicit dispatch timestamp. Ignore copies, avoid moving backward during partial
writes, and clear selection on a new run without a project. Reuse the read-only
review handler with a request-local project snapshot. Add browser selection
polling and a run status strip; reload on a project switch. Install a persistent,
automatically restarting user service. Document the receipt contract and update
the review design spec. No live actor files or design scripts were edited.

## Result

`pixi run python tools/operator_review_selftest.py` passed the selection and real
HTTP regression covering project changes, run changes, copied receipts, partial
writes and the waiting page. `git diff --check` passed. Live Tailscale HTTP reads
returned ot7 / ot7-plover-c from operator-status and the same project with an
available accepted revision from api/project. The service is active and enabled.
An already-open old-server tab needs one refresh to load the new follower.
Subsequent switches happen automatically. Future drivers must publish the
receipt contract documented in docs/OPERATOR-REVIEW.md.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 406835d56d0f5a6485a42f327348d024d8eed1d3

## State Impact

- target: jolly-loom-0622 — The persistent operator dashboard follows the configured run and its latest explicitly dispatched project, with automatic browser reload and waiting state; ADR-387 and docs/OPERATOR-REVIEW.md define the driver receipt contract.
