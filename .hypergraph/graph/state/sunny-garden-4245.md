---
node_id: b2e4c757-55b0-5ec0-aa43-641f631c0318
slug: sunny-garden-4245
title: R2. An arm reaches targets placed at random
created_at: '2026-09-30T07:04:58+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot11: **R2. An arm reaches targets placed at random.** - Under a goal-sampling task (P3), the final pre-registered confirmation evaluation meets the frozen reach spec on every seed, and meets the judge's bar. - The spec covers tolerance, time and overshoot, over targets the policy never trained on. - The mechanism may be an earlier arm (Heron, ot6–ot8) or a new one designed by the product agent. [rec: kind-spire-3578]

Declared target: `gap-r2-arm-reaches-targets-placed`. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**R2's measured bar is reached; the owner ticks it** [rec: tender-quartz-6082]. Status flipped to working on that measured, causally parented evidence, as for R3; the checkbox remains the owner's.

- **Project.** `ot11-heron-1`, a `cp -a` copy of `ot8-heron-b` (which stays read-only); model `183fabff…` (ot8's accepted MJCF), arm length 144.0 mm. The mechanism is fixed for the session, since a changed mechanism would move the held-out targets [rec: silver-harvest-8970].
- **Held-out targets.** Twenty targets drawn before any training by `runner/goals.py` (names no behaviour), committed in `retained/r2-heron-1-targets.json` (`8bb702af`) with the session pre-registration (`02603727`). Every evaluation's drawn targets equal the receipt within 4.9e-05 mm; no seed void [rec: silver-harvest-8970] [rec: cold-summit-2811].
- **Frozen spec handed over byte for byte** through `prompts/reach.loop.prompt.txt`; `rounds.py` has no reach-specific path; spec block canonical sha256 `61b25b02…` in all five reach evaluations [rec: silver-harvest-8970] [rec: cold-summit-2811].
- **Rounds.** Round 4's `3270ce26…` passed 9 of 10 (seed 1106 Q2 0.055 vs 0.05 arm lengths) [rec: silver-harvest-8970]. Round 5 (pre-registered `c758ffeb`; run `reach-r5`, seed 41, 800 it × 1024 envs, 890 s budget, warm-started from reach-r4 ckpt 475 with a reward-only task change: reach_scale 20→10 mm, fine_w 2→3) ended at the budget at iteration 422 without collapse; policy `6bb5a403…` (ckpt 400) passes **10 of 10**, seed 1106 Q2 7.92 → 3.33 mm. The session was launched by an earlier iteration and verified against its pre-registration rather than relaunched [rec: cold-summit-2811].
- **Confirmation 1** (registration `e80fd938`, committed before running; results `aa5b5a8e`): policy `6bb5a403…` at revision `13f9c63c…` meets Q1–Q4 on all ten seeds 1101–1110 over held-out targets. Worst Q2 final error 4.54 mm (limit 7.2), Q3 time to target 0.46 s (limit 2.0), Q4 overshoot 0.153 (limit 0.20). Metrics equal reach-r5's round evaluation exactly (deterministic per frozen seed) [rec: tender-quartz-6082].
- **Blind judge** (`runner/judge.py reach`, three calls a seed, claude-opus-5-5): bar met on 1101/1105/1110 with totals 12, 12, 12; spec and judge agree [rec: tender-quartz-6082].

## Negative knowledge

- [scope: reach policy 6bb5a403 on ot11-heron-1 under the frozen reach spec | confidence: high | evidence: tender-quartz-6082] **The holds twitch, and no predicate reads it.** Seed 1110's target-B hold has 16 of 170 frame steps over 1 mm (largest 4.8 mm in 20 ms, 78 mm tip path); six of ten seeds exceed 30 mm tip path in at least one hold; 1102 holds still. Q2 bounds every excursion inside 7.2 mm, so the verdict stands, and the judge's frames 0.2 s apart mostly miss it. Measuring hold steadiness would change the frozen contract (a recorded decision re-evaluating every earlier policy) and was not taken; it is a REPORT.md remaining defect and a sim-to-real candidate.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- silver-harvest-8970 — reach loop on ot11-heron-1: twenty held-out targets pre-drawn, four rounds, best policy 3270ce26 passes 9 of 10 seeds
- cold-summit-2811 — reach round 5: warm start from r4, policy 6bb5a403 passes 10 of 10 seeds (1106 Q2 7.92 -> 3.33 mm)
- tender-quartz-6082 — pre-registered confirmation 1: 10 of 10 held-out seeds pass, judge 12/12/12; R2's measured bar reached; hold twitch recorded
