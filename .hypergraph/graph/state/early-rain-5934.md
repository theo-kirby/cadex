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

**The per-seed reader [rec: windy-tide-4050].** `docs/probes/ot9/runner/balance_eval.py`, pinned by `cli/tests/test_ot9_balance_eval.py`, reports peak tilt and its time, minimum chassis height, termination and digests, voids a run on unpinned artifacts, and gives an all-ten-seeds candidate verdict; its agreement gate reproduces ot8's no-policy fall (`fallen` at 0.66 s) [rec: windy-tide-4050] [rec: hidden-wing-6674].

**The frozen ten-seed evaluation of r3-ppo-1 passes 10/10 [rec: candid-wood-6113].** Seeds 0-9 via `./cadex params --set rollout_seed=S`, read against the MJCF and task pins: every seed ran 400 steps / 8.0 s at 50 Hz (401 solver frames), terminated by truncation, never fired `fallen`, none void. Peak tilt 2.78-5.35 deg, all at 0.06-0.08 s (the reset transient); minimum chassis height 105.05-105.83 mm; every seed on policy ef71f370, MJCF 933b1ac6, task 1f8c1040. `candidate_verdict` is recomputed from the rows by `test_the_first_ten_seed_evaluation_is_every_seed_on_one_reopened_policy`. Receipt: commit e5e181c9, `docs/probes/ot9/retained/r4-robin-eval-1.json` [rec: candid-wood-6113].

**Reported, not judged [rec: candid-wood-6113].** The policy drives about 0.84 m in nearly the same direction on every seed — systematic, and outside the bar, which does not measure position. Because `rollout_seed` is a script literal, each evaluated seed is its own accepted revision; the project's accepted revision is the seed-9 one, ae889a9b [rec: candid-wood-6113].

*Reconcile judgement*: the declared evidence for B3 is complete; status stays `working` because only the owner ticks the checkbox [rec: candid-wood-6113].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- windy-tide-4050 — balance reader built and gated against the no-policy fall
- hidden-wing-6674 — reader layout confirmed on a real trace; seed-0 diagnostic of r3-ppo-1
- candid-wood-6113 — frozen ten-seed evaluation of r3-ppo-1: pass 10/10, drift reported
