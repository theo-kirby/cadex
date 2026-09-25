---
node_id: a308fe3a-a414-5d3f-9712-97f6eea8e9e0
slug: twilight-flint-8205
title: B1. The experiment has a frozen baseline and evaluation contract.
created_at: '2026-09-22T17:39:46+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: working

## Current

**B1. The experiment has a frozen baseline and evaluation contract.** `docs/probes/ot9/README.md` names ot8 Robin's script, accepted revision, geometry digest, MJCF and task digests. It fixes ten evaluation seeds before training, the 8 s / 30 degree / no-`fallen` bar, training and evaluation commands, and accounting for failed, interrupted and void runs. Keep the same seeds across revisions and publish every result, including failures. [rec: curious-branch-9704]

**The contract exists [rec: mild-crest-2685].** `docs/probes/ot9/README.md` and `contract.json` (commit a80484a2) pin ot8-robin from its own artifacts: script f805fdc2, revision 0b438561, digest b933d905, geometry 34898ebc, MJCF 933b1ac6, task 1f8c1040. Evaluation seeds 0-9 were frozen before any training; the bar is 8 s / 400 steps at 50 Hz, peak tilt at most 30 deg and no `fallen`, on every seed; train, install and evaluate commands are fixed; runs are accounted as completed / failed / interrupted / void. `cli/tests/test_ot9_contract.py` pins it [rec: mild-crest-2685].

**The per-seed reader it called for has since landed** (`docs/probes/ot9/runner/balance_eval.py`, see B3) [rec: windy-tide-4050]. Status stays `working`, not complete, because only the owner ticks the checkbox; the maintainer's judgement is that the declared evidence for B1 is now present.

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- mild-crest-2685 — contract written and test-pinned, pins read from ot8-robin's artifacts, seeds 0-9 frozen
- windy-tide-4050 — the per-seed trace reader B1 left outstanding now exists
