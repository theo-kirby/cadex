# orun15 P2: a fore-pair lag term, scored per step before training

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 10).
Follows `hl-sole.md`: with `hind_lag` (w10) the hinds split 40 ms on
10/10 seeds, and the fore pair closed (LF +120 / RF +140 ms after LH, in
one frame on 0.54 of strides). P2 needs both pairs at least 40 ms apart.

## The question

What pays for the fore order now, and what would a fore lag term of
`hind_lag`'s form pay per step on the judged traces (O7)?

## What already pays it

- `track_contact` (w10 over four paws): about 0.7 a step on each pair's
  order, as `clip-read.md` found for the hinds.
- **`fore_sync` (w2), `1 - abs(cfl_down - cfr_down)`**: an orun11 term
  (owner, 2026-10-18: "the fore pair as near together as the hind"). It
  pays the two fore paws for being in the same state, so it pays a tie
  directly. The clip's own fore pattern (LF down samples 8–11, RF 11–14)
  agrees on 15 of 21 samples and would earn 2 × 15/21 = **1.43** a step;
  a fully tied fore pair earns 2.0. hl-sole-50 earns **1.65**, more than
  the clip: following the clip's fore split would cost it 0.22 a step.

## The candidate and the tool

`fore_lag` = `|rlf − rrf| · (1 − |(clf − crf) − (rlf − rrf)|)`, the same
form as `hind_lag` on the fore pair: +1 split the clip's way (RF 3
samples, ~60 ms, after LF), 0 together, −1 the other way; 0 wherever the
clip has both fores in one state. The clip scores 6/21 = 0.286 a step.

`lag_term.py` now scores it beside `hind_lag`, with the fore pair's
RF-after-LF touchdown lag and tied share per seed:

```
L=~/cadex-projects/leo; E=$L/evaluations; R=$L/runs/hl-sole/train
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/lag_term.py $R/gallop-task.json \
    $R/cat_model-model.xml $E/hl-sole-50 $E/sf-sole-50 $E/hl-sole-25 $E/sp-sole-50
```

## What it reads (10 seeds each, after the first second)

| evaluation | m/s | `fore_lag` a step (clip 0.286) | `fore_sync` (w2; clip 1.43) | RF after LF ms (seed medians) | fores together (seeds) | r(`fore_lag`, fores together) | `hind_lag` a step |
|---|---|---|---|---|---|---|---|
| **hl-sole-50** | 2.12 | **+0.030** (−0.004–0.071) | **1.65** | +20 on 9, +10 on 1 | 0.29–0.61 | +0.52 | +0.222 |
| sf-sole-50 | 2.37 | +0.064 (0.053–0.078) | 1.45 | +40 on 7, +20 on 3 | 0.21–0.38 | +0.21 | +0.059 |
| sp-sole-50 | 2.18 | +0.115 (0.084–0.184) | 1.49 | +0 on 3, +20 on 7 | 0.36–0.54 | −0.53 | +0.104 |
| hl-sole-25 | 0.76 | +0.138 (0.048–0.157) | 1.05 | +0 to +60 | 0.07–0.42 | +0.12 | +0.240 |

- **Every fast v04 policy takes a tenth to two fifths of what the clip
  would earn on the fore order**, and hl-sole-50, the one with its hinds
  split, takes the least (0.030, a tenth). At weight 10 the gap to the
  clip is 2.6 a step on hl-sole-50, about `hind_lag`'s 2.2 on sf-sole-50
  that split the hinds in hl-sole.
- **`fore_sync` pays the tie that P2 forbids.** It is the only term on the
  fore pair that the fast policies earn more of than the clip, and
  hl-sole-50 earns the most of it (1.65), as its fore pair closed.
- **Per seed it does not separate a lagged seed from a tied one** on
  hl-sole-50 (r +0.52, wrong-signed) or sf-sole-50 (+0.21): within a
  policy the seeds spread over 0.00–0.08 a step, so the per-seed spread is
  the clip's phase, not the tie. Only sp-sole-50, whose fores split most,
  reads the right way (−0.53). `hind_lag` read −0.31 on sf-sole-50 before
  it split the hinds in training, so a weak per-seed signal did not stop
  that term working; between policies, `fore_lag` ranks the most tied
  (hl-sole-50) lowest.

## The screen: fl-sole (queued this iteration)

- hlk8-sole's 21-term task (hind_lag w10 on leo-v04.2) with **`fore_sync`
  off** (`--build-param fore_sync_w=0`) and **`fore_lag` added** (w10, a
  literal: the script is at the 64-parameter cap). Both act on the fore
  order, so they are one lever: the pay for a fore tie is removed and a
  pay for the clip's fore split is added. The model is v04.2's, so
  hlk8-sole is the like-for-like comparison.
- Script `~/orun15-queue/orun15-fl.py` is `orun15-hlk8.py` plus the
  `fore_lag` block (9 lines) and nothing else. Cold, 50 iterations, 4,096
  envs, seed 0, `budget_s` 4,600 (hlk8-sole's), queued at 19:37 behind
  hlk8-sole (`queue_run.py --after hlk8-sole --build`, its own
  `MemoryMax=30G` scope, `~/orun15-queue/fl-sole.log`).
- `fore_sync_w=0` is stored in the project's parameters by the build, so
  later builds carry it until a build sets it back. `fore_sync` was the
  owner's orun11 ask; O3 and P2 (orun15) now ask for the fore pair at
  least 40 ms apart, which it pays against.
- **Keep rule**, judged at 25 and 50 against hlk8-sole at the same
  checkpoint: the fore pair's median RF-after-LF lag ≥ 40 ms on ≥ 5 of 10
  seeds with rotary order on ≥ 5, the hinds still ≥ 40 ms apart on ≥ 5,
  U no worse than hlk8-sole's + 0.03 on each leg, speed ≥ 90% of
  hlk8-sole's. **Stop at +25** if the fores land in one frame on more
  than hlk8-sole-25's share.

## Built

- `queue_run.py` set `fore_sync_w=0` (project commit `2f7d46a`, revision
  `e9987cce`, 20:10) and then the script (project commit `3515594`,
  accepted revision **`1732bef8`**, 20:19:12). The build ran while
  hlk8-sole trained, so it took 17 minutes against v04.2's 3.6.
- Every verdict in the attempt's `result.json` equals hlk8-sole's revision
  `1412f4af` (142 verdict fields, 0 differ). The bundled
  `cat_model-model.xml` is byte-identical to hlk8-sole's (model
  `b2bb0efe`, leo-v04.2), so no clearance pass is needed. The
  `gallop-task.json` differs only in its reward list: `fore_sync` (w2)
  out, `fore_lag` (w10) in, 21 terms each.
- fl-sole launches from the queue when hlk8-sole frees the lock (about
  21:10). Its queue log is `~/orun15-queue/fl-sole.log`; the launch line
  goes to an unlinked copy, so read `runs/fl-sole/registration.json` for
  it.

## Timed (iteration 11)

- fl-sole launched from the queue at 21:07:12 when hlk8-sole finished;
  its tenth iteration ended at 21:22:47, 15.6 minutes in (about 93 s an
  iteration with start-up, hlk8-sole's 16.8). The trainer's ETA then was
  3,422 s more, so about 4,350 s in all, inside the 4,600 s budget; +25
  falls near 21:45 and 50 near 22:20.
- hlk8-sole-50, its like-for-like, is judged in `hlk8-sole.md`: U 0.29 /
  0.02, hinds 40 ms apart on 10/10, fore pair 40 ms apart at the median
  and in one frame on 0.20 of strides, LF tapping on 0.50 of its steps
  (`no-tap.md`), 2.17 m/s. fl-sole's 25 and 50 add LF's and RF's taps a
  step (`fore_tap.py`) to the keep rule's readings.
