---
node_id: bcf52146-e4c5-5311-b46c-9d71d6cae19e
slug: lucky-creek-4303
title: Stopped walk descendants keep their full cleanup grace
created_at: '2026-09-08T19:57:28+00:00'
parents:
- tidy-cove-8382
summary: ''
---
## What

Corrected `_stop_leg` so a direct child exiting on SIGTERM cannot shorten the
process group's full termination grace. A monotonic deadline preserves the
remaining grace before the unconditional SIGKILL. Added a real subprocess
regression, updated CLI documentation and the project-doc scaffold, and logged
ADR-261's correction and a completed ROADMAP item.

## Why

This answers the critic rejection of `tidy-cove-8382`, prioritized explicitly
by the overseer. It advances the charter criterion **The walk exists and is
tested headlessly** (`crisp-reef-5607`): a bounded unattended walk must let its
descendants finish cleanup, even after their direct parent has exited.
Assumption: the explicit one-unit dispatch budget governs; the overseer's
second requested unit remains next rather than combining two changes here.
The causal parent is the rejected stop implementation, whose follow-up this is.

## Method

The POSIX regression starts a parent with default SIGTERM handling and a
separate descendant in the same group. It waits for the descendant to install
its handler, then calls `_stop_leg` with a one-second test grace. The descendant
needs 0.3 seconds to write its cleanup marker; the test asserts that marker,
the parent's SIGTERM exit, and at least the full grace elapsed. Both subprocesses
have bounded lives, with final group cleanup in the test.

Before the fix, `pixi run python -m pytest cli/tests/test_walk.py -k
preserves_descendant_cleanup_grace -q` failed with “group kill interrupted
descendant cleanup” (1 failed, 43 deselected). After the fix the same regression
passed (1 passed, 43 deselected, 1.64 s). The complete zone gate was
`pixi run python -m pytest cli/tests`; its output remains outside the repo at
`/tmp/cadex-iteration28-cli.log`. No engine, protocol, payload or shell code changed.

## Result

Full CLI suite: **240 passed in 226.73 s**, exit 0, no skips. `git diff --check`
passed. The group kill remains unconditional, with the existing final drain
bound; only the prematurely shortened cleanup grace is corrected.

This unit fixes the critic rejection rather than providing another lifecycle
rehearsal. The graph already records the charter walk criterion as working;
no new criterion closure is claimed. The remaining planned evidence is the
`ot4-quill` parameter-only iterate: `--set stroke=60`, no prompt, explicit CPU,
5 iterations, 16 environments, seed 0, trainer timeout 600 and finite leg bound,
into a fresh project run directory. Verify objective comparability and report
both travel channels and reward deltas without claiming significance from one
sample. Generated outputs stay outside this repository. Comparison identity
and the prompt-driven project-history revisit remain later plan units.

Dispatch closed: 1 unit — preserved the full descendant cleanup grace, proved the regression fails before the fix, and passed all 240 CLI tests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 56c071dbeac32d837ef0849eb9133ee917a80e6c

## State Impact

- target: crisp-reef-5607 — Corrected the critic-rejected termination grace: a monotonic deadline preserves the full grace after a fast parent exit before unconditional group SIGKILL; the real descendant cleanup regression fails before the fix and all 240 CLI tests pass.
