---
node_id: 3f8e6de1-246e-5775-b23c-a6f6f000ad0f
slug: rough-bell-4381
title: 'ot11 R1 walk round 8 published: r8-stance stands on one diagonal pair; evaluation void (HIP_MM digit); mechanism change in bounds'
created_at: '2026-10-01T04:22:49+00:00'
parents:
- red-mountain-4965
summary: ''
---
## What

Published walk round 8: `r8-stance`, the first run of session 3 and the first in which the product agent changed the mechanism. It went into the README section, a path-free receipt (`retained/p4-quad-1-r8-evaluation.json`), the overview and detail filmstrips of seed 1101 (≤300 KB each, dark floor), the run ledger (`retained/ot11-runs.json`, 14 runs, 21,692.35 s supervised) and REPORT.md row 14, with test_ot11_report's count moved to 14. Commit `ebffb3d1`.

## Why

The critic asked for exactly this unit. Once r8-stance had finished and been evaluated, it was to be published from quad-1-s3 and the ledger, with four checks:
- the spec block against the mechanism rule;
- the model digest;
- whether the stance change stayed inside the bounds;
- the SPEC_LIFT caveat, if HX moved.

All four are done. The critic also asked that an early driver stop caused by the evaluation count be recorded as an interruption. That stop has not happened yet. Its exact conditions are written down below. No other GPU job was started.

## Method

- **Waited for the run, without polling the GPU.**
  - r8-stance ran from 03:41Z to 04:14Z. The agent evaluated its final policy at 04:19Z.
  - It had also evaluated the iteration-300 checkpoint mid-run, at 04:01Z.
- **Mechanism check.**
  - Diffed r6's MJCF (`ade106a6…`) against r8's (`3e6933ec…`).
  - With every `pos`, `quat` and `fromto` attribute stripped, the two files are byte-identical. That covers the option and compiler lines, the floor plane, the joint ranges and damping, the masses and inertias, and all eight actuators.
- **Script check.**
  - Diffed `script_history` 0044 → 0049 (trained) → 0052 (evaluated). The only change from 0049 to 0052 is the policy weights.
- **Spec block check.**
  - Compared each revision's block line by line to `retained/walk-spec-block.txt`.
  - Traced where `rig.hip_height_mm` comes from: `CadexDynamics.py:8345` averages the hip anchors' z from the compiled model, and the MJCF writes them to six significant figures.
- **Read the evaluation and the film.**
  - Read per-seed and per-foot numbers from the evaluation report.
  - Looked at both filmstrips.
- **Built the receipt** in round 7's schema with an inline script, asserted it holds no machine path, and re-ran the ledger with `runner/run_ledger.py`.

## Result

**Round 8 measured.**
- r8-stance ran from a fresh start: seed 71, 800 iterations × 2048 envs, 2,400 s budget.
- It finished all 800 iterations in 2,008.15 s supervised (1,858.5 s in the trainer). The trainer was `97bc1d9a…`, recorded in every checkpoint.
- The training reward went from −2.14 to −3.06, then to −0.28 per step. It was never positive.

**The final policy (`749e0bce…`, revision `a0460e13…`) stands on the FL+RR diagonal and holds FR and RL in the air for the whole episode.** On the eight complete seeds:
- FR and RL have duty factor 0.00, and their lowest points are 3–10 mm above the floor.
- FL and RR carry the robot and slide (slip share 0.68–1.00).
- W3 is −0.12 to 0.15, W4-heading reaches 62°, and W5 is 0 steps on every seed.
- Seeds 1109 and 1110 tipped by step 22.

The new `trot` term pays one pair lifted while the other stands, with no requirement that the pairs alternate. Its median is +405 per episode, the largest positive term after `alive`. The posture is visible in every frame of the film.

**W10 moved for the first time.** It went from −0.175..−0.092 hip heights in round 6 to −0.095..−0.061 here. That is still below −0.05 on every seed, and it was measured on a two-foot stance, not a gait.

**The mechanism change is inside session 3's bounds.**
- Model `ade106a6…` → `3e6933ec…`, the same structure with only the poses changed. The base is 10.25 mm higher. Four legs, the same feet, catalog actuators at the same limits, floor and global physics unchanged.
- The four solved-pose foot–floor contacts became zero-gap clearances. That is a design-time assembly check, not in the MJCF.
- HX did not move, so SPEC_LIFT has the same value. The feet now sit about 3 mm from the hip in x, inboard of the formula's HX+20 lever, so the drawn lift is slightly larger than strictly needed. That is conservative, not a contract change.

**The evaluation is VOID under the pre-registered mechanism rule.**
- The block differs from the retained one only on `HIP_MM = 106.9488` (plus a trailing comment). WEIGHT_N matches exactly.
- The rig states 106.949, which is 106.9490 at the block's four printed decimals.
- The effect is bounded at 0.0002 mm/s on the drawn command, two parts per million. W6 and W10 use the rig's own hip height.
- It is still void and is published as void, not as a fail. The iteration-300 mid-run evaluation (`96ff3b79…`, revision `2029ad21…`, 0/10, four seeds tipped) carries the same line and is void too.
- R1 is unchanged: no walk evaluation has passed in eight rounds.

**Concerns for the next iteration:**
1. **The `HIP_MM` digit will void every later session-3 evaluation unless the agent corrects it.**
   - The actor must not edit the agent's script or prompt mid-session, and the pre-registered continuation does not mention it.
   - If the next run is evaluated with 106.9488 again, publish it as void too. The receipt's `spec_block` field records the reasoning.
   - A product-side guard would remove this whole class of error: `evaluate` could warn when a spec constant differs from the rig, or the block could read `HIP_MM` from the rig. That is a P2/P4 tool change for a later unit, after the session ends, not during it.
2. **Driver standing.**
   - The ledger holds 11 evaluations, which equals `--max-runs 11`, with every run ended. `rounds.py` checks only between turns.
   - If turn 1 ends without registering another run, the driver stops after one of three runs. The cause is the mid-run checkpoint evaluation, which the pre-registration's "one evaluation per run" arithmetic did not foresee. Record that as a **driver interruption, not an attempt**.
   - At 04:22Z turn 1 was still running and the driver was alive. The agent had set `policy_on=0, hip_pose=30, knee_pose=-60`, apparently to measure the passive stance. No r9 was registered yet.
3. The tail is now two unreconciled records.

Tests: `cli/tests -k ot11` 73 passed. Docs, receipts and a count change only, so no engine file changed and no full suite was needed.

Dispatch closed: 1 unit — walk round 8 (r8-stance) published: stands on one diagonal pair, 0/10 measured but VOID under the mechanism rule (HIP_MM 106.9488 vs rig 106.949); mechanism change inside bounds; ledger 14 runs / 21,692 s

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: ebffb3d1e0f95243d42127270bfb3604bbc0baae

## State Impact

- target: smooth-fountain-9832 — walk round 8 (r8-stance, first mechanism revision: stance hip 18/knee -30, base +10.25 mm, MJCF otherwise identical, inside session-3 bounds; diagonal 'trot' reward term) finished 800 it in 2,008 s GPU; final policy stands on the FL+RR diagonal with FR/RL aloft all episode (W3 -0.12..0.15, W5 0 steps, W8-low 0.00), W10 improved to -0.095..-0.061 HH but fails every seed; the evaluation and its iteration-300 mid-run evaluation are VOID under the pre-registered mechanism rule (HIP_MM 106.9488 vs rig 106.949 at four decimals); R1 still unmet; driver at 11/11 evaluations may stop session 3 early (would be an interruption)
- target: golden-bay-4173 — run ledger at 14 runs / 21,692.35 s supervised GPU (REPORT.md row 14, retained/ot11-runs.json, test_ot11_report count 14)
