---
node_id: 5de906d9-cbfa-51a5-b7a0-e2e4e2630493
slug: quiet-arbor-0259
title: Freeze assembled training review inputs across accepted design changes
created_at: '2026-09-12T18:38:22+00:00'
parents:
- misty-trail-1655
summary: ''
---
## What

Freeze a walk's assembled review inputs before training (ADR-291). New walks retain training-view.json, run-local STL meshes with digests, component identities and placement sources, parameter values/specs and project-document snapshots. Later status writes preserve the training documents and specs. The dashboard uses the retained assembly before legacy export fallback; missing, modified or symlinked meshes are unavailable. Training refuses an accepted revision/digest changed between retention and dispatch.

## Why

This unit advances D2 (historical model/spec identity) and D5 (retention across design changes), following misty-trail-1655's demonstrated absence of assembled placements. It implements the critic's next retention unit before another biped training attempt. It does not reconstruct probe2's missing history.

The critic also requested reconciliation of young-crane-9546 first. This dispatch explicitly forbids reconciliation, state/view edits and hypergraph update without exceptions, so I did not perform that prerequisite. The stale clearance-first plan remains pending for a separately authorized reconcile pass; it did not guide this unit. No goal or generated state/plan view was edited.

## Method

Retain the accepted review model under the project lock before the walk invokes its train leg; copy its mesh bytes, publish the versioned marker last, and preserve it on subsequent writes. Use the existing accepted-model reader and permitted-path resolver, with mesh digests checked on serving. The train leg checks the retained identity after rebuilding and before dispatch. No engine or shell code, protocol, payload, dependency, or production training artifacts changed.

The new headless browser regression changes accepted revision A to B, changes B's assembled placement and parameter values/defaults, changes DECISIONS.md, deletes A's staging directory, and writes a failed run status. It checks the historical revision label, different camera target, rendered pixels, retained body placement [5, 0, 10] mm, parameter value 90/default 80 rather than the current 120/110, original decision text and exact mesh bytes. It additionally refuses modified and symlinked meshes and an incomplete snapshot. A real-engine/fake-trainer test rejects a changed identity before producing a policy.

Validation commands and results:
- pixi run test-engine: 2103 passed, 54 skipped, 281.97 s.
- pixi run python -m pytest cli/tests -q: initial 357 passed, 1 skipped, 3 failed against old snapshot-timing assertions. Corrected those assertions (including an honestly empty pretraining document snapshot).
- pixi run python -m pytest cli/tests --lf -q: collected the full suite on the final source; 361 passed, 1 skipped, 295.80 s. Includes the new regression and changed-identity guard.
- pixi run python -m pytest cli/tests/test_review_server.py cli/tests/test_review_record.py -q: 48 passed, 1 skipped, 51.53 s; headless browser executed.
- git diff --check: exit 0.

Two extra walk-test invocations briefly overlapped the initial CLI suite and could launch toy trainers concurrently. I detected the overlap, terminated both extra invocation trees, and then ran trainer-capable verification serially. This was a verification scheduling deviation from the one-training-at-a-time rule; no fresh-biped training was launched and no retained biped history was altered. No build was necessary for this CLI-only change.

## Result

The demonstrated retention gap is closed for new walks: an earlier training run can show its own assembly, specs and decisions after the accepted design and staging cache change. D2 and D5 gain automated browser evidence; neither the full real-biped D5 lifecycle nor D9 is claimed complete. Missing old history stays missing. Copying must retain the entire run directory, including training-view.json, training-view/ and project-docs/; docs/CLI.md and the roadmap describe this contract. No new dependency. The next real design-change/retraining attempt remains work for another unit, and the stale plan still needs authorized reconciliation.

Dispatch closed: 1 unit — retain assembled training views and immutable specs/decisions across design changes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 0bcc8e20b3530f410e3f4edf12fc4303c7068330

## State Impact

- target: shy-meadow-0959 — New walks retain assembled model placements and checked mesh bytes before training; browser regression preserves historical placement and specs after accepted revision change and staging deletion. Real fresh-biped historical lifecycle remains open.
- target: sharp-union-6036 — Training-start document/spec snapshots survive later status writes and accepted design changes; changed identity before dispatch is refused. D5 gains browser retention evidence, not the real biped revise/retrain pass.
