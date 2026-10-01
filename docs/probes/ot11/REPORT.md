# ot11 closing report

Verified against source: 2026-10-01. `[Cadex-new]`

This is C1's report for run ot11 (charter: `.ouroboros/goal.md`). It is
written while the run continues, one section at a time, and each section is
held to a receipt under [`retained/`](retained/) by
`cli/tests/test_ot11_report.py`. The evidence behind every claim, and the
contract the evaluations are read against, is in [`README.md`](README.md).
The owner ticks the criteria; this page does not.

## Every training run

Nineteen runs have ended in ot11, eighteen attempts and one refused start
(`r9-steelfoot`, row 15: its trainer exited before its first iteration).
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

| behaviour | runs | GPU time, s |
|---|---|---|
| balance | 1 | 900.57 |
| reach | 5 | 4,447.41 |
| walk | 13 | 24,965.71 |
| **all** | **19** | **30,313.69** |

**How to read the two times.** *GPU time* is the supervisor's wall time
from launch to exit; the trainer holds the GPU for all of it, so it is the
time the charter counts, and it exists for every run. *The trainer's own
time* is the figure in the trainer's receipt, which a trainer writes only
when it saves its final policy. A run stopped at its wall-clock budget or on
collapse has none. The difference, 148 to 202 s on the nine walk runs that
have both, is time the supervisor measured outside the trainer's own clock.

**Earlier figures on the README.** Rounds 1–4 of the walk, and every reach
and balance round, quote the GPU time above. Round 5's section quotes
1,898 s, which is its trainer's own time; its GPU time is 2,099.82 s.

**What the table leaves out.** Settings not shown are in the receipt:
`checkpoint_every`, the network size where the agent set it, and
`entropy`, which reach rounds 3–5 set to 0. A warm start names the run whose
policy it began from; `reach-r5` began from `reach-r4`'s iteration-475
checkpoint and `r6-trot` from `r5-swing`'s final policy, and `r7-relswing` from
`r6-trot`'s, and `r11-speedpay` from `r10-steelfoot-fresh`'s. Robin's ot9
baseline (`r3-ppo-1`) and ot10's `w2-2` are earlier runs measured as known
negatives (P1), not ot11 training runs, and are not in this table.

**What the table leaves out, continued.** `r9-steelfoot` is in the table
and in the totals because its supervisor ran for 52.03 s, but it is not an
attempt (`attempt: false` in the receipt): it trained nothing. A run still
training has no end time yet, so the receipt lists it under `in_progress`
and in no total. When this was last regenerated that was `r14-margin15-lift`,
walk session 4's third run, registered at 08:36:27Z and training fresh.

## Every evaluation

Twenty-five evaluations are stored across the five ot11 projects, every one
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
- **No walk evaluation has passed a seed.** Every walk row reads on W10's
  ADR-467 code, after the settle; the earlier rows were re-read when that
  decision was taken.
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
  engine scored it, and it fails 0 of 10 regardless. `r14-margin15-lift`,
  training on a 1.5 mm margin, is void for R1 on the same clause, and any
  evaluation of it will be reported as void.
- `r9-steelfoot` has no row, because it never trained (see *Every
  failure*).

## Every judge score

Twelve blind-judge scores exist: three seeds on each of the two known
negatives and the two confirmation evaluations. Every one is three calls of
`claude-opus-5-5` with no fallback, and each trait's score is the median of
the three. The bar, frozen in [`README.md`](README.md), is a total of at
least 9 of 12 with no trait under 2, on each judged seed. The receipts are
`retained/judge-*.json`; the table is
[`retained/ot11-evaluations.json`](retained/ot11-evaluations.json)'s
`judges`.

| # | judged | behaviour | seed | V1 | V2 | V3 | V4 | total | meets bar | evaluation's verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `r2-confirm-1` | reach | 1101 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 2 | `r2-confirm-1` | reach | 1105 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 3 | `r2-confirm-1` | reach | 1110 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 4 | `r3-confirm-1` | balance | 1101 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 5 | `r3-confirm-1` | balance | 1105 | 3 | 3 | 3 | 3 | 12 | yes | pass |
| 6 | `r3-confirm-1` | balance | 1110 | 2 | 3 | 3 | 3 | 11 | yes | pass |
| 7 | `robin` | balance | 1101 | 0 | 1 | 0 | 1 | 2 | no | fail |
| 8 | `robin` | balance | 1105 | 1 | 1 | 2 | 1 | 5 | no | fail |
| 9 | `robin` | balance | 1110 | 0 | 1 | 0 | 1 | 2 | no | fail |
| 10 | `w2-2` | walk | 1101 | 1 | 2 | 0 | 1 | 4 | no | fail |
| 11 | `w2-2` | walk | 1105 | 1 | 1 | 0 | 1 | 3 | no | fail |
| 12 | `w2-2` | walk | 1110 | 1 | 2 | 0 | 1 | 4 | no | fail |

The judge and the spec agree on all twelve: it fails both negatives and
passes both confirmations. Its known limit is recorded in the contract: the
still-frame judge does not see `w2-2`'s slip (ADR-460, ADR-461), which W7
measures. **No ot11 walk policy has been judged**, because none has passed
the spec; the judge is run on a confirmation evaluation, and walk has none.

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

The reach rows are four consecutive design–train–evaluate–revise rounds,
each motivated by the previous evaluation and each answered by the next;
walk rounds 5–7 are three more. That is P4's evidence of a loop. Rounds 1–3
of walk trained on a trainer whose servo physics disagreed with the
engine's (ADR-465), so what they measured about the reward is weaker than
the rows suggest.

## Every failure

Each item names its receipt.
- **Twenty-one of 25 evaluations failed** (every row above except 5, 6, 11
  and 12), and three of them are void: rows 20 and 21 on a scale digit, row
  25 for R1 on its foot contact margin.
- **Two runs collapsed** and were stopped by `--stop-on-collapse`:
  `r1-clearance` after 569 iterations and `r7-relswing` after 538
  ([`retained/ot11-runs.json`](retained/ot11-runs.json)). Each was
  evaluated on its best or an early checkpoint.
- **Seven runs ended at their wall-clock budget** before or at their last
  iteration (`budget_exhausted`, same receipt). Each was evaluated on a
  checkpoint it had written.
- **One start was refused, and is not an attempt.** `r9-steelfoot`'s
  trainer exited 1 after 52.03 s with no iteration run: a warm start may
  not change what the network reads, and the steel-foot model changed it.
  Its supervisor's status is in the project's
  `runs/r9-steelfoot/training-status.json`. `run_ledger.py` carries it as
  row 15 of the run table with `attempt: false`, so the receipt counts 17
  attempts in 18 runs. The agent re-registered the same task fresh as
  `r10-steelfoot-fresh`.
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
- **R1 is not met.** No walk evaluation has passed a seed: rows 13–25 of
  *Every evaluation* all pass 0 of 10
  ([`retained/ot11-evaluations.json`](retained/ot11-evaluations.json)).
  Walk session 4 is pre-registered and running
  ([`retained/p4-quad-1-s4-preregistration.json`](retained/p4-quad-1-s4-preregistration.json));
  its first two rounds are rows 24 and 25, and its later rounds are not in
  this report yet.
- **No walking gait has been judged.** The judge runs on a confirmation
  evaluation, and walk has none; its scores on a gait that steps are
  unmeasured (*Every judge score*).
- **The judge does not see stepping or slip.** Its manner score gave
  `w2-2` "real steps" on all eighteen calls on seeds 1101 and 1110, while
  W5 and W7 failed them (ADR-460, ADR-461, ADR-463;
  [`retained/judge-w2-2-seed-1101.json`](retained/judge-w2-2-seed-1101.json)).
  That is a recorded limit of the contract, and W5 and W7 are
  authoritative for it.
- **W10 under a gait on the steel-ball feet has not passed on the floor.**
  Round 11's stepping front feet sank to −0.154 to −0.074 hip heights
  ([`retained/p4-quad-1-r12-evaluation.json`](retained/p4-quad-1-r12-evaluation.json)).
  Round 12 passes W10 on every seed, but only because its 3 mm foot contact
  margin makes MuJoCo push on a foot before its sphere reaches the floor.
  Over the settled frames, the median height of a foot that bears load was
  −3.1 to +0.4 mm in rounds 10 and 11, and +1.5 to +3.5 mm on all four
  feet in round 12
  ([`retained/p4-quad-1-r13-evaluation.json`](retained/p4-quad-1-r13-evaluation.json),
  `rest_height`). The pass is not a fix.
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
  12 is void for R1, and so is the agent's next run, `r14-margin15-lift`,
  which cuts the margin to 1.5 mm. Nothing in the product refuses a margin
  yet; the walk session's mechanism rule still permits one, so the void is
  applied when a round is published.
- **The feet sank because the exported contact spring was soft, and that
  is fixed in the product for models exported from now on** (ADR-469).
  Every geom and the environment floor were on MuJoCo's default 0.02 s
  spring, and a soft contact sinks in proportion to the acceleration
  pressing on it. Round 11's policy, on its own MJCF and ten seeds, sank a
  foot 6.18–7.62 mm on that spring and 0.66–2.50 mm at 0.004 s
  ([`retained/p4-quad-1-contact-depth.json`](retained/p4-quad-1-contact-depth.json)).
  Every walk round so far trained and was evaluated on the old spring,
  because a bundle carries the MJCF it was accepted with; a revision
  accepted after ADR-469 gets the new one.
- **Walk rounds 1–3 trained on a trainer whose servo physics disagreed
  with the engine's** (ADR-465). Their evaluations stand, and what they
  say about their rewards is weaker than their rows suggest.
- **A mechanism-changing session's spec check is the actor's, not the
  engine's.** ADR-468 makes the engine refuse a spec whose stated scale
  differs from the model. That the rest of the walk spec block is
  unchanged is checked by the actor after each evaluation, against
  [`retained/walk-spec-block.txt`](retained/walk-spec-block.txt), under the
  session's pre-registered `mechanism_rule`; nothing in the product refuses
  a reworded predicate.
- **The packaged lifecycle gate was owed from ADR-465 to ADR-468** and is
  now paid: the payload was rebuilt and restaged from engine source
  unchanged since ADR-468 (commit `d410b098`), and
  `test_cadexd_lifecycle.py` passed 23 of 23, none skipped, against it on
  2026-10-01. ADR-469's contact spring is an engine change made after it,
  so the gate is owed again until it is rerun on a payload staged from that
  source.
