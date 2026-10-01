# ot11 closing report

Verified against source: 2026-10-01. `[Cadex-new]`

This is C1's report for run ot11 (charter: `.ouroboros/goal.md`). It is
written while the run continues, one section at a time, and each section is
held to a receipt under [`retained/`](retained/) by
`cli/tests/test_ot11_report.py`. The evidence behind every claim, and the
contract the evaluations are read against, is in [`README.md`](README.md).
The owner ticks the criteria; this page does not.

## Every criterion and its receipt

One line per done criterion of the charter, each with the evidence it
rests on. Every link is checked by `cli/tests/test_ot11_report.py`. This
is a claim of evidence for critic review, not a tick.

| criterion | evidence | receipts |
|---|---|---|
| P1 | The contract for walk, reach and balance was frozen in [`README.md`](README.md) before any ot11 run (ADR-454), with ten seeds each, the pass rule, the blind judge and its bar. `w2-2` fails the walk spec on stepping and slip, and Robin fails the balance spec on drift and heading; the judge's blind spot on slip is a recorded limit (ADR-463). | [`contract.json`](contract.json), [`retained/p1-w2-2.json`](retained/p1-w2-2.json), [`retained/p1-robin.json`](retained/p1-robin.json), [`retained/judge-w2-2-seed-1101.json`](retained/judge-w2-2-seed-1101.json), [`retained/judge-robin-seed-1101.json`](retained/judge-robin-seed-1101.json) |
| P2 | The spec is declared in xscript beside the task (ADR-456); `cadex evaluate` writes the per-seed, per-predicate report with reward terms, terminations, the three metric families and the film (ADR-457, ADR-459); the dashboard shows it. The metrics are pinned on passing and failing fixtures in `test_evaluation_metrics.py`, where `w2-2` is a failing one, and the command in `cli/tests/test_evaluate.py`. | [`retained/p2-w2-2-evaluation.json`](retained/p2-w2-2-evaluation.json), [`retained/p2-robin-evaluation.json`](retained/p2-robin-evaluation.json) |
| P3 | `assembly.goal` draws a goal per episode by one algorithm the engine and the trainer both run, the policy observes it and the trace records it (ADR-462); `test_dynamics_goal_trainer.py` fails if they drift. R2 trained on it, over held-out targets. | [`retained/r2-heron-1-targets.json`](retained/r2-heron-1-targets.json) |
| P4 | The product agent runs one loop for every behaviour through four bridge tools and a detached supervisor; `cadex walk` stays as one scripted use (ADR-464). Reach ran five rounds and walk twenty-four, each revision citing the previous evaluation (*Every revision*, below). | [`retained/p4-heron-1-rounds.json`](retained/p4-heron-1-rounds.json), [`retained/p4-quad-1-rounds.json`](retained/p4-quad-1-rounds.json), [`retained/p4-robin-1-rounds.json`](retained/p4-robin-1-rounds.json) |
| R1 | Confirmation 1, registered at `5841202e`: 10 of 10 on the frozen walk spec, on a model reopened through `cadex export` with no contact margin or gap, and the judge's bar met on 1101, 1105 and 1110 (10, 11, 12). Evaluation row 36. | [`retained/r1-confirm-1-registration.json`](retained/r1-confirm-1-registration.json), [`retained/r1-confirm-1-evaluation.json`](retained/r1-confirm-1-evaluation.json), [`retained/judge-r1-confirm-1-seed-1101.json`](retained/judge-r1-confirm-1-seed-1101.json) |
| R2 | Confirmation 1: 10 of 10 on the frozen reach spec over targets drawn before any training, and the judge's bar met on every judged seed (12, 12, 12). Evaluation row 12. | [`retained/r2-confirm-1-registration.json`](retained/r2-confirm-1-registration.json), [`retained/r2-confirm-1-evaluation.json`](retained/r2-confirm-1-evaluation.json), [`retained/judge-r2-confirm-1-seed-1101.json`](retained/judge-r2-confirm-1-seed-1101.json) |
| R3 | Confirmation 1: 10 of 10 on the frozen balance spec, shoves included, and the judge's bar met on every judged seed (12, 12, 11). Evaluation row 6. | [`retained/r3-confirm-1-registration.json`](retained/r3-confirm-1-registration.json), [`retained/r3-confirm-1-evaluation.json`](retained/r3-confirm-1-evaluation.json), [`retained/judge-r3-confirm-1-seed-1101.json`](retained/judge-r3-confirm-1-seed-1101.json) |
| C1 | This page. At the confirmation revision (`4d2baa7d`) on 2026-10-01: `pixi run test-engine` 2529 passed, 61 skipped; `cli/tests`, CPU-only, 1288 passed, 1 skipped (the review server's private-network check, which needs `CADEX_REVIEW_HOST`). The packaged lifecycle gate last ran after ADR-470, the last engine change, and passed 23 of 23; no engine source has changed since (*Remaining defects*). | [`retained/ot11-runs.json`](retained/ot11-runs.json), [`retained/ot11-evaluations.json`](retained/ot11-evaluations.json) |

## Every training run

Thirty-one runs have ended in ot11, twenty-nine attempts and two refused starts
(`r9-steelfoot`, row 15, and `r21-r19-continue`, row 27: each trainer exited
before its first iteration).
All went through the product's `train_start` tool, one GPU job at a time,
with `--stop-on-collapse` on. Every one was registered before it launched: its settings, its seed, its
wall-clock budget and its reason are in its project's
`runs/<run>/registration.json`. How each ended is in the run's
`training-status.json`, written by its supervisor.
[`runner/run_ledger.py`](runner/run_ledger.py) reads those two files and
nothing else. Its receipt is
[`retained/ot11-runs.json`](retained/ot11-runs.json), and the table below
is that receipt.

| # | behaviour | project | run | seed | settings | warm start | budget, s | ended | iterations run | GPU time, s | trainer's own time, s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | balance | `ot11-robin-1` | `bal-1` | 7 | 650 it × 1024 envs | — | 900 | `budget_exhausted` | 399 | 900.57 | — |
| 2 | reach | `ot11-heron-1` | `reach-r1` | 7 | 700 it × 1024 envs | — | 880 | `budget_exhausted` | 685 | 880.45 | — |
| 3 | reach | `ot11-heron-1` | `reach-r2` | 11 | 800 it × 1024 envs | — | 890 | `budget_exhausted` | 649 | 890.51 | — |
| 4 | reach | `ot11-heron-1` | `reach-r3` | 23 | 800 it × 1024 envs | — | 890 | `budget_exhausted` | 649 | 890.46 | — |
| 5 | reach | `ot11-heron-1` | `reach-r4` | 31 | 800 it × 1024 envs | — | 895 | `budget_exhausted` | 474 | 895.49 | — |
| 6 | reach | `ot11-heron-1` | `reach-r5` | 41 | 800 it × 1024 envs | `reach-r4` | 890 | `budget_exhausted` | 422 | 890.50 | — |
| 7 | walk | `ot11-quad-1` | `r1-clearance` | 7 | 1000 it × 2048 envs | — | 2,350 | `collapsed` | 569 | 1,542.42 | — |
| 8 | walk | `ot11-quad-1` | `r2-bounded` | 11 | 800 it × 2048 envs | — | 2,380 | `finished` | 800 | 2,251.49 | 2,103.3 |
| 9 | walk | `ot11-quad-1` | `r3-nochatter` | 23 | 800 it × 2048 envs | — | 2,380 | `budget_exhausted` | 800 | 2,381.11 | — |
| 10 | walk | `ot11-quad-1` | `r4-anglesonly` | 31 | 780 it × 2048 envs | — | 2,390 | `finished` | 780 | 2,183.25 | 2,032.9 |
| 11 | walk | `ot11-quad-1` | `r5-swing` | 41 | 780 it × 2048 envs | — | 2,400 | `finished` | 780 | 2,099.82 | 1,897.6 |
| 12 | walk | `ot11-quad-1` | `r6-trot` | 53 | 760 it × 2048 envs | `r5-swing` | 2,400 | `finished` | 760 | 2,157.29 | 2,004.1 |
| 13 | walk | `ot11-quad-1` | `r7-relswing` | 67 | 760 it × 2048 envs | `r6-trot` | 2,400 | `collapsed` | 538 | 1,720.84 | — |
| 14 | walk | `ot11-quad-1` | `r8-stance` | 71 | 800 it × 2048 envs | — | 2,400 | `finished` | 800 | 2,008.15 | 1,858.5 |
| 15 | walk | `ot11-quad-1` | `r9-steelfoot` | 83 | 800 it × 2048 envs | `r6-trot` | 2,400 | `failed` | 0 | 52.03 | — |
| 16 | walk | `ot11-quad-1` | `r10-steelfoot-fresh` | 97 | 800 it × 2048 envs | — | 2,400 | `finished` | 800 | 2,209.67 | 2,060.4 |
| 17 | walk | `ot11-quad-1` | `r11-speedpay` | 109 | 760 it × 2048 envs | `r10-steelfoot-fresh` | 2,400 | `finished` | 760 | 2,014.44 | 1,862.9 |
| 18 | walk | `ot11-quad-1` | `r12-convex-sym` | 131 | 800 it × 2048 envs | — | 2,400 | `finished` | 800 | 2,105.98 | 1,954.1 |
| 19 | walk | `ot11-quad-1` | `r13-hovercost-margin` | 137 | 800 it × 2048 envs | — | 2,400 | `finished` | 800 | 2,239.22 | 2,089.7 |
| 20 | walk | `ot11-quad-1` | `r14-margin15-lift` | 139 | 800 it × 2048 envs | — | 2,400 | `finished` | 800 | 2,348.43 | 2,178.3 |
| 21 | walk | `ot11-quad-1` | `r15-stiffspring-clearfoot` | 151 | 760 it × 2048 envs | — | 2,400 | `finished` | 760 | 1,926.40 | 1,777.4 |
| 22 | walk | `ot11-quad-1` | `r16-alive10` | 157 | 760 it × 2048 envs | — | 2,400 | `finished` | 760 | 2,093.52 | 1,941.9 |
| 23 | walk | `ot11-quad-1` | `r17-discount-bodyrate` | 163 | 760 it × 2048 envs | — | 2,400 | `finished` | 760 | 2,061.01 | 1,910.6 |
| 24 | walk | `ot11-quad-1` | `r18-sync-slip` | 181 | 600 it × 2048 envs | `r17-discount-bodyrate` | 2,350 | `finished` | 600 | 1,582.47 | 1,434.6 |
| 25 | walk | `ot11-quad-1` | `r19-contact-sync` | 191 | 750 it × 2048 envs | `r18-sync-slip` | 2,350 | `finished` | 750 | 2,010.27 | 1,861.1 |
| 26 | walk | `ot11-quad-1` | `r20-contact35` | 201 | 700 it × 2048 envs | `r19-contact-sync` | 2,350 | `finished` | 700 | 1,913.86 | 1,765.7 |
| 27 | walk | `ot11-quad-1` | `r21-r19-continue` | 211 | 750 it × 2048 envs | `r19-contact-sync` | 2,350 | `failed` | 0 | 52.28 | — |
| 28 | walk | `ot11-quad-1` | `r21b-r19-continue` | 211 | 750 it × 2048 envs | `r19-contact-sync` | 2,350 | `finished` | 750 | 2,068.98 | 1,964.1 |
| 29 | walk | `ot11-quad-1` | `r22-gentle-contact25` | 221 | 750 it × 2048 envs | `r19-contact-sync` | 2,350 | `finished` | 750 | 1,727.12 | 1,622.5 |
| 30 | walk | `ot11-quad-1` | `r23-r19-clip05` | 231 | 1200 it × 2048 envs | `r19-contact-sync` | 3,500 | `stopped` | 87 | 261.25 | — |
| 31 | walk | `ot11-quad-1` | `r24-r19-vw005` | 241 | 1200 it × 2048 envs | `r19-contact-sync` | 3,500 | `budget_exhausted` | 924 | 3,501.24 | — |

| behaviour | runs | GPU time, s |
|---|---|---|
| balance | 1 | 900.57 |
| reach | 5 | 4,447.41 |
| walk | 25 | 46,512.54 |
| **all** | **31** | **51,860.52** |

**How to read the two times.** *GPU time* is the supervisor's wall time
from launch to exit; the trainer holds the GPU for all of it, so it is the
time the charter counts, and it exists for every run. *The trainer's own
time* is the figure in the trainer's receipt, which a trainer writes only
when it saves its final policy. A run stopped at its wall-clock budget or on
collapse has none. The difference, 105 to 202 s on the eighteen walk runs that
have both, is time the supervisor measured outside the trainer's own clock.

**Earlier figures on the README.** Rounds 1–4 of the walk, and every reach
and balance round, quote the GPU time above. Round 5's section quotes
1,898 s, which is its trainer's own time; its GPU time is 2,099.82 s.

**What the table leaves out.** Settings not shown are in the receipt:
`checkpoint_every`, the network size where the agent set it, and
`entropy`, which reach rounds 3–5 set to 0. A warm start names the run whose
policy it began from; `reach-r5` began from `reach-r4`'s iteration-475
checkpoint and `r6-trot` from `r5-swing`'s final policy, and `r7-relswing` from
`r6-trot`'s, and `r11-speedpay` from `r10-steelfoot-fresh`'s, and `r18-sync-slip` from
`r17-discount-bodyrate`'s, and `r19-contact-sync` from `r18-sync-slip`'s, and
`r20-contact35`, `r21b-r19-continue`, `r22-gentle-contact25`, `r23-r19-clip05` and `r24-r19-vw005` from `r19-contact-sync`'s. `r23-r19-clip05` also set the PPO clip to 0.05, and `r24-r19-vw005` the value-loss weight to 0.05. Robin's ot9
baseline (`r3-ppo-1`) and ot10's `w2-2` are earlier runs measured as known
negatives (P1), not ot11 training runs, and are not in this table.

**What the table leaves out, continued.** `r9-steelfoot` and
`r21-r19-continue` are in the table and in the totals because their
supervisors ran for 52.03 s and 52.28 s, but neither is an attempt
(`attempt: false` in the receipt): each trained nothing. A run still
training has no end time yet, so the receipt lists it under `in_progress`
and in no total. No run was in progress when this was last regenerated.

## Every evaluation

Thirty-six evaluations are stored across the five ot11 projects, every one
written by `cadex evaluate` or the agent's `evaluate` tool (the same code)
into the project's `evaluations/<key>/evaluation.json`.
[`runner/eval_ledger.py`](runner/eval_ledger.py) reads those files, and the
judge receipts below, and nothing else. Its receipt is
[`retained/ot11-evaluations.json`](retained/ot11-evaluations.json), and the
table is that receipt. *Policy* names the run and the file that trained the
evaluated weights, found by hashing every policy file under a registered
run; the two known negatives were trained before ot11 and are named by
their origin. *Predicates failed* counts the failing seeds for each
predicate that did not pass on all of them.

**Every row is checked against the frozen contract** (ADR-472). The
receipt's `contract_deviations` is what
[`runner/conformance.py`](runner/conformance.py) finds when it compares
the spec each evaluation resolved (seeds, episode length, every predicate's
id, metric and bound, the reset tilt and lift, each shove's force in body
weights, its window, direction and duration, and the goal) with
[`contract.json`](contract.json). Thirty-two of the 36 conform. Two kinds of
deviation exist, and both were already recorded by hand. In rows 1 and 2,
ot10's `w2-2` is read without W3 and the lateral half of W4, because its
task has no commanded speed to track (*README*, P1). In rows 20 and 21,
`r8-stance` drew its command from 0.599999–0.999998 hip heights, from the
script's `HIP_MM = 106.9488` against a measured 106.949: the stale digit
that made both void under the session's mechanism rule and led to ADR-468.

| # | behaviour | project | evaluation | policy | verdict | seeds passed | predicates failed (failing seeds) | terminations | film |
|---|---|---|---|---|---|---|---|---|---|
| 1 | walk | `ot11-w2-negative` | `60f655537c0b-7a4e8c233214` | ot10 `w2-2` | fail | 0 of 10 | W1 2, W2 9, W4-heading 1, W5-steps 7, W5-share 10, W6 10, W7 10, W8-low 7, W8-high 4, W9 10, W10 10 | horizon 8, tipped 2 | — |
| 2 | walk | `ot11-w2-negative` | `064d8d7cd34c-7a4e8c233214` | ot10 `w2-2` | fail | 0 of 10 | W1 2, W2 8, W4-heading 1, W5-steps 10, W5-share 10, W6 4, W7 10, W8-low 1, W8-high 1, W9 10, W10 10 | horizon 8, tipped 2 | yes |
| 3 | balance | `ot11-robin-negative` | `b2302f600801-ef71f370a2f1` | ot9 `r3-ppo-1` | fail | 0 of 10 | B1 6, B2 6, B3 10, B4 10, B5 10 | fallen 6, horizon 4 | — |
| 4 | balance | `ot11-robin-negative` | `3a42fdec8b94-ef71f370a2f1` | ot9 `r3-ppo-1` | fail | 0 of 10 | B1 6, B2 6, B3 10, B4 10, B5 10 | fallen 6, horizon 4 | yes |
| 5 | balance | `ot11-robin-1` | `cbf14e3c6865-8919a22dae1f` | `bal-1 it 400` | pass | 10 of 10 | — | horizon 10 | yes |
| 6 | balance | `ot11-robin-1` | `r3-confirm-1` | `bal-1 it 400` | pass | 10 of 10 | — | horizon 10 | yes |
| 7 | reach | `ot11-heron-1` | `42ff7b8e1099-c5a01908a054` | `reach-r1 best` | fail | 0 of 10 | Q2 10, Q3 10, Q4 7 | horizon 10 | yes |
| 8 | reach | `ot11-heron-1` | `0ce61b45859b-e1b0277de9db` | `reach-r2 best` | fail | 1 of 10 | Q2 9, Q3 9, Q4 1 | horizon 10 | yes |
| 9 | reach | `ot11-heron-1` | `a9d8520c81c9-2036f471cc3b` | `reach-r3 best` | fail | 0 of 10 | Q2 10, Q3 10, Q4 2 | horizon 10 | yes |
| 10 | reach | `ot11-heron-1` | `6418a337500a-3270ce260233` | `reach-r4 it 475` | fail | 9 of 10 | Q2 1, Q3 1 | horizon 10 | yes |
| 11 | reach | `ot11-heron-1` | `13f9c63c93c9-6bb5a403c4af` | `reach-r5 it 400` | pass | 10 of 10 | — | horizon 10 | yes |
| 12 | reach | `ot11-heron-1` | `r2-confirm-1` | `reach-r5 it 400` | pass | 10 of 10 | — | horizon 10 | yes |
| 13 | walk | `ot11-quad-1` | `8498db6e1ff5-8db0cb619fc4` | `r1-clearance best` | fail | 0 of 10 | W1 4, W2 4, W3 10, W4-lateral 5, W4-heading 8, W5-steps 5, W5-share 10, W6 10, W7 10, W8-low 3, W8-high 2, W9 8, W10 10 | horizon 6, tipped 4 | yes |
| 14 | walk | `ot11-quad-1` | `80ba9fb9905e-1a0f0d28a2aa` | `r2-bounded final` | fail | 0 of 10 | W3 10, W4-lateral 1, W4-heading 5, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W9 10, W10 10 | horizon 10 | yes |
| 15 | walk | `ot11-quad-1` | `9f711fcaa419-102133e9310b` | `r3-nochatter best` | fail | 0 of 10 | W1 1, W3 10, W4-lateral 1, W4-heading 5, W5-steps 7, W5-share 10, W6 9, W7 10, W8-low 10, W9 10, W10 10 | collapsed 1, horizon 9 | yes |
| 16 | walk | `ot11-quad-1` | `ce8d19639f13-d2dcaf39ba21` | `r4-anglesonly final` | fail | 0 of 10 | W1 1, W2 1, W3 10, W5-steps 10, W5-share 10, W6 10, W7 10, W8-high 10, W9 10, W10 10 | horizon 9, tipped 1 | yes |
| 17 | walk | `ot11-quad-1` | `dee2391353b7-6a7c89de9ade` | `r5-swing final` | fail | 0 of 10 | W3 1, W4-lateral 1, W5-steps 9, W5-share 10, W6 2, W7 10, W8-low 10, W9 10, W10 10 | horizon 10 | yes |
| 18 | walk | `ot11-quad-1` | `abebe8381134-0eaef24f7f32` | `r6-trot final` | fail | 0 of 10 | W3 1, W5-steps 8, W5-share 10, W6 2, W7 10, W8-low 10, W9 10, W10 10 | horizon 10 | yes |
| 19 | walk | `ot11-quad-1` | `d35b9080ec77-71128e61c033` | `r7-relswing it 200` | fail | 0 of 10 | W1 6, W3 3, W4-lateral 2, W5-steps 4, W5-share 10, W6 2, W7 9, W8-low 10, W8-high 2, W9 10, W10 10 | collapsed 6, horizon 4 | yes |
| 20 | walk | `ot11-quad-1` | `2029ad2130b6-96ff3b792f7a` | `r8-stance it 300` | fail | 0 of 10 | W1 4, W2 7, W3 10, W4-lateral 8, W4-heading 7, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 8, W9 10, W10 10 | horizon 6, tipped 4 | yes |
| 21 | walk | `ot11-quad-1` | `a0460e13b112-749e0bcedb8e` | `r8-stance final` | fail | 0 of 10 | W1 2, W2 6, W3 10, W4-lateral 8, W4-heading 7, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 10, W9 10, W10 10 | horizon 8, tipped 2 | yes |
| 22 | walk | `ot11-quad-1` | `2cb0f0e5d80e-34f47b033235` | `r10-steelfoot-fresh final` | fail | 0 of 10 | W3 10, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 10, W9 10 | horizon 10 | yes |
| 23 | walk | `ot11-quad-1` | `bfb59bb5d902-f35fefd6a569` | `r11-speedpay final` | fail | 0 of 10 | W3 10, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 10, W9 10 | horizon 10 | yes |
| 24 | walk | `ot11-quad-1` | `ca8310e9d841-3179aa38a75d` | `r12-convex-sym final` | fail | 0 of 10 | W3 5, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 10, W9 10, W10 10 | horizon 10 | yes |
| 25 | walk | `ot11-quad-1` | `0bbe95889512-70b9ac55c145` | `r13-hovercost-margin final` | fail | 0 of 10 | W3 10, W5-share 1, W6 10, W7 9, W8-low 10, W9 3 | horizon 10 | yes |
| 26 | walk | `ot11-quad-1` | `6688a28a61d8-5f97b60219ba` | `r14-margin15-lift final` | fail | 0 of 10 | W5-share 7, W6 10, W7 2, W8-low 10, W10 9 | horizon 10 | yes |
| 27 | walk | `ot11-quad-1` | `bf664d9bfc69-d430a9224345` | `r15-stiffspring-clearfoot final` | fail | 0 of 10 | W1 5, W2 5, W3 10, W4-lateral 5, W5-steps 10, W5-share 10, W6 10, W7 10, W8-low 10, W8-high 10, W9 10, W10 5 | horizon 5, tipped 5 | yes |
| 28 | walk | `ot11-quad-1` | `e84b045a4528-dd0f9dc053a7` | `r16-alive10 final` | fail | 0 of 10 | W1 8, W2 8, W3 6, W4-lateral 3, W5-steps 10, W5-share 10, W6 9, W7 10, W8-low 10, W8-high 10, W9 8 | horizon 2, tipped 8 | yes |
| 29 | walk | `ot11-quad-1` | `50b2a42caf1c-63cbf22407c0` | `r17-discount-bodyrate final` | fail | 1 of 10 | W5-share 2, W7 8, W9 8 | horizon 10 | yes |
| 30 | walk | `ot11-quad-1` | `f0851df103a5-0ef672db5077` | `r18-sync-slip final` | fail | 2 of 10 | W1 1, W2 1, W5-steps 1, W5-share 1, W9 8 | horizon 9, tipped 1 | yes |
| 31 | walk | `ot11-quad-1` | `35122157a90f-de546ddd91e1` | `r19-contact-sync final` | fail | 9 of 10 | W9 1 | horizon 10 | yes |
| 32 | walk | `ot11-quad-1` | `f924ce70604e-4a341e7b3047` | `r20-contact35 final` | fail | 0 of 10 | W5-share 3, W7 10, W8-low 1, W9 1 | horizon 10 | yes |
| 33 | walk | `ot11-quad-1` | `a11861cc1e14-8c94fcd21f0e` | `r21b-r19-continue final` | fail | 2 of 10 | W5-share 2, W7 8, W8-low 1, W9 1 | horizon 10 | yes |
| 34 | walk | `ot11-quad-1` | `da95bfa94936-e91a397134ac` | `r22-gentle-contact25 final` | fail | 6 of 10 | W2 1, W7 2, W8-low 2, W9 1 | horizon 10 | yes |
| 35 | walk | `ot11-quad-1` | `7df101b06548-5aaf21e70e63` | `r24-r19-vw005 it 900` | pass | 10 of 10 | — | horizon 10 | yes |
| 36 | walk | `ot11-quad-1` | `r1-confirm-1` | `r24-r19-vw005 it 900` | pass | 10 of 10 | — | horizon 10 | yes |

**How to read it.**
- **Rows 1–4 are P1's known negatives**, read before any ot11 training
  run. Rows 1 and 3 are the first product readings (ADR-457); row 1 kept
  the w2 task's mass draw, and is superseded by row 2 (ADR-458). Robin's
  task never randomised, so rows 3 and 4 agree number for number. Rows 2
  and 4 are P2's evaluations, the first with a film.
- **Rows 6 and 12 are R3's and R2's confirmation evaluations**, each
  pre-registered before it ran (`retained/r3-confirm-1-registration.json`,
  `retained/r2-confirm-1-registration.json`). Both pass on all ten seeds.
  Rows 5 and 11 are the loop rounds that earned them, on the same policy.
- **Rows 20 and 21 are void** under session 3's pre-registered mechanism
  rule: the task's `HIP_MM` was 106.9488 against the rig's 106.949(0) at
  four decimals (`retained/p4-quad-1-r8-evaluation.json`, `spec_block`).
  The engine scored them, and they fail on every seed regardless. ADR-468
  now refuses such a spec when it is declared.
- **Walk rows 1–2 and 13–28 pass no seed; rows 35 and 36 pass all ten.** Every
  walk row reads on W10's ADR-467 code, after the settle; the earlier rows
  were re-read when that decision was taken. The first seeds to pass came
  in rows 29–34 (1, 2, 9, 0, 2 and 6 of 10), and none of those passed the
  rule. Row 35 is the agent's own evaluation of `r24-r19-vw005` at
  iteration 900, and passes 10 of 10. Row 36 is R1's pre-registered
  confirmation of that policy, reopened through `cadex export`, and passes
  10 of 10 with no contact offset on the model
  ([`retained/r1-confirm-1-evaluation.json`](retained/r1-confirm-1-evaluation.json)).
- **Row 22 is valid.** Its spec block's `HIP_MM` and `WEIGHT_N` equal the rig's to the block's
  printed precision (`retained/p4-quad-1-r10-evaluation.json`,
  `spec_block`). It passes W10 on every seed, the first walk policy to do
  so, and it stands still on three feet.
- **Row 23 is valid** on the same checks
  (`retained/p4-quad-1-r11-evaluation.json`, `spec_block`). It keeps W10 on
  every seed and still takes no step: it rocks its body fore and aft in
  place on three feet, which the doubled speed pay rewards.
- **Row 25 is void for R1.** Its model carries a 3 mm contact `margin` on
  each foot, and the owner's clause of 2026-10-01 (charter R1) makes any
  policy evaluated on a model with a margin, a gap or any other setting
  that holds geometry off the floor void for R1, whatever it reads. The
  engine scored it, and it fails 0 of 10 regardless.
- **Row 26 is void, and the product voided it** (ADR-470): its model
  carries a 1.5 mm margin on each foot, and `cadex evaluate` marked all ten
  seeds void and named the four geoms in `contact_offsets`
  ([`retained/p4-quad-1-r14-evaluation.json`](retained/p4-quad-1-r14-evaluation.json)).
  It fails 0 of 10 regardless. It ran on the physics `r14-margin15-lift`
  trained on: a payload staged from ADR-470's commit with only ADR-469's
  0.004 s spring reverted, so the evaluated task digests to the trained
  one. Session 4's agent could not declare this policy at all, because the
  engine moved to ADR-469 under its last turn and the task digest moved
  with it. Its spec block is valid under the session's mechanism rule.
- **Row 27 is the first walk evaluation on a model with no contact
  offset and the ADR-469 spring, and it is valid** (`contact_offsets` is
  empty, nothing void;
  [`retained/p5-quad-1-r15-evaluation.json`](retained/p5-quad-1-r15-evaluation.json)).
  The agent's own `evaluate` call wrote it inside walk session 5's turn.
  Its revision differs from the registered one only in the policy line,
  its model and task hash to the trained ones, and its spec block differs
  from the frozen one only in HIP_MM and WEIGHT_N, which equal the rig.
  It fails 0 of 10, and badly: five seeds tip in 0.50–0.94 s (W1, W2), and
  the other five stand for the full 10 s without one step on any foot
  (W5-steps 0, duty 1.0, speed_ratio 0.03–0.06).
- **Row 28 is session 5's second round, and it is valid on the same
  checks** (`contact_offsets` empty;
  [`retained/p5-quad-1-r16-evaluation.json`](retained/p5-quad-1-r16-evaluation.json)).
  It fails 0 of 10 in two modes. Five seeds (1101, 1102, 1104, 1106,
  1108) lunge forward at speed_ratio 0.75–0.97 on one step per front
  foot, the rear-right never stepping, and tip at 1.76–2.50 s, before
  their shove (3.39–4.01 s). The other five hold the rear-left foot
  34–50 mm up (duty 0.05–0.25) at speed_ratio 0.05–0.22. Three of those
  tip 0.32–0.61 s after their shove, and two stand the 10 s.
- **Row 29 is session 5's third and last round, and it is valid on the
  same checks** (`contact_offsets` empty;
  [`retained/p5-quad-1-r17-evaluation.json`](retained/p5-quad-1-r17-evaluation.json)).
  It is the first walk evaluation to pass a seed: 1108 passes every
  predicate, and the other nine fail. No seed tips: all ten run the 10 s
  and stand through their shove (3.39–6.53 s), at tilt 12.4–17.2° and
  speed_ratio 0.90–0.98. Every foot steps 5–14 times (W5-steps passes on
  all ten), clearance is 0.15–0.22 HH and duty 0.48–0.61. What fails is
  slip (W7 0.154–0.208 on eight seeds, against 0.15) and leg balance:
  the rear feet take 10–14 steps to the front feet's 5–11 (W9 1.4–2.4 on
  eight seeds, against 1.5), and on 1101 and 1109 the front feet's step
  share falls to 0.69 and 0.57 (W5-share, against 0.70).
- **Row 30 is session 6's first round, and it is valid on the same
  checks** (`contact_offsets` empty, the model hashes to r17's, and the
  spec block differs from the frozen one only in WEIGHT_N, which equals
  the rig;
  [`retained/p6-quad-1-r18-evaluation.json`](retained/p6-quad-1-r18-evaluation.json)).
  Seeds 1102 and 1108 pass every predicate. Slip is fixed: W7 passes on
  all ten (0.096–0.146, against 0.15, from 0.154–0.208 on eight). What
  fails is still leg balance: the rear feet out-step the front on eight
  seeds (W9 1.56–2.33, against 1.5). Seed 1107 also tips at 5.90 s,
  0.61 s after the largest shove of the ten (0.97 N at 5.29 s), with three
  steps on one foot (W1, W2, W5). The other nine run the 10 s, at tilt
  11.7–15.4° and speed_ratio 0.92–0.97, clearance 0.25–0.27 HH and duty
  0.47–0.59. W10 holds on all ten (−0.023 to −0.014 HH).
- **Row 31 is session 6's second and last round, valid on the same
  checks** (`contact_offsets` empty, the model hashes to r17's and r18's,
  the task to the one trained, and the spec block is byte-identical to
  row 30's;
  [`retained/p6-quad-1-r19-evaluation.json`](retained/p6-quad-1-r19-evaluation.json)).
  Nine seeds pass every predicate, and no seed tips. Seed 1109 fails W9
  alone, at 1.571 against 1.5: its front feet step 7 and 8 times and its
  rear-left 11. W9 follows the commanded speed. 1109's command is the
  lowest of the ten (0.628 HH/s), and 1101's, the next lowest (0.647),
  gives the next highest ratio (1.333). The other eight sit at 1.18–1.30.
  At 1109's command the front feet swing for 0.57–0.60 s, while
  rear-left keeps its 0.36 s swing. 1109's shove is the smallest of the
  ten (0.31 N), so it does not explain the failure. On all ten: slip
  0.090–0.125, tilt 7.9–22.9°, speed_ratio 0.93–1.00, clearance 0.28–0.32
  HH, duty 0.45–0.59, W10 −0.022 to −0.013 HH. Walk session 7's agent
  re-evaluated r19 before it trained, under the same key, and the file was
  rewritten with every number unchanged: only `written_at` moved in the
  receipt.
- **Row 32 is walk session 7's first round, valid on the same checks**
  (`contact_offsets` empty, the model hashes to r17's, r18's and r19's,
  the task to the one trained, and the spec block is byte-identical to
  row 31's;
  [`retained/p7-quad-1-r20-evaluation.json`](retained/p7-quad-1-r20-evaluation.json)).
  The agent's one change was `contact_w` 2.0 → 3.5, a parameter value with
  the script source unchanged, warm from r19. It fails every seed, on
  slip: W7 0.156–0.270 against 0.15, from 0.090–0.125 in row 31, and on
  every seed the foot that slips most is rear-left (the other three feet
  0.09–0.18). Steps fall to 5–9 per foot (r19: 7–14) and tilt rises to
  25.0–28.7° (r19: 7.9–22.9°). Seed 1109's W9 now passes (1.333, from
  1.571), but 1101's fails (1.600). No seed tips. The warm start did not
  carry r19's gait over: the run's first iteration reads −2.03 reward per
  step against r19's final 4.47, and it ends at 3.56.
- **Row 33 is walk session 7's second round, valid on the same checks**
  (`contact_offsets` empty, the model hashes to r17's–r20's, the task to
  the one trained, and the spec block is byte-identical to row 32's;
  [`retained/p7-quad-1-r21b-evaluation.json`](retained/p7-quad-1-r21b-evaluation.json)).
  The agent set `contact_w` back to 2.0, so the task hashes to r19's
  (`db670704…`), and trained r19's own task warm from r19 for 750
  iterations, to test whether r20's loss of slip came from the weight or
  from the warm start. It passes 2 of 10 (1103 and 1108) and fails slip on
  eight: W7 0.135–0.192, rear-left the worst foot on nine seeds. 1109's W9
  passes (1.400) and 1101's fails (1.600: rear-left 8 steps, the other
  three 5). No seed tips; tilt 23.6–27.2°, as r20's and not r19's
  7.9–22.9°. **So the warm start, not the weight, lost r19's gait**: the
  trainer loads only the actor (`training/cadex_train.py`, `--init-from`),
  so it re-initialises the action noise at 0.30 against r19's final 0.177
  and starts a fresh critic, and both r20 and r21b open the same way (first iterations +1.97,
  −2.03 and +2.19, −1.64 per step, against r19's final 4.47). r21b ends at
  3.65. The agent drew the same conclusion and registered `r22` with
  `initial_std` 0.12 and a learning rate of 5e−5
  ([filmstrip, seed 1101](p4-quad-1-walk-r21b-seed-1101-overview.png),
  [detail](p4-quad-1-walk-r21b-seed-1101-detail.png)).
- **Row 34 is walk session 7's third round, valid on the same checks**
  (`contact_offsets` empty, the model hashes to r17's–r21b's, the task to
  the one trained, and the spec block is byte-identical to row 33's;
  [`retained/p7-quad-1-r22-evaluation.json`](retained/p7-quad-1-r22-evaluation.json)).
  The agent warmed r19 again, this time at `initial_std` 0.12 (below r19's
  final 0.177) and a learning rate of 5e−5, and moved `contact_w` 2.0 → 2.5
  as a declared reward-weight-only task change. It passes 6 of 10 (1101,
  1102, 1106, 1107, 1108, 1109), from row 33's 2 and row 31's 9. Slip
  fails 1103 and 1110 (W7 0.195, 0.156; 0.097–0.195 over ten, and the
  worst foot is now front-right on all ten), W8-low fails 1103 and 1105
  (0.399, 0.355), W9 fails 1104 alone (1.667), and W2 fails 1104 at
  30.03° against 30, with no seed tipping. 1109, r19's one failure, passes
  W9 at 1.500. **The narrower start did not keep r19's gait either**:
  iteration 0 reads +3.86 per step and iteration 5 +4.36 (the run's best),
  then training falls to +0.76 at iteration 19 and climbs back only to
  3.43 at 750, with σ barely moving (0.120 → 0.115). r20 and r21b opened
  at σ 0.30 and r22 at 0.12, and all three lost the gait within twenty
  iterations, so the reset width was not the only cause. The other thing
  `--init-from` resets is the critic, which starts untrained against a
  converged actor; ADR-471 carries the width and not the critic, and
  whether the critic is the rest of it is not measured here
  ([filmstrip, seed 1103](p4-quad-1-walk-r22-seed-1103-overview.png),
  [detail](p4-quad-1-walk-r22-seed-1103-detail.png)).
- **Row 35 is walk session 8's second run, and the first walk evaluation
  to pass every seed.** It is valid on the same checks: `contact_offsets`
  is empty and the trained model has no `margin=` or `gap=`, the model
  hashes to r17's–r22's (6cecfa2d), the task to r19's (db670704), and the
  spec block differs from the frozen one only in `HIP_MM` and `WEIGHT_N`,
  which equal the rig (96.7006 mm, 5.0507 N) and are byte-identical to
  rows 31's and 34's
  ([`retained/p8-quad-1-r24-evaluation.json`](retained/p8-quad-1-r24-evaluation.json)).
  The agent warmed r19 on r19's identical task at r19's own width, with
  the default clip and learning rate and the value-loss weight at 0.05.
  The 3,500 s budget stopped the run at iteration 924 with no final
  policy, so the agent installed its last checkpoint (iteration 900) and
  evaluated that, once; it says it did not choose it by any seed's
  result, and the loop ledger holds no other r24 evaluation. All ten pass
  every predicate: W9 1.0–1.3 (1109 was 1.571 under r19), W7 slip
  0.081–0.111, W3 0.955–1.008, swing clearance 0.275–0.297 hip heights,
  duty 0.437–0.608, W10's lowest foot −0.019 to −0.012 hip heights, and
  8–13 steps per foot. Tilt, 6.5–24.2° against 30, is the thinnest margin.
  **Training did not lose r19's gait this time.** After the iteration-1
  dip that every warm start shows, reward per step never fell below +2.96
  (iteration 18), against about +0.3 to +1.3 for r20–r23, and the total
  loss sat near +66 to +97 against r23's +596 to +652. That fits session
  7's diagnosis, the untrained critic, but no ablation separates it from
  the seed. **This is not R1.** It is the agent's own evaluation and not a
  pre-registered confirmation, and no judge has seen it
  ([filmstrip, seed 1101](p4-quad-1-walk-r24-seed-1101-overview.png),
  [detail](p4-quad-1-walk-r24-seed-1101-detail.png)).
- **Row 36 is R1's confirmation evaluation**, pre-registered in
  [`retained/r1-confirm-1-registration.json`](retained/r1-confirm-1-registration.json)
  (commit `5841202e`) before it ran, and run once. It holds row 35's
  policy (5aaf21e7) at row 35's revision (7df101b0), on the frozen seeds,
  and reads the same numbers: every seed's metrics equal row 35's. Before
  it ran, a fresh engine reopened the project through `cadex export` and
  rebuilt the same revision. The model hashed to 6cecfa2d with no
  `margin=` or `gap=`, the task to db670704, and the policy verified to
  5aaf21e7 (witness error 1.2 × 10⁻⁷ against 10⁻⁴). `contact_offsets` is
  empty, the spec hashes to the registered 25adaa1e, and
  `runner/conformance.py` names no deviation
  ([`retained/r1-confirm-1-evaluation.json`](retained/r1-confirm-1-evaluation.json)).
  The judge's bar is met on 1101, 1105 and 1110 (*Every judge score*).
- `r9-steelfoot` has no row, because it never trained (see *Every
  failure*).

## Every judge score

Fifteen blind-judge scores exist: three seeds on each of the two known
negatives and the three confirmation evaluations. Every one is three calls of
`claude-opus-5-5` with no fallback, and each trait's score is the median of
the three. The bar, frozen in [`README.md`](README.md), is a total of at
least 9 of 12 with no trait under 2, on each judged seed. The receipts are
`retained/judge-*.json`; the table is
[`retained/ot11-evaluations.json`](retained/ot11-evaluations.json)'s
`judges`.

| # | judged | behaviour | seed | V1 | V2 | V3 | V4 | total | meets bar | evaluation's verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `r1-confirm-1` | walk | 1101 | 3 | 3 | 2 | 2 | 10 | yes | pass |
| 2 | `r1-confirm-1` | walk | 1105 | 3 | 3 | 2 | 3 | 11 | yes | pass |
| 3 | `r1-confirm-1` | walk | 1110 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 4 | `r2-confirm-1` | reach | 1101 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 5 | `r2-confirm-1` | reach | 1105 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 6 | `r2-confirm-1` | reach | 1110 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 7 | `r3-confirm-1` | balance | 1101 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 8 | `r3-confirm-1` | balance | 1105 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 9 | `r3-confirm-1` | balance | 1110 | 2 | 3 | 3 | 3 | 11 | yes | pass |
| 10 | `robin` | balance | 1101 | 0 | 1 | 0 | 1 | 2 | no | fail |
| 11 | `robin` | balance | 1105 | 1 | 1 | 2 | 1 | 5 | no | fail |
| 12 | `robin` | balance | 1110 | 0 | 1 | 0 | 1 | 2 | no | fail |
| 13 | `w2-2` | walk | 1101 | 1 | 2 | 0 | 1 | 4 | no | fail |
| 14 | `w2-2` | walk | 1105 | 1 | 1 | 0 | 1 | 3 | no | fail |
| 15 | `w2-2` | walk | 1110 | 1 | 2 | 0 | 1 | 4 | no | fail |

The judge and the spec agree on all fifteen: it fails both negatives and
passes all three confirmations. Its known limit is recorded in the contract:
the still-frame judge does not see `w2-2`'s slip (ADR-460, ADR-461), which
W7 measures. **The first walking gait it has judged is R1's confirmation**
(rows 1–3, 10, 11 and 12 of 12). Every V3 under 3 names the body pitching
or turning, at 4.54 s and 7.26 s on 1101 (the shove at 3.88 s) and near
5.08 s on 1105. That is tilt W2 measures and passes: 1101 reaches 24.0°
and turns 8.1°, 1105 reaches 7.3°, against W2's 30° (6.5–24.2° over all
ten, the thinnest margin in the spec). One call on 1105 scored V2 at 2,
saying the frames "can't fully rule out slipping"; W7 measures slip at
0.081–0.111 against 0.15, and is authoritative for it (ADR-463). Neither
is a contradiction: the judge never fails a seed the spec passes.

## Every revision the agent made, and why

Every revision below is the product agent's, made through its tools, and
its reason is the one it wrote into the run's `registration.json` before
the run launched. *Cited* is the measurement that reason quotes from the
previous evaluation; *evaluation* is the row of *Every evaluation* that
shows whether it helped.

| run | what the agent changed | cited | evaluation | seeds passed | did it help |
|---|---|---|---|---|---|
| `bal-1` | balance task redesigned from ot9's: wheel encoders and IMU yaw read; pay for holding position, heading and low speed under 0.08–0.30 × weight shoves | `r3-ppo-1`: B3 drift ~16 COM heights (limit 2.0), B4 heading ~131° (limit 20), B5 never at rest | 5 | 10 | yes: every predicate passed |
| `reach-r1` | new task: a random target redrawn every 2 s, read by the policy | the fixed-point task could not state Q1–Q4 | 7 | 0 | baseline |
| `reach-r2` | linear distance cost added, coarse reach sharpened to 20 mm, tip-speed cost dropped, alive 1.5 | r1: Q2 failed 10 of 10, median 0.82 arm lengths; film shows one pose whatever the target | 8 | 1 | yes: worst final error fell to 0.04–0.26 |
| `reach-r3` | settle cost ungated, fine reach 2·exp(−d/5), entropy 0 | r2: Q2 failed 9 of 10, median 0.099; a steady offset short of target | 9 | 0 | no: 0.07–0.31, worse |
| `reach-r4` | tip-speed cost linear, force² cost raised, joint rates privileged | r3: settle cost at its ceiling, ~120 N·mm RMS force against ~35 N·mm to hold: chatter | 10 | 9 | yes: 0.008–0.055 |
| `reach-r5` | warm start from r4's iteration 475; reach scale 20→10 mm, fine weight 2→3 | r4: seed 1106 at 0.0550 against 0.05, holding 8 mm short | 11 | 10 | yes: every seed |
| `r1-clearance` | goal-conditioned walk task: commanded speed, foot height × foot speed, sink and diagonal-sync costs | `w2-2`: W7 slip 49–81 % | 13 | 0 | baseline; collapsed |
| `r2-bounded` | every cost bounded with tanh, alive 3 | r1 collapsed, every step net negative; W3 −1.46 to −0.05 | 14 | 0 | partly: no collapse, still backwards |
| `r3-nochatter` | hip and knee chatter charged, landing-speed cost | r2: ~360°/s RMS knee chatter, read from the knee-speed reward term; W3 −2.06 to −1.22 | 15 | 0 | no: still backwards |
| `r4-anglesonly` | joint rates and gyro removed from the inputs, damping randomised; first run on the ADR-465 trainer | r3: chatter still ~350°/s in evaluation though charged in training; W3 −1.89 to −1.06 | 16 | 0 | no: it stands |
| `r5-swing` | inputs restored; per-foot swing pay, grounded-slip cost | r4: stands still: W5-steps 0, W8-high 1.0, W3 ~0.00 | 17 | 0 | yes for speed: W3 passes 9 of 10 |
| `r6-trot` | stronger trot sync, slip and sink costs; warm start from r5 | r5: only the front-left foot steps: W9 5.7–33, W7 0.46–0.53 | 18 | 0 | yes for slip: 0.28–0.32 |
| `r7-relswing` | swing paid on body-relative foot speed; warm start from r6 | r6: W8-low 0.23–0.27, front feet held up | 19 | 0 | mixed: slip 0.14–0.31, collapsed |
| `r8-stance` | **mechanism**: stance hip 18°/knee −30° (base +10.25 mm); diagonal-trot term; fresh start | r6: W10 −0.175 to −0.09 HH, W8-low 0.23–0.27, W9 6.3–39, W7 0.28–0.32 | 21 | 0 | no: stands on one diagonal pair, W8-low 0.00; void |
| `r10-steelfoot-fresh` | **mechanism**: steel-ball feet (foot 1.5 → 10.5 g), stance back to 30°/−60°; trot term removed, grounded slip 1.5, alive 3.5; fresh start | r8: W10 −0.095 to −0.06 HH, W8-low 0.00 from a diagonal pair held up for the trot pay | 22 | 0 | yes for W10 (−0.029 to −0.021, every seed); no for gait: stands on three feet, W3 ≈ 0.00 |
| `r11-speedpay` | speed tracking 2 → 4 with its Gaussian widened 0.4 → 0.6 × command, speed error −1 → −2; warm start from r10 | r10: W3 ≈ 0.00, W5-steps 0, W8-high 1.0; standing nets +2.17 per step | 23 | 0 | no: W3 0.015–0.033, still no step; rocks in place, and speed pay rises from +0.03 to +1.0–1.65 per step |
| `r12-convex-sym` | Gaussian speed pay replaced by a convex speed cost; swing pay signed, with a 0.15 cost on any lifted foot; diagonal-symmetry and hip-antiphase costs on the joint encoders; alive 5; fresh start | r11: W8-low 0.00, W5-steps 0, W3 0.015–0.033; speed pay +1.3 per step for rocking, swing pay +0.21 for jiggling a raised foot | 24 | 0 | partly: it travels (W3 0.65–0.81, passes 5 of 10) and both front feet step (6–11 steps), but the rear-left foot is held up on every seed (W8-low 0.00), the rear-right drags (slip 0.85–0.98), and W10 fails again (−0.154 to −0.074) |
| `r13-hovercost-margin` | hover cost 0.15 → 0.6 and swing pay rescaled; tilt cost −20 → −40, alive 6; **mechanism**: a 3 mm contact margin on each foot sphere; fresh start | r12: slip 0.85–0.98 against a 0.15 hover cost, so a foot held up was cheapest (W8-low 0.00); W10 −0.154 to −0.074 | 25 | 0 | partly: all four feet now leave the floor (W5-steps passes 10 of 10), tilt falls to 3.6–6.8° and W10 passes, but the margin holds every resting foot 0.7–3.5 mm above the floor, so W10's pass is the margin and the evaluation reads most of stance as swing (W8-low 0.02–0.09); clearance 0.03–0.04 HH (W6) and W3 0.28–0.64 fail. **Void for R1** (margin model, owner 2026-10-01) |
| `r14-margin15-lift` | **mechanism**: foot contact margin 3 → 1.5 mm; hover cost flat past ~3 mm and swing pay growing with height (h/14 mm); a linear term in the speed cost; fresh start | r13: W8-low duty_min 0.02–0.09, W6 clearance 0.032–0.038 HH, W3 0.28–0.64, W7 0.12–0.22 | 26 | 0 | partly: W3 passes on every seed (speed_ratio 0.98–1.05) and every foot steps 19–25 times, but clearance falls to 0.020–0.026 HH (W6), duty_min stays 0.30–0.33 (W8-low), and on half the margin W10 fails 9 of 10 (−0.066 to −0.049 HH). **Void for R1** (margin model; voided by `cadex evaluate`, ADR-470) |
| `r15-stiffspring-clearfoot` | **mechanism**: the foot margin removed and the model rebuilt on ADR-469's 0.004 s spring; the moving-foot cost fades as a 6 mm Gaussian of lift instead of exp(−h/3 mm), weight 1.5 → 2.0; fresh start | r14: W6 clearance 0.020–0.026 HH, W8-low duty_min 0.30–0.33, W7 slip 0.11–0.16, W10 −0.066 to −0.049 HH | 27 | 0 | no: no foot steps on any seed (W5-steps 0, duty 1.0), five seeds tip within 0.94 s (W1, W2) and the five that stand slide their feet (slip 0.54–0.80) at speed_ratio 0.03–0.06. W10 passes on every seed that stands (−0.015 to −0.003 HH): on the new spring a standing foot sinks under 1.5 mm |
| `r16-alive10` | alive 6 → 10; the moving-foot cost weight 2.0 → 1.5, keeping the 6 mm Gaussian fade; same model; fresh start | r15: W1/W2 on 5 seeds (tipped at 0.50–0.94 s); a surviving step netted −1.16 to −1.21, so tipping beat staying up | 28 | 0 | partly: a surviving step now nets +4.4 to +5.4 and tips come later (1.76–6.58 s against 0.50–0.94 s), but more seeds tip (8 against 5). Five lunge at speed_ratio 0.75–0.97 and tip before their shove; five stand on three legs, rear-left held 34–50 mm up, and three tip after their shove. No foot steps four times (W5-steps max 1). W10 passes on every seed (−0.010 to −0.002 HH) |
| `r17-discount-bodyrate` | discount 0.97 (the trainer default) → 0.995; a bounded roll/pitch-rate cost (`body_rate`, weight −1.5, scale 90°/s); same model; fresh start | r16: W1/W2 on 8 seeds (tipped at 1.76–6.58 s, tilt 37–42°) with training episodes of 100–140 steps, so a fall sat beyond the discount horizon; W7 0.26–0.74, W5-steps 0–1, W8-low 0.0–0.39 | 29 | 1 | yes: no seed tips (W1/W2 pass 10 of 10, tilt 12.4–17.2°), every foot steps 5–14 times (W5-steps 10 of 10), W3, W6, W8 and W10 pass on every seed, and seed 1108 passes all thirteen predicates. Slip still fails on 8 (W7 0.154–0.208) and the rear feet out-step the front (W9 1.4–2.4 on 8) |
| `r18-sync-slip` | **reward weights only**: trot_sync 1 → 2.5, diag_sym 1 → 2, slip 1.5 → 2.2, speed_error 5 → 8 so that walking still beats standing; same model; warm start from r17 | r17: W7 0.154–0.208 on 8 seeds, W9 1.75–2.4 on 8 (the rear feet stepping about twice as often as the front), with trot_sync and diag_sym costs showing the diagonal pairs out of phase | 30 | 2 | partly: slip is fixed (W7 passes 10 of 10, 0.096–0.146) and seeds 1102 and 1108 pass every predicate, but W9 still fails on 8 (1.56–2.33), and seed 1107 tips 0.61 s after the largest shove (0.97 N) |
| `r19-contact-sync` | **reward only**: a new `contact_sync` cost (weight `contact_w` 2) on diagonal-pair contact-state mismatch, c = exp(−((z − z_stand)/8 mm)²), in the slot of the `sink` term, which it removed because a task allows at most 16 reward terms; same model; warm start from r18, 750 iterations | r18: W9 1.56–2.33 on 8 seeds while diag_sym showed the diagonal joint angles matched within about 4.5° RMS, so the extra steps were brief touchdowns of one foot that the squared-millimetre trot_sync barely charges; 1107 tipped at 5.9 s | 31 | 9 | yes: W9 falls to 1.18–1.57 and passes on 9 of 10. No seed tips, and slip, clearance, duty and W10 hold on all ten. Seed 1109, the slowest command (0.628 HH/s), fails W9 alone at 1.571 |
| `r20-contact35` | **reward weight only**: `contact_w` 2.0 → 3.5, the script source unchanged; same model; warm start from r19, 700 iterations | r19: W9 1.571 on seed 1109, where rear-left stepped 11 times against the front feet's 7 and 8 and `contact_sync` charged about −66 per episode | 32 | 0 | no: 1109's W9 passes (1.333), but slip fails on all ten (W7 0.156–0.270, rear-left the worst foot on every seed), and 1101 fails W9 (1.600) |
| `r21b-r19-continue` | **nothing in the task**: `contact_w` back to 2.0, so r19's task byte for byte, continued warm from r19 for 750 iterations | r20: W7 0.156–0.270 on all ten after `contact_w` 3.5, with training reward falling from r19's 4.47 to about 0.9 within 50 iterations, so it asked whether the weight or the warm start lost the gait | 33 | 2 | no for R1, yes as a test: slip fails 8 of 10 (W7 0.135–0.192) with the weight restored, so the warm start's reset action noise (0.30 against r19's 0.177) lost the gait, not the weight |
| `r22-gentle-contact25` | **reward weight and trainer settings**: `contact_w` 2.0 → 2.5 (declared as a reward-weight-only change), warm from r19 at `initial_std` 0.12 and learning rate 5e−5, 750 iterations | r21b: W7 0.135–0.192 on 8 seeds and W9 1.6 on 1101 with r19's task restored, training reward 2.19 → 0.99 in 20 iterations, so it asked for a gentler fine-tune that keeps r19's gait | 34 | 6 | partly: 6 of 10, the best since r19's 9; 1109's W9 passes (1.500), slip fails 2 (W7 0.156–0.195), W8-low 2, W9 and W2 one each on 1104 (1.667, 30.03°). Training still fell from +4.36 to +0.76 by iteration 19, so a narrower start did not keep the gait |
| `r24-r19-vw005` | **trainer settings only**: r19's task byte for byte, warm from r19 at r19's own width, default clip and learning rate, value-loss weight 0.05, checkpoints every 25, 1,200 iterations in 3,500 s | r23 (no evaluation; the agent's run before it, stopped): reward per step fell 4.40 → 0.26 by iteration 86 while the total loss sat at +596 to +652, after r22 (row 34) had already fallen at a narrower width, so it read the fresh critic's value loss as what moved the actor | 35 | 10 | yes: 10 of 10 on every predicate, W9 1.0–1.3, slip 0.081–0.111; training never fell below +2.96 after iteration 1. The agent's evaluation of its last checkpoint, not a confirmation |

The reach rows are four consecutive design–train–evaluate–revise rounds,
each motivated by the previous evaluation and each answered by the next;
walk rounds 5–7 are three more. That is P4's evidence of a loop. Rounds 1–3
of walk trained on a trainer whose servo physics disagreed with the
engine's (ADR-465), so what they measured about the reward is weaker than
the rows suggest.

## Every failure

Each item names its receipt.
- **Thirty of 36 evaluations failed** (every row above except 5, 6, 11,
  12, 35 and 36), and four of them are void: rows 20 and 21 on a scale digit, rows
  25 and 26 for R1 on their foot contact margins.
- **Two runs collapsed** and were stopped by `--stop-on-collapse`:
  `r1-clearance` after 569 iterations and `r7-relswing` after 538
  ([`retained/ot11-runs.json`](retained/ot11-runs.json)). Each was
  evaluated on its best or an early checkpoint.
- **Eight runs ended at their wall-clock budget** before or at their last
  iteration (`budget_exhausted`, same receipt). Each was evaluated on a
  checkpoint it had written.
- **Two starts were refused, and are not attempts.** `r9-steelfoot`'s
  trainer exited 1 after 52.03 s with no iteration run: a warm start may
  not change what the network reads, and the steel-foot model changed it.
  Its supervisor's status is in the project's
  `runs/r9-steelfoot/training-status.json`. `run_ledger.py` carries it as
  row 15 of the run table with `attempt: false`, so the receipt counts 17
  attempts in 18 runs. The agent re-registered the same task fresh as
  `r10-steelfoot-fresh`. `r21-r19-continue`'s trainer exited 1 after
  52.28 s, also with no iteration run: the agent passed
  `--init-from-task-change` for a bundle byte-identical to the one its
  warm start trained on, and the trainer refuses that flag when there is
  no change (row 27, `attempt: false`). The agent re-registered it without
  the flag as `r21b-r19-continue`.
- **One run was stopped by the agent and saved no policy, so it has no
  evaluation** (`r23-r19-clip05`, row 30, `stopped`). It was walk session
  8's first run: warm from r19 with the PPO clip at 0.05. After 87
  iterations (261.25 s), the agent stopped it through `train_stop`. Its
  reason, in the project's `loop-ledger.jsonl`, is that training reward per
  step fell from 4.40 at iteration 5 to 0.72 at iteration 74, the same
  warm-start loss as r20–r22. Its next registration (`r24-r19-vw005`)
  quotes the total loss holding at +596 to +652 while reward fell, and
  attributes the fall to the fresh critic's value loss. No policy was
  saved, so there was nothing to evaluate.
- **Walk session 3 ended at 0 of 10 on all three of its runs**
  (`r8-stance`, `r10-steelfoot-fresh`, `r11-speedpay`; rows 21–23,
  `retained/p4-quad-1-s3-rounds.json`). The steel feet fixed W10, and no
  round produced a step. The README's *Walk session 3 closes* says what the
  session measured as a whole.
- **Walk session 4's first round failed 0 of 10** (`r12-convex-sym`, row
  24, [`retained/p4-quad-1-r12-evaluation.json`](retained/p4-quad-1-r12-evaluation.json)).
  It was the first round since session 2 to travel and to step, on three
  legs, and the stepping front feet failed W10.
- **Walk session 4's second round failed 0 of 10** (`r13-hovercost-margin`,
  row 25, [`retained/p4-quad-1-r13-evaluation.json`](retained/p4-quad-1-r13-evaluation.json)).
  All four feet stepped for the first time in ot11, on a 3 mm foot contact
  margin that held the feet above the floor; W3, W6 and W8-low failed on
  every seed. It is void for R1 on that margin (owner, 2026-10-01).
- **Walk session 4's third round failed 0 of 10, and is void**
  (`r14-margin15-lift`, row 26,
  [`retained/p4-quad-1-r14-evaluation.json`](retained/p4-quad-1-r14-evaluation.json)).
  It travels at the commanded speed and every foot steps, on a 1.5 mm
  margin; W6 and W8-low fail on every seed and W10 on nine. Session 4
  closed at its three-run limit with no evaluation passing a seed.
- **Walk session 5's first round failed 0 of 10** (`r15-stiffspring-clearfoot`,
  row 27, [`retained/p5-quad-1-r15-evaluation.json`](retained/p5-quad-1-r15-evaluation.json)).
  It is valid: no contact offset, the ADR-469 spring. No foot steps on any
  seed, and five seeds roll onto their side within 0.94 s
  ([filmstrip, seed 1101](p4-quad-1-walk-r15-seed-1101-overview.png)).
- **Walk session 5's second round failed 0 of 10** (`r16-alive10`,
  row 28, [`retained/p5-quad-1-r16-evaluation.json`](retained/p5-quad-1-r16-evaluation.json)).
  Valid on the same checks. Eight seeds tip, five of them in a forward
  lunge before the shove
  ([filmstrip, seed 1101](p4-quad-1-walk-r16-seed-1101-overview.png)).
- **Walk session 5's third round failed 1 of 10** (`r17-discount-bodyrate`,
  row 29, [`retained/p5-quad-1-r17-evaluation.json`](retained/p5-quad-1-r17-evaluation.json)).
  Valid on the same checks. It walks all ten seeds to the horizon, and
  nine fail on slip (W7) and on the rear feet stepping more often than
  the front (W9, W5-share)
  ([filmstrip, seed 1101](p4-quad-1-walk-r17-seed-1101-overview.png)).
- **Walk session 6's first round failed 2 of 10** (`r18-sync-slip`,
  row 30, [`retained/p6-quad-1-r18-evaluation.json`](retained/p6-quad-1-r18-evaluation.json)).
  Valid on the same checks. Slip passes on every seed; eight fail W9, the
  rear feet stepping 1.56–2.33 times as often as the front, and seed 1107
  tips after its shove
  ([filmstrip, seed 1101](p4-quad-1-walk-r18-seed-1101-overview.png)).
- **Walk session 6's second round failed 9 of 10** (`r19-contact-sync`,
  row 31, [`retained/p6-quad-1-r19-evaluation.json`](retained/p6-quad-1-r19-evaluation.json)).
  Valid on the same checks. Seed 1109 fails W9 alone (1.571 against 1.5)
  at the lowest commanded speed of the ten
  ([filmstrip, seed 1109](p4-quad-1-walk-r19-seed-1109-overview.png),
  [detail](p4-quad-1-walk-r19-seed-1109-detail.png)).
- **Walk session 7's first round failed 0 of 10** (`r20-contact35`,
  row 32, [`retained/p7-quad-1-r20-evaluation.json`](retained/p7-quad-1-r20-evaluation.json)).
  Valid on the same checks. Raising `contact_w` 2.0 → 3.5 fixed seed
  1109's W9 and broke slip on all ten, with rear-left the worst foot on
  every seed
  ([filmstrip, seed 1101](p4-quad-1-walk-r20-seed-1101-overview.png),
  [detail](p4-quad-1-walk-r20-seed-1101-detail.png)).
- **Walk session 7's second round failed 8 of 10** (`r21b-r19-continue`,
  row 33, [`retained/p7-quad-1-r21b-evaluation.json`](retained/p7-quad-1-r21b-evaluation.json)).
  Valid on the same checks. r19's own task, continued warm from r19,
  fails slip on eight seeds: a warm start resets the action noise to the
  trainer's 0.30 and loses the gait it starts from
  ([filmstrip, seed 1101](p4-quad-1-walk-r21b-seed-1101-overview.png),
  [detail](p4-quad-1-walk-r21b-seed-1101-detail.png)).
- **Walk session 7's third round failed 4 of 10** (`r22-gentle-contact25`,
  row 34, [`retained/p7-quad-1-r22-evaluation.json`](retained/p7-quad-1-r22-evaluation.json)).
  Valid on the same checks. A warm start from r19 at a narrower σ (0.12)
  and a lower learning rate passes six seeds and fails 1103, 1104, 1105
  and 1110 on slip, duty, W9 and tilt; training still lost r19's gait in
  its first twenty iterations
  ([filmstrip, seed 1103](p4-quad-1-walk-r22-seed-1103-overview.png),
  [detail](p4-quad-1-walk-r22-seed-1103-detail.png)).
- **Walk session 6 trained two runs, not the three it registered.**
  `runner/rounds.py` stops when the project's ledger holds `--max-runs`
  evaluations. The agent's first act was to re-evaluate r17 (the
  ledger's 20th evaluated row, at 12:24 UTC, four minutes after the
  session was registered, is a second row for r17's policy), so r19's
  evaluation was the 22nd and the driver ended the session after its
  first turn
  ([`retained/p4-quad-1-s6-preregistration.json`](retained/p4-quad-1-s6-preregistration.json)).
  Fixed for session 7: the driver counts runs, not evaluations.
- **Walk session 7's driver counted its refused start as one of its three
  runs.** `r21-r19-continue` failed before iteration 0 (run row 27,
  `attempt: false`), and the driver it was launched with counted it as a
  settled run. It did not cut the session short: the driver reads its run
  count only between turns, and the agent trained `r20`, `r21b` and `r22`
  inside the session's first turn, then ended it on its own
  (`ot11-notes/quad-1-s7/turn-1` is the only turn). For any later session,
  `runner/rounds.py` reads the run's status and counts a `failed` end with
  no iteration as a refused start that uses up nothing, the same rule as
  `run_ledger.py` (pinned by `test_a_refused_start_does_not_use_up_a_round`).
- **Warm start was unreachable for reach r3.** The agent guessed five paths
  for `init_from_parent_task`, and `train_start` refused each; seven
  `train_start` calls errored in that session
  ([`retained/p4-heron-1-rounds.json`](retained/p4-heron-1-rounds.json)).
  It was fixed for later rounds, and `reach-r5` and `r6-trot` warm-started.
- **Three defects in the pipeline itself were found by its own
  evaluations** and fixed by decision: the trainer's servo integration
  (ADR-465), W10 read during the reset drop (ADR-467, every earlier policy
  re-read), and a stale scale constant in a spec (ADR-468).

## Remaining defects

What is still wrong or unmeasured at this revision, each with its receipt.
A defect fixed by decision is under *Every failure*, not here.
- **R1's measured bar is reached by row 36, its pre-registered
  confirmation, and the owner ticks it; this page does not.** Rows
  13–28 of *Every evaluation* pass 0 of 10, row 29 passes 1 of 10
  (seed 1108), row 30 passes 2 of 10 (seeds 1102 and 1108), row 31
  passes 9 of 10 (all but 1109), row 32 passes 0 of 10, row 33 passes
  2 of 10 (1103 and 1108), row 34 passes 6 of 10 and row 35, the agent's
  own evaluation of `r24-r19-vw005`'s iteration-900 checkpoint, passes
  10 of 10
  ([`retained/ot11-evaluations.json`](retained/ot11-evaluations.json)).
  Walk session 4
  ([`retained/p4-quad-1-s4-preregistration.json`](retained/p4-quad-1-s4-preregistration.json))
  closed at its three-run limit: rows 24, 25 and 26, the last two void.
  Walk session 5
  ([`retained/p4-quad-1-s5-preregistration.json`](retained/p4-quad-1-s5-preregistration.json)),
  the first on a model with the ADR-469 spring and no contact offset,
  closed at its three-run limit: rows 27, 28 and 29. Walk session 6
  ([`retained/p4-quad-1-s6-preregistration.json`](retained/p4-quad-1-s6-preregistration.json))
  ran on the same model and closed after two rounds: rows 30 (2 of 10)
  and 31 (9 of 10). Walk session 7
  ([`retained/p4-quad-1-s7-preregistration.json`](retained/p4-quad-1-s7-preregistration.json))
  ran on the same model in one turn and closed after three rounds: rows
  32 (0 of 10), 33 (2 of 10) and 34 (6 of 10), every one warm from r19.
  The agent closed it with r19 declared again and a written decision not
  to fine-tune an evaluated policy until the warm start's opening loss is
  fixed, which it attributes to an untrained critic. ADR-471 carries the
  exploration width into a warm start; r22, at a width below r19's own,
  lost the gait the same way, so the width alone is not the fix, and the
  critic is unmeasured. Walk session 8
  ([`retained/p4-quad-1-s8-preregistration.json`](retained/p4-quad-1-s8-preregistration.json))
  starts from the same model and r19 declared, with at most three runs of
  at most 3,600 s each. Its prompt gives the warm-start training
  measurements and no remedy, and the agent chooses the revision. Its
  first run, `r23-r19-clip05` (row 30), was stopped by the agent with no
  policy (above). Its second, `r24-r19-vw005`, warm from r19 with the
  value-loss weight at 0.05, passes 10 of 10 (row 35), and the agent ended
  the session on it with `walk_r24.cxpolicy` declared. R1's confirmation
  ([`retained/r1-confirm-1-registration.json`](retained/r1-confirm-1-registration.json),
  committed before it ran) reopened and verified that revision through
  `cadex export`, then passed 10 of 10 (row 36) and met the judge's bar
  on all three judged seeds (10, 11 and 12 of 12). What stays a defect is
  how thin the tilt margin is: four seeds reach 23.9–24.2° against W2's
  30°, after a shove of at most 0.2 body weights.
- **The judge does not see stepping or slip.** Its manner score gave
  `w2-2` "real steps" on all eighteen calls on seeds 1101 and 1110, while
  W5 and W7 failed them (ADR-460, ADR-461, ADR-463;
  [`retained/judge-w2-2-seed-1101.json`](retained/judge-w2-2-seed-1101.json)).
  That is a recorded limit of the contract, and W5 and W7 are
  authoritative for it.
- **W10 under a gait on the steel-ball feet passed on the floor only on ADR-469's spring.**
  Round 11's stepping front feet sank to −0.154 to −0.074 hip heights
  ([`retained/p4-quad-1-r12-evaluation.json`](retained/p4-quad-1-r12-evaluation.json)).
  Round 12 passes W10 on every seed, but only because its 3 mm foot contact
  margin makes MuJoCo push on a foot before its sphere reaches the floor.
  Over the settled frames, the median height of a foot that bears load was
  −3.1 to +0.4 mm in rounds 10 and 11, and +1.5 to +3.5 mm on all four
  feet in round 12
  ([`retained/p4-quad-1-r13-evaluation.json`](retained/p4-quad-1-r13-evaluation.json),
  `rest_height`). The pass is not a fix. With no contact offset, on
  ADR-469's spring, W10 holds under a stepping gait on every seed of rows
  29–36, where round 11's stepping feet on the old spring sank; on R1's
  confirmation (row 36) the lowest foot reached −0.019 to −0.012 hip
  heights over the ten seeds
  ([`retained/r1-confirm-1-evaluation.json`](retained/r1-confirm-1-evaluation.json)).
- **A foot contact margin moves what the gait predicates read.** The
  contract reads a foot's geometry: stance is a sphere at or under 1.0 mm
  (`STANCE_MM`), and slip is counted only between stance frames. With a
  3 mm margin, 48–96 % of round 12's settled frames sat between 1 and 4 mm,
  bearing load but read as swing. So W8 and W7 under-read stance and slip,
  and W5 can count a hover that moves forward as a step. Round 12's verdict is still a
  fail, on W3, W6 and W8-low. The spec is unchanged. **The owner decided
  this on 2026-10-01** (charter R1): a margin, a gap or any setting that
  holds geometry off the floor does not count as passing W10, whoever
  authors it, and a policy evaluated on such a model is void for R1. Round
  12 is void for R1, and so is the agent's next run, `r14-margin15-lift`
  (row 26), which cut the margin to 1.5 mm. **The product now applies that void
  itself** (ADR-470): `cadex evaluate` voids every seed of a model with a
  contact margin or gap and lists the geoms in the report's
  `contact_offsets`. On the retained models it lists r13's four feet at
  3.0 mm and r14's at 1.5 mm, and nothing on any other ot11 run, Robin or
  Heron model. Row 25 was evaluated before that and keeps its published
  verdict, with the void it was given by hand; row 26 was voided by
  the product. The walk session's mechanism
  rule still permits a margin in training. Only the evaluation is void.
- **The feet sank because the exported contact spring was soft, and that
  is fixed in the product for models exported from now on** (ADR-469).
  Every geom and the environment floor were on MuJoCo's default 0.02 s
  spring, and a soft contact sinks in proportion to the acceleration
  pressing on it. Round 11's policy, on its own MJCF and ten seeds, sank a
  foot 6.18–7.62 mm on that spring and 0.66–2.50 mm at 0.004 s
  ([`retained/p4-quad-1-contact-depth.json`](retained/p4-quad-1-contact-depth.json)).
  Every walk round so far trained and was evaluated on the old spring,
  because a bundle carries the MJCF it was accepted with; a revision
  accepted after ADR-469 gets the new one. `ot11-quad-1` was rebuilt on it
  with no foot margin (revision `af05ab62`): driven by r14's policy over
  seeds 1101–1110, every foot lifting off 8–41 times per seed, the deepest
  foot point after the settle is −0.89 to −1.37 mm, −0.009 to −0.014 hip
  heights against W10's −0.05
  ([`retained/p5-quad-1-rebuilt-depth.json`](retained/p5-quad-1-rebuilt-depth.json)).
  That is the contact under a stepping load, not a W10 pass. The first
  policy trained on this model (row 27) holds W10 on the five seeds that
  stand (−0.015 to −0.003 HH, a foot at most 1.45 mm under), but it takes
  no step. The second (row 28) lifts every foot and lands most of them,
  but no more than once or twice a seed, and holds W10 on all ten
  (−0.010 to −0.002 HH). The third (row 29) is the first policy
  trained on this model to step steadily: every foot steps 5–14 times a
  seed over the full 10 s, and the deepest foot point is −0.0172 to
  −0.0129 HH (1.25–1.66 mm under), so W10 holds on all ten under a
  sustained stepping load.
- **Walk rounds 1–3 trained on a trainer whose servo physics disagreed
  with the engine's** (ADR-465). Their evaluations stand, and what they
  say about their rewards is weaker than their rows suggest.
- **Nothing in the product refuses a reworded predicate.** ADR-468 makes
  the engine refuse a spec whose stated scale differs from the model, and
  the actor checks the walk spec block against
  [`retained/walk-spec-block.txt`](retained/walk-spec-block.txt) after each
  evaluation, under the session's pre-registered `mechanism_rule`. Since
  ADR-472 every stored evaluation's resolved spec is also compared with the
  contract when the evaluation ledger is built, so a drifted seed, bound,
  metric, shove or goal is named in the receipt beside its row. That check
  reports and does not refuse, and it runs when the ledger is rebuilt, not
  when `cadex evaluate` runs.
- **The packaged lifecycle gate was owed from ADR-465 to ADR-468** and is
  now paid: the payload was rebuilt and restaged from engine source
  unchanged since ADR-468 (commit `d410b098`), and
  `test_cadexd_lifecycle.py` passed 23 of 23, none skipped, against it on
  2026-10-01. ADR-469's contact spring is an engine change made after it,
  so the gate was owed again. It is paid: the payload was rebuilt and
  restaged from `22d30e7e` (which carries `CONTACT_TIMECONST_S = 0.004`),
  and `test_cadexd_lifecycle.py` passed 23 of 23 against it. ADR-470's
  evaluation void is engine source too. The payload was restaged with it,
  and the gate passed 23 of 23 again. Suites at that revision: test-engine
  2523 passed, 60 skipped; cli/tests 1271 passed, 1 skipped.
