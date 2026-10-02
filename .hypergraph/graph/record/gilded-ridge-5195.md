---
node_id: bb27f45c-5bc8-59b9-bd85-7ea84f3bb87f
slug: gilded-ridge-5195
title: 'ot11 R1/P4 walk round 6 published: r6-trot 0/10, RL unchanged, rear pair now dragged; C1 REPORT.md run ledger started (12 runs, 17,963 s GPU)'
created_at: '2026-10-01T02:36:07+00:00'
parents:
- pale-ember-2389
summary: ''
---
## What

Published walk round 6 (`r6-trot`, session 2's second run) against the unchanged walk spec: 0 of 10 seeds. Also started C1's closing report: `docs/probes/ot11/REPORT.md` now holds a ledger of all twelve ot11 training runs with their settings, budget and GPU time. A collector (`runner/run_ledger.py`) builds the receipt `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, and `cli/tests/test_ot11_report.py` holds the page's table to that receipt row for row.

## Why

The critic named both: let r6-trot finish under its supervisor, evaluate it once, publish it the way round 5 was published, and check whether RL's step count and W9 moved. While it trained, start the C1 skeleton. r6 had finished at 02:11Z, before this iteration began. The product agent ran its single `evaluate` itself, through the loop, at 02:13Z. I did not run a second evaluation. I published the agent's own report. R1 is the highest open criterion, and P4's rounds count on it.

## Method

- Supervision: `rounds.py` (pid 1159861, setsid) and the product agent's turn kept running. I signalled nothing.
- r6 receipt `retained/p4-quad-1-r6-evaluation.json`, in round 5's schema:
  - registration, status and trainer receipt.
  - Checkpoint digests. Every `.cxpolicy` records trainer `97bc1d9a…`, which equals `training/cadex_train.py` at HEAD.
  - Per-seed predicates, feet, reward terms, shove times and trace digests.
  - A spec-block containment check against `retained/walk-spec-block.txt`: true.
  - The revision diff 0036→0039. It equals the registered change and nothing else.
- Copied the evaluation's own dark-floor filmstrips for seed 1101 (148 KB and 247 KB).
- README section "Walk round 6", with a predicate table against round 5, a per-foot table, the answer to round 5's open question, and the agent's diagnosis quoted from its transcript.
- Run ledger: collector run over ot11-robin-1, ot11-heron-1 and ot11-quad-1 gives 12 runs and 17,963.36 s supervised. No machine path appears in the receipt; `init_from` is made project-relative.
- Tests:
  - The new test fails when one number on the page changes (checked by mutating 2,157.29 to 2,157.30).
  - The ot11 tests pass (72).
  - The full `cli/tests` run result is in Result.

## Result

**Round 6 fails 0 of 10.** The policy is `0eaef24f…`, iteration 760 of 760, 2,157 s GPU (2,004 s in the trainer), warm-started from r5. Its report is `evaluations/abebe8381134-0eaef24f7f32/evaluation.json`.

- **The critic's question: RL did not move.** RL takes 2–6 steps (round 5: 1–6).
- **W9 did not improve.** It reads 6.3–39 on eight seeds and is not measured on 1107 and 1108, where RR takes 0 steps (round 5: 5.7–33).
- **The pairing moved instead.** FR rose from 4–14 steps to 15–28, and RR fell from 10–18 to 0–7. The gait is now both front feet stepping and both rear feet dragged.
- **W7 slip fell from 0.46–0.53 to 0.28–0.32**, still about twice the 0.15 limit.
- **`trot_sync` changed little.** Its weight was more than tripled (−0.3 to −1.0), but the raw diagonal mismatch fell only about 10% (mean 257 to 232 per episode).
- W3 fails 1 seed (1101, 1.35). W6 fails 2 seeds. W8-low, W9, W10, W5-share and W7 fail all 10.
- **The agent's diagnosis matches the measurement this time.** It reads FL as held aloft (duty 0.23–0.27) and the hind feet as sliding. It registered `r7-relswing`: swing pay on foot speed relative to the body, a hover cost, grounded slip 2.0. The run uses seed 67, 760 iterations and 2,400 s, warm-started from r6.
- **r7 is the seventh and last run** that `p4-quad-1-s2-preregistration.json` allows. It was training on the GPU when this iteration ended, under its own supervisor. The next iteration should publish r7's evaluation the same way and then close walk session 2.
- **REPORT.md now has a run ledger and nothing else yet.** Balance used 900.57 s, reach 4,447.41 s and walk 12,615.38 s. When r7 ends, re-run `run_ledger.py` and add its row; the test will fail until the page matches.
- **One inconsistency is noted on the page.** Round 5's README section quotes 1,898 s, which is trainer time. Every other section quotes supervised time, and the ledger uses supervised time throughout.
- **Tests.** `cli/tests` has one failure, `test_walk.py::test_the_same_walk_handles_a_linear_carriage`. The cause is `jaxlib XlaRuntimeError: INTERNAL: cuSolver internal error`: the test trains on the GPU while r7-relswing holds about 24.7 GB of it. It fails the same way when run alone. This change touches no code it runs (docs, receipts, a probe script and a new test only). The full run stopped at that failure under `-x` with 1213 passed and 1 skipped. Re-running test_walk onward gave 89 passed and the same 1 failure. **Next iteration: re-run that test once the GPU is free, after r7 ends. If it still fails, it is a real break and must be named broken.** I did not run `pixi run test-engine`, because no engine source changed.
- **New dependency:** none.
- **Tail:** two records are now past the high-water mark (pale-ember-2389 and this one). The critic asked for a reconcile after r6 is published.

Dispatch closed: 1 unit — walk round 6 published (0/10; RL unchanged, rear pair now dragged, W9 no better) and REPORT.md's test-pinned run ledger started

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: c9339f2247b31ed2a0ed1216ecc8eb72ded3788d

## State Impact

- target: smooth-fountain-9832 — walk round 6 (r6-trot, warm start from r5, reward weights only) fails 0/10: RL 2-6 steps (was 1-6), RR 0-7 (was 10-18), W9 6.3-39 / unmeasured on 2 seeds, W7 0.28-0.32; agent registered r7-relswing, the 7th and last run session 2 allows
- target: golden-bay-4173 — REPORT.md exists with every ot11 training run (12 runs, settings, budget, 17,963.36 s supervised GPU), test-pinned to retained/ot11-runs.json built by runner/run_ledger.py; evaluations, judge scores, revisions and defects sections not yet written
