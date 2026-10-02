---
node_id: 38a7169d-3310-5801-a9ea-6b0180e97dca
slug: pale-ember-2389
title: 'ot11 P1 W10 read after the settle (ADR-467): w2-2 and walk rounds 1-5 re-read exactly, no verdict moved; r5-swing walks forward and fails 0/10'
created_at: '2026-10-01T01:58:34+00:00'
parents:
- square-crane-0130
summary: ''
---
## What
- A recorded contract decision: walk predicate W10 ("on the floor, not in
  it") now reads each foot's lowest height **after the 1.0 s settle**, as
  W3, W4 and W8 already did. Its limit, −0.05 hip heights, is unchanged
  (ADR-467, commit `6ea2e66e`).
- `CadexEvaluation.gait` adds `settled_lowest_height_mm` and
  `settled_lowest_height_hip_heights` per foot. `foot_lowest_hip_heights_min`
  reads the settled value, and `lowest_height_mm` over every frame stays in
  the report.
- Every earlier walk policy was re-evaluated from its stored traces with a
  new runner, `docs/probes/ot11/runner/w10_reread.py`. The receipt is
  `retained/p1-walk-w10-reread.json`.
- Updated: `contract.json` (W10's row and `decisions`), the ot11 README
  (table row and a decision section), the XSCRIPT.md metric row, and P1's
  `runner/measure.py`.

## Why
The critic's message had two parts.
- **Settle W10 before r6 is registered.** Evaluation trust outranks
  training, and square-crane-0130 measured that W10 over every frame fails
  a pose-holding robot on every seed because of the reset drop. I chose to
  change W10 rather than keep it: over every frame it measured the reset,
  not what ADR-454 says it measures. The settled reading still catches
  both known failures.
- **Publish r5-swing first.** **Deviation:** I did not publish r5's round
  receipt, filmstrip or README round section. The unit is the W10 decision.
  r5's evaluation is included in the re-evaluation, but its round
  publication is the next unit.
- **r6 was registered before the decision landed in the record.** The
  agent registered `r6-trot` (started 01:35Z) while this unit ran. The
  code change was live earlier, as described under Result.
- I started no GPU job. But the full `cli/tests` run touched the GPU; see
  Result.

## Method
- **Code and failing-first tests.**
  - New test
    `test_a_landing_from_the_reset_lift_is_not_read_as_standing_in_the_floor`
    uses a new `trot(landing=, landing_s=)` fixture knob: a 10 mm dip before
    0.4 s, then 4 mm or 6 mm stance sink.
  - The `w2-2` fixture test now also pins each foot's settled depth
    (−17.58, −21.29, −8.08, −8.90 mm).
  - Both tests failed with the CadexEvaluation change stashed, and both
    pass with it.
- **Re-evaluation.** `w10_reread.py` loads each stored `evaluation.json`.
  - It finds the evaluated MJCF in the project by `model_sha256`, and
    rebuilds the feet rig with `CadexDynamics.evaluation_rig`, because the
    report's rig omits the foot geoms.
  - It re-measures each seed's stored trace with `CadexEvaluation.measure`.
    Shoves come from the spec and the draw, and the command is the
    `settled_command` of the trace's goal channel.
  - Its gate: every stored metric must re-read exactly (abs 1e-12), and the
    stored W10 must equal the every-frame minimum. It then re-holds the
    spec's predicates.
  - It ran on CPU (`CUDA_VISIBLE_DEVICES=` empty) over seven evaluations:
    `ot11-w2-negative` `064d8d7cd34c` (P2) and `60f655537c0b`, and
    `ot11-quad-1` rounds 1–5 (`8498db6e1ff5`, `80ba9fb9905e`,
    `9f711fcaa419`, `ce8d19639f13`, `dee2391353b7`).
- **Suites.**
  - `pixi run test-engine`: 2,510 passed, 60 skipped.
  - Full `cli/tests`: 2 failed, 1,254 passed, 1 skipped. Both failures were
    then fixed or explained; see Result. After the fix, `test_ot11_judge.py`
    plus the carriage test passed 18 of 18 on CPU.
  - `test_ot11_contract` and `test_ot11_measure`: 43 passed.

## Result
**True now:**
- **The contract.** W10 is read after the settle, with the same limit.
  ADR-467 is in `contract.json` `decisions`.
- **The re-evaluation.** All 70 seeds across 7 evaluations re-read
  exactly. **No seed's verdict moved, and W10 still fails every seed of
  every evaluation.**
  - `w2-2` still fails W5 and W7 (stepping and slip) on every seed of both
    evaluations, plus W10 (−0.259 to −0.142 hip heights). That is the right
    reason.
  - Only round 4 moves: −0.131..−0.085 becomes −0.083..−0.072, because its
    front-left foot stands 7 mm in the floor.
  - Two evaluations (w2-2 `60f655`, round 1) each have one seed that ends
    inside the settle. W10 is then "not measured" and fails, as W3 already
    did.
- **Timing (honest).** Walk session 2's `cadexd` imports the engine from
  `src/Mod/cadex`, so the new reading went live when the source was edited
  (about 01:20Z), not at an install.
  - r5-swing's evaluation (`dee2391353b7-6a7c89de9ade`, 01:28Z) ran on the
    new code. Its report carries `settled_lowest_height_mm`.
  - On all ten of its seeds the deepest frame is after the settle, so both
    readings give identical numbers and the same verdict.
  - `build/release` and the staged payload still hold the old
    CadexEvaluation.py until the next `build-engine`/`stage-engine`. The
    live session does not use them.
- **r5-swing is a real change: it walks forward.** It fails 10 of 10, but
  W3 passes 9/10 (speed ratio 0.82–1.25), W1 and W2 pass 10/10, and
  W4-heading passes 10/10.
  - It still fails W5-steps (1–6 steps on the worst foot; passes on 1
    seed), W5-share (0/10), W7, W8-low, W9 and W10 (−0.209 to −0.138 hip
    heights).
  - Training reached a best of 1.01/step at iteration 773 and ran 780
    iterations in 1,898 s on GPU.
  - Not yet published: round receipt, filmstrip, README round section. That
    is the next unit, along with the agent's own diagnosis from its
    transcript.
- **Session 2 is live.** The agent registered and started `r6-trot` (760
  iterations, started 01:35Z). It was still training at record time.

**Concerns:**
- **The full `cli/tests` run reaches for the GPU.**
  `test_walk.py::test_the_same_walk_handles_a_linear_carriage` failed with
  `jaxlib XlaRuntimeError: RESOURCE_EXHAUSTED … CUDA_ERROR_OUT_OF_MEMORY`
  while r6-trot held the GPU. This is the traceback the last record asked
  to capture. It passes on CPU (`CUDA_VISIBLE_DEVICES=`
  `JAX_PLATFORMS=cpu`). r6 kept running. While a session trains, run the
  CLI suite with the GPU hidden. Making that test pin CPU is a candidate
  fix.
- `test_ot11_judge.py` pinned `decisions == [ADR-454, ADR-463]`. It now
  pins the first two and requires that later decisions not concern the
  judge or the film marks.
- The off-contract `p1-w2-2-seeds.json` receipt was measured by
  `runner/measure.py` under the old reading. Its traces are not stored, so
  it was not re-read. The same policy's two on-contract evaluations were
  re-read.
- No new dependency.
- Unreconciled tail: 1 (this record).

Dispatch closed: 1 unit — W10 read after the 1.0 s settle (ADR-467, limit unchanged); w2-2 and walk rounds 1–5 re-read from stored traces with exact agreement, no verdict moved, w2-2 still fails W5/W7; r5-swing (walks forward, 0/10) evaluated on the new code with identical readings, its publication deferred

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 6ea2e66e23b9786bbe6a3371c172abf2fc79f1a7

## State Impact

- target: rough-shore-6557 — W10 now reads each foot's lowest height after the 1.0 s settle (ADR-467, commit 6ea2e66e), limit -0.05 hip heights unchanged; w2-2 (two evaluations) and walk rounds 1-5 re-read from stored traces with exact agreement on 70 seeds, no verdict moved, W10 still fails every seed, w2-2 still fails W5 and W7 on every seed
- target: smooth-fountain-9832 — walk round 5 r5-swing (session 2) walks forward: W3 9/10, W1/W2 10/10, but fails 10/10 on stepping (W5), slip (W7), W8-low, W9 and W10; publication pending; r6-trot training
