---
node_id: 87cefe0b-f85d-5de9-80b4-11899c677307
slug: lucky-shade-9428
title: F2. A run reads as what happened to it
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun4: **F2. A run reads as what happened to it.** A run stopped through `train_stop`, or `loop.request_stop` with a reason, reads as **stopped** with that reason in `/api/project`'s stage and on the page, never as failed. A walk killed without a stop request reads as **failed** (finish, test and give an ADR to the unaccepted ADR-558 work on branch `orun3-wip-adr558`). Tests cover stopped, killed, finished and crashed, through both `train_start` and `cadex walk`. The human owns the checkbox. No work recorded yet; open until a causally parented record shows the criterion met with measured evidence [rec: light-mist-9160].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-f2-run-reads-as-what)
