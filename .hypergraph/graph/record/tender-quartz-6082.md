---
node_id: 24843f65-19f4-59d6-8169-6c14035ca015
slug: tender-quartz-6082
title: 'ot11 R2 confirmation 1: policy 6bb5a403 passes the frozen reach spec on 10 of 10 held-out seeds; judge 12/12/12; hold twitching recorded'
created_at: '2026-09-30T21:09:32+00:00'
parents:
- cold-summit-2811
summary: ''
---
## What

R2's confirmation evaluation for reach on `ot11-heron-1`. I pre-registered it (`e80fd938`), ran it once, and recorded the verdict in this iteration (`aa5b5a8e`). The policy is `6bb5a403…` (reach-r5, checkpoint 400) at accepted revision `13f9c63c…`. The evaluation passes the frozen reach spec on 10 of 10 seeds, on the held-out targets. The blind judge's bar is met on every judged seed: 1101, 1105 and 1110 score 12, 12 and 12.

## Why

This is the critic's named next unit. R2 is the highest-ranked open criterion that has a passing round behind it. Round 5 passed 10 of 10 seeds [rec: cold-summit-2811], and its pre-registration made that pass the condition for registering a confirmation. I did everything the critic asked:
- The registration fixes policy 6bb5a403 at revision 13f9c63c, spec 61b25b02, the held-out target receipt `r2-heron-1-targets.json` (8bb702af), seeds 1101–1110, and the judged seeds and bar as in R3's confirmation.
- It was committed before the run.
- It was run once, and the verdict is recorded in the same iteration.

## Method

- **Registration.** `docs/probes/ot11/retained/r2-confirm-1-registration.json` has the same shape as R3's. It adds a void rule: a drawn target more than 0.001 mm from the receipt voids its seed. The detail sheet is explicit at 4.0 s with frames 0.2 s apart, which is the contract's reach detail.
- **Evaluation.** From the projects directory: `./cadex evaluate --project ot11-heron-1 --out ot11-heron-1/evaluations/r2-confirm-1 --film 1101,1105,1110 --detail-start 4.0 --detail-step 0.2 --json`. It exited 0.
- **Checks.**
  - The spec block hashes, as canonical JSON, to 61b25b02.
  - The policy, task (e912e040) and model (183fabff) digests match the registration.
  - The worst difference between a drawn target and the receipt is 4.9e-5 mm.
  - No seed is void. There were no solver warnings. Every episode ran 8.0 s at 50 Hz and ended by truncation.
  - Every seed's metrics equal those of the reach-r5 round evaluation exactly.
- **Judge.** `runner/judge.py reach` ran on each judged seed, three calls each, with runner digest c4613d74. All nine calls came from claude-opus-5-5 with no refusals or retries.
- **Receipt.** The receipt copies the evaluation with the engine paths stripped.
- **Diagnosis of a judge note.** One call on 1105 scored V2 and V3 at 2 for tip jitter in the hold. I measured the tip's frame-to-frame motion (c_forearm origin) against the goal in every seed's trace.
- **Tests.** `pixi run python -m pytest` on the five ot11 suites in `cli/tests`: 78 passed. No code changed.

## Result

**R2's measured bar is reached.**

- **Spec.** 10 of 10 seeds pass Q1–Q4 on targets never trained on.
  - Q2 worst final error: 0.014–0.032 arm lengths (1.99–4.54 mm), against a limit of 7.2 mm.
  - Q3 worst time to target: 0.08–0.46 s, against 2.0 s.
  - Q4 worst overshoot: 0.021–0.153, against 0.20.
- **Judge.** Medians are 3/3/3/3 on all three judged seeds. The spec and the judge agree, so there is no contradiction to diagnose. The owner ticks R2; I do not.

**A new defect, recorded rather than acted on: the holds twitch, and no predicate reads it.**
- On seed 1110's target-B hold, 16 of 170 frame steps are over 1 mm. The largest is 4.8 mm in 20 ms, the tip travels 78 mm in all, and the error ranges 0.37–3.06 mm. All three judge calls scored 1110 at 3.
- Six of ten seeds have over 30 mm of tip path in at least one hold. Seed 1102 holds dead still.
- Q2 bounds every excursion inside 7.2 mm, so the verdict stands.
- The judge's twelve frames 0.2 s apart mostly miss the twitching.
- Measuring hold steadiness would change the frozen contract. That is a recorded decision that re-evaluates every earlier policy, and I did not take it.
- It goes into REPORT.md's remaining defects. It is also a candidate for the long-term sim-to-real rung (actuator limits and noise).

**Next.**
- There are now three unfolded records (cold-summit-2811 and this one on top of silver-harvest-8970's fold, and the critic said three), so **reconcile next**.
- After that, the open criteria are R1 (walk) and C1.

Dispatch closed: 1 unit — R2 confirmation 1 pre-registered and run once: 10/10 seeds pass the frozen reach spec, judge 12/12/12, hold twitching recorded as an unmeasured defect

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: aa5b5a8ee72ba82393740ec32e60c8fea28a6efd

## State Impact

- target: sunny-garden-4245 — R2's pre-registered confirmation 1 (e80fd938, aa5b5a8e) passes: policy 6bb5a403 at revision 13f9c63c meets Q1-Q4 on all ten seeds over held-out targets (Q2 worst 4.54 mm of 7.2) and the judge's bar on 1101/1105/1110 (12, 12, 12); measured bar reached, owner tick pending; holds twitch (1110: 78 mm path) unmeasured by any predicate
