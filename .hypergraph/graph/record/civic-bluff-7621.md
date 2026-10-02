---
node_id: c5f15b33-9d2d-5924-9602-872f74bbb262
slug: civic-bluff-7621
title: 'ot11 R1: r16-alive10 published (row 28), valid no-margin walk evaluation, fails 0 of 10 in two measured modes; r17 live'
created_at: '2026-10-01T11:25:42+00:00'
parents:
- early-bramble-6327
summary: ''
---
## What

Published walk session 5's second round, `r16-alive10`, as run row 22 and evaluation row 28 of `docs/probes/ot11/REPORT.md`. The receipt is `retained/p5-quad-1-r16-evaluation.json`, plus the seed-1101 filmstrip (243 KB) and detail sheet (209 KB). It is **valid**, and it **fails 0 of 10**. A revision row for r16 (motivated by row 27, answered by row 28), a failure bullet and the W10 line under "Remaining defects" were added. `cli/tests` was re-run with the GPU hidden: 1271 passed, 1 skipped (commit `bc088ea5`).

## Why

R1 (`smooth-fountain-9832`) is the only open ot11 criterion a live session can move. The critic named this unit: when r16-alive10 finishes, publish it the way r15 was published, and if it splits between tipping and standing, record that diagnosis from measurements. r16 was still training when I started (about 1200 of its 2400 s budget gone), so I waited inside the iteration. Training ended at 07:01 local with all 760 iterations run. The agent's own `evaluate` tool wrote the evaluation at about 07:04, and I published that stored evaluation without re-running it. I started no GPU job and touched nothing under `src/Mod/cadex`. I did everything the critic asked.

## Method

- **Validity checks.**
  - `contact_offsets` is `[]` and no seed is void (ADR-470).
  - The evaluated revision `e84b045a` (0086) is byte-identical to 0085. 0085 differs from the registered `8ace1401` (0084) only in the policy line: walk_r15 → walk_r16, with its sha256 `dd0f9dc0`.
  - The model sha (`6cecfa2d`) equals the trainer receipt's. The task sha (`189840ee`) equals both the trainer receipt's and the registration's. The policy sha equals the supervisor's.
  - The script's spec block equals the frozen `walk-spec-block.txt` (sha `487416af`) except for HIP_MM 96.7006 and WEIGHT_N 5.05069617762, which equal the evaluation's rig.
- **Ledgers.** Regenerated with `runner/run_ledger.py` and `runner/eval_ledger.py` over the same project order as before: 22 runs, 21 attempts, 36,682.04 s supervised (walk 16, 31,334.06 s); 28 evaluations, 12 judge scores. No run was in progress when the ledgers were generated.
- **Diagnosis.** Per-seed measurements were read from the stored `evaluation.json`: duration, termination, tilt, speed_ratio, steps, duty and clearance for each foot, slip, W10, the shove time and the reward terms.
- **Test.** The counts in `cli/tests/test_ot11_report.py` were bumped: 22 runs and 21 attempts, 28 evaluations, 21 revision rows, 24 failed.

## Result

What is true now:
- **r16 fails every seed, in two measured modes, and it no longer stands still the way r15 did.**
  - *Lunge* (1101, 1102, 1104, 1106, 1108): speed_ratio 0.75–0.97. Each front foot takes one step and the rear-right never steps (duty 0.0–0.39). These tip at 1.76–2.50 s with tilt 37–42°, before their shove arrives (3.39–4.01 s).
  - *Three-legged stand* (1103, 1105, 1107, 1109, 1110): the rear-left foot is held 34–50 mm up (duty 0.05–0.25) and speed_ratio is 0.05–0.22. Three of these tip 0.32–0.61 s after their shove (1103, 1107, 1109). Two stand the full 10 s.
  - W5-steps reaches at most 1 on any seed (min 4). Slip is 0.26–0.74 and W8-low duty_min is 0.0–0.39. W3 passes on 4 seeds.
  - The reward does not explain the tipping: a surviving step now nets +4.4 to +5.4 (alive +10), compared with −1.16 to −1.21 on r15. Tips still come at 1.76–6.58 s, and more seeds tip (8 against r15's 5).
- **W10 holds on all ten seeds** (−0.010 to −0.002 HH). Every foot lifts and lands, but only once or twice a seed. A sustained stepping load is still measured only by r14's policy driven on the rebuilt model.
- **The loop is turning on its own.** The agent read row 28 and registered `r17-discount-bodyrate` at about 07:08 local: discount 0.995 and a roll/pitch-rate cost, fresh start, seed 163, 2400 s budget. Its reason cites row 28's W1/W2, W7, W5 and W8 measurements and the 100–140-step training episodes. r17 is training now (GPU pid 2781438), and it is the next unit to publish.
- **Suites.** `cli/tests`: 1271 passed / 1 skipped, run with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`. `test-engine` was not re-run because nothing under `src/Mod/cadex` changed.
- **Tail.** Since the last reconcile, this is the only unreconciled record.

Dispatch closed: 1 unit — r16-alive10 published as row 28, valid and failing 0 of 10 (five lunge-and-tip before the shove, five three-legged stands, three tipping after the shove); diagnosis recorded; cli/tests green on CPU while r17 trains.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: bc088ea582350fd1d0aab3bbba21cae3b5b486e4

## State Impact

- target: smooth-fountain-9832 — walk session 5 round 2 (r16-alive10, row 28) is valid (contact_offsets empty) and fails 0 of 10: five seeds lunge at speed_ratio 0.75-0.97 and tip at 1.76-2.50 s before the shove, five stand on three legs (rear-left held 34-50 mm up) and three of those tip after the shove; no foot steps more than twice; W10 holds on all ten (-0.010..-0.002 HH); the agent registered r17-discount-bodyrate from those measurements and it is training
- target: golden-bay-4173 — REPORT.md at 22 runs (21 attempts, 36,682.04 s) and 28 evaluations; cli/tests 1271 passed / 1 skipped at bc088ea5 (CPU-only)
