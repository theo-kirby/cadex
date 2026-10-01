# ot11 closing report

Verified against source: 2026-10-01. `[Cadex-new]`

This is C1's report for run ot11 (charter: `.ouroboros/goal.md`). It is
written while the run continues, one section at a time, and each section is
held to a receipt under [`retained/`](retained/) by
`cli/tests/test_ot11_report.py`. The evidence behind every claim, and the
contract the evaluations are read against, is in [`README.md`](README.md).
The owner ticks the criteria; this page does not.

## Every training run

Fourteen runs have been trained in ot11, all through the product's
`train_start` tool, one GPU job at a time, with `--stop-on-collapse` on.
Every one was registered before it launched: its settings, its seed, its
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

| behaviour | runs | GPU time, s |
|---|---|---|
| balance | 1 | 900.57 |
| reach | 5 | 4,447.41 |
| walk | 8 | 16,344.37 |
| **all** | **14** | **21,692.35** |

**How to read the two times.** *GPU time* is the supervisor's wall time
from launch to exit; the trainer holds the GPU for all of it, so it is the
time the charter counts, and it exists for every run. *The trainer's own
time* is the figure in the trainer's receipt, which a trainer writes only
when it saves its final policy. A run stopped at its wall-clock budget or on
collapse has none. The difference, 148 to 202 s on the four walk runs that
have both, is time the supervisor measured outside the trainer's own clock.

**Earlier figures on the README.** Rounds 1–4 of the walk, and every reach
and balance round, quote the GPU time above. Round 5's section quotes
1,898 s, which is its trainer's own time; its GPU time is 2,099.82 s.

**What the table leaves out.** Settings not shown are in the receipt:
`checkpoint_every`, the network size where the agent set it, and
`entropy`, which reach rounds 3–5 set to 0. A warm start names the run whose
policy it began from; `reach-r5` began from `reach-r4`'s iteration-475
checkpoint and `r6-trot` from `r5-swing`'s final policy, and `r7-relswing` from
`r6-trot`'s. Robin's ot9
baseline (`r3-ppo-1`) and ot10's `w2-2` are earlier runs measured as known
negatives (P1), not ot11 training runs, and are not in this table.
