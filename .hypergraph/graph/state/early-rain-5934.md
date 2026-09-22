---
node_id: fab8229f-e774-54c6-aee5-47760bcaef42
slug: early-rain-5934
title: B3. Robin balances across the declared evaluation set.
created_at: '2026-09-22T17:39:47+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: working

## Current

**B3. Robin balances across the declared evaluation set.** On each of ten frozen reset seeds, the accepted policy runs the full 8 s at the task's 50 Hz control rate, stays within 30 degrees of accepted chassis attitude throughout, and never fires `fallen`. Report all ten trajectories' duration, peak tilt, minimum chassis height, termination, and policy/model digests. One failed seed fails this criterion; do not average it away. [rec: curious-branch-9704]

**The per-seed reader exists [rec: windy-tide-4050].** `docs/probes/ot9/runner/balance_eval.py`, pinned by `cli/tests/test_ot9_balance_eval.py`, reports peak tilt (from the solved keyframe) and its time, minimum chassis height, termination and digests, voids a run on unpinned artifacts, and gives an all-ten-seeds candidate verdict. Its agreement gate on ot9-robin's no-policy smoke reproduces G4: `fallen` at 0.66 s, 102.234 deg at 1 s [rec: windy-tide-4050]. The first real rollout trace confirms its layout — 401 `solver_output` frames for 400 steps [rec: hidden-wing-6674].

**One diagnostic seed, not the evaluation [rec: hidden-wing-6674].** A seed-0 rollout of r3-ppo-1 (ef71f370) ran the full 8.0 s with no `fallen`, peak tilt 5.35 deg, minimum height 105.4 mm, with about 0.84 m of xy drift. This is training-side diagnostics only; **the frozen ten-seed evaluation has not run**, so nothing yet counts toward the bar.

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- windy-tide-4050 — balance reader built and gated against the no-policy fall
- hidden-wing-6674 — reader layout confirmed on a real trace; seed-0 diagnostic of r3-ppo-1
