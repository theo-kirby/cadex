---
node_id: 24e3c8c0-0e7f-5b5f-a09c-24d8b8597ea4
slug: brave-field-8478
title: Measure Reed baseline policies across ten rollout seeds
created_at: '2026-09-12T19:26:46+00:00'
parents:
- careful-gate-4868
summary: ''
---
## What

Measured the fresh Reed biped's retained probe3 checkpoint20 and final policies on seeds 0–9, with an eight-second episode limit, through 20 public CLI engine rollouts. Added the reproducible independent-copy harness, compact per-seed identity/results JSON and a user-facing interpretation in docs/HEADLESS-BIPED-REVIEW.md.

## Why

Advances D9's same-episode/seed comparative evidence. The baseline previously measured only seed 0; this unit establishes the declared ten-seed comparison set before a physical design edit. I narrowed the critic's requested edit/retrain/video/browser/restart sequence to this completed measurement unit rather than landing a partial training lifecycle. No parametric edit, retraining or new video was performed; these remain required. The critic's request to reconcile royal-water-8317 conflicts with this dispatch's explicit prohibition of reconciliation and state edits. I did not reconcile, did not follow the retired clearance/section plan, and leave the plan impact for an authorized reconcile pass.

## Method

From the repository root, ran `python3 docs/probes/reed-baseline/evaluate.py ~/cadex-projects/ot5-biped ~/cadex-projects/ot5-biped-baseline-seeds-v2`, exit 0. The harness copies the stopped source project, writes the retained playback script with each seed, and invokes `./cadex script --set ... --out ... --json` for each policy/seed, with a 120-second timeout per invocation. CLI accepted-script transactions verify the policy witness. Assertions pin model, task and policy hashes to the retained traces, compare both seed-0 traces in full against their originals, and compare the original project's entire non-Git file manifest before/after. Compact evidence is docs/probes/reed-baseline/results.json; full traces, accepted CLI history and receipts remain in the external copy's evidence/baseline-seeds directory. Existing project artifacts were reused; no old mechanism or checkpoint was imported from another design.

The initial harness assumed truncated meant incomplete output and rejected the checkpoint's completed eight-second episode. Corrected it to require end_time_s=8 when time-limited, and reran into a fresh destination; the initial external copy and /tmp/reed-baseline-evaluation.log are retained. Successful run output is /tmp/reed-baseline-evaluation-v2.log. `python3 -m py_compile docs/probes/reed-baseline/evaluate.py` and `git diff --check` passed. No engine/CLI/shell product files changed, no build or new dependency, and no full product-suite rerun; direct real-engine execution validates the documentation harness.

## Result

Checkpoint20 (74750cc6d8e7) survived 10/10 episodes for 8 seconds, with forward torso-link displacement mean 39.352 mm (34.295–45.941). Final policy (a06b4bf489529) fell in 10/10 episodes, observed mean 0.498 seconds (0.48–0.52), displacement mean 200.854 mm (189.535–210.536). Displacement is between published first/last torso-link poses; falls follow the declared engine termination, not an inferred pose threshold. These are poor-gait measurements, not evidence that extra travel means better walking. Both original seed-0 traces reproduce exactly and the source project's non-Git files remain byte-identical.

The documentation explains a longer foot as a plausible fore/aft support experiment, explicitly not an established cause or improvement. No design decision is implemented. Next work still requires the critic's review-driven parametric edit, bounded retraining and verified video, same seeds/episode comparison, two-design historical browser checks and dashboard restart during active training. This unit does not tick D2/D5/D6/D9 and claims no new browser test. Assumption: the source had no concurrent writer while copied and evaluated; the final manifest assertion passed. Plan reconciliation remains unresolved under the explicit contributor-only restriction.

Dispatch closed: 1 unit — measure and retain Reed's ten-seed pre-edit policy baseline

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 74b08bcde5077ec246362025f0772e177769c6de

## State Impact

- target: silent-river-6649 — D9 baseline now has 20 real public-CLI rollouts on seeds 0–9 at eight seconds: checkpoint20 survives 10/10; final falls 10/10 in 0.48–0.52 seconds. Original artifacts unchanged; edit/retraining/comparison lifecycle remains open.
