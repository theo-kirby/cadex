---
node_id: 31a64e70-b15b-5990-a217-c85fd54d7527
slug: square-crane-0130
title: 'ot11 P1 W10 trust: round-4 foot lows fall in the reset drop, FL stance fails anyway; passive robot rests inside W10 but fails it from any >=0.5 mm drop'
created_at: '2026-10-01T01:16:33+00:00'
parents:
- northern-eagle-1465
summary: ''
---
## What

A measurement of whether the frozen walk predicate W10 ("on the floor, not in it": every foot's lowest height over every frame ≥ −0.05 hip heights, −4.84 mm on ot11-quad-1) can be passed by a quadruped at rest. Two parts, with W10 left untouched: (1) where each foot's lowest frame falls in round 4's ten evaluation traces (reset drop / stance before the shove / after the shove); (2) a passive zero-action rollout of the evaluated model on CPU MuJoCo. Commit `9f05fce0`: `docs/probes/ot11/runner/w10_trust.py`, receipt `docs/probes/ot11/retained/p1-walk-w10-trust.json`, and a README section, "W10 at rest: the reset drop fails it, standing does not".

## Why

Evaluation trust outranks the behaviours, and walk session 2 is training against W10 right now. Round 4 failed W10 on 10/10 seeds while standing still, and the agent's closing report blamed the reset drop. That was a hypothesis, not a measurement. The critic named this unit.

**Deviation: no reconcile.** The critic asked for a reconcile first (fold windy-nest-5080 and northern-eagle-1465 into smooth-fountain-9832 and late-pond-2851). This dispatch's rules forbid the reconcile skill in a work iteration, with no exceptions, so I did not run it. The tail is now 3 unreconciled records. A reconcile pass is due and should be the next housekeeping iteration.

## Method

- **Phases.** For each `seed-*-trace.json` in `ot11-quad-1/evaluations/ce8d19639f13-d2dcaf39ba21`, each foot's height series is read with W10's own reader: `CadexEvaluation.foot_series` over `CadexDynamics.evaluation_rig(model, feet=c_foot_*)`. The model is round 4's MJCF, sha `ade106a6…`, the same one the evaluation used. A lowest frame before the 1.0 s settle counts as the reset drop.
- **Passive rollout.** Pixi env, CPU (`CUDA_VISIBLE_DEVICES=` empty), mujoco 3.10.0, timestep 0.002. The model starts at its `solved` keyframe with ctrl = 0, which makes every position servo hold the solved pose. It is dropped from 0, 5, 10 and 15 mm for 10 s, then scanned at 0–5 mm in 0.5 mm steps for 2 s each. Feet are read at the trace's 50 Hz as sphere centre z − radius.
- `w2-2`'s fixture (`cadex_tests/evaluation_fixtures.w2_2`) was re-read the same way to see whether a settle-window W10 would still catch it.
- Ran the ot11 cli tests and licensing compliance: 88 passed, 1 skipped. No engine or trainer code changed, so neither full suite was re-run.

## Result

**True now:**
- **Round 4.** The deepest frame falls in the reset drop (0.06–0.38 s) for FL 10/10, FR 10/10, RL 9/10 and RR 5/10; the rest fall after the shove. But FL also *stands* at −7.08 to −6.97 mm in steady stance on every seed. That is past −4.84 mm without the drop, so **round 4's W10 verdict does not depend on the drop.**
- **Passive rollout, at rest.** It passes W10, by 0.53 mm (front feet −2.80 mm, rear −4.31 mm). Round 4's −7.0 mm FL stance is therefore the policy's posture, not the contact model's.
- **Passive rollout, dropped.** It fails W10 from any drop of 0.5 mm or more (−4.87 mm at 0.5 mm, −7.34 mm at 5 mm, −10.15 mm at 10 mm). The spec's reset draws a lift of 0–5 mm above tilt clearance, and the ten evaluation seeds start 5.41–9.94 mm up. **So a pose-holding robot fails W10 on every evaluation seed in its first 0.4 s, before any gait.** W10 is passable only by a policy that cushions its landing. That makes it partly a property of the reset, while W3, W4 and W8 are read after the settle.
- **w2-2.** Read after the settle, it still fails W10: FR −21.29 mm at 2.10 s, FL −17.58 mm at 5.78 s. A settle-window reading would keep both known verdicts.
- **W10 is unchanged and every verdict stands.** Reading W10 after the 1.0 s settle is named in the README as a possible *recorded contract decision*. It would re-evaluate w2-2 and walk rounds 1–4, and it should land between session-2 rounds, not during one. Not taken here: it is a contract change and deserves its own unit and ADR.

**State of other work:**
- Walk session 2 (`rounds.py`, out `ot11-notes/quad-1-s2`) is running. Its first run, `r5-swing`, was still training at this record's time, so no session-2 round had landed to publish.
- `test_the_same_walk_handles_a_linear_carriage` was not run this iteration, because no engine code changed. There is no traceback to capture.

**Concerns:**
- The passive rollout applies lift only. The seeds' reset tilt (≤3°) was not reproduced, and would make one corner land first and deeper.
- The reconcile is overdue: the tail holds 3 records.

Dispatch closed: 1 unit — W10 trust measured: round 4's lows are in the reset drop but its FL stance (−7.0 mm) fails W10 anyway; a passive robot rests inside W10 and fails it from any ≥0.5 mm drop, against seed lifts of 5.4–9.9 mm; W10 unchanged, a settle-window decision named.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 9f05fce09f1f8c5ed2925bf56b7edd6029f40225

## State Impact

- target: rough-shore-6557 — W10 measured for trust (commit 9f05fce0): a passive zero-action quadruped rests inside W10 (rear feet -4.31 mm vs -4.84 limit) but fails it from any reset drop >=0.5 mm, and the walk spec's seeds drop 5.4-9.9 mm, so W10 over every frame is partly a reset property; round 4 and w2-2 still fail W10 if read after the 1.0 s settle; W10 unchanged, a settle-window reading is a candidate recorded decision that would re-evaluate w2-2 and rounds 1-4
- target: smooth-fountain-9832 — round 4's W10 failure is the policy's posture (FL stance -7.0 mm on all ten seeds), not only the reset drop; any R1 policy must also cushion its landing to pass W10 as frozen
