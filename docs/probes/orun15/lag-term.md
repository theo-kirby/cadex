# orun15 P2: a hind-pair lag term, scored per step before training

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 7).
Follows `clip-read.md` (the clip asks RH 62.5 ms before LH; the fast
policies land the hinds within 0–20 ms) and `rh-mirror.md` (the handed
half-bound is the policy's, not the model's).

## The question

Only `track_contact` (w10, over four paws) pays for the hind order, and
`clip-read.md` put its stake at about 0.7 of ~30 a step, by arithmetic on
the clip. Before training a term on the hind lag (O7), what does one pay
per step on a judged trace, and does it tell a lagged seed from a tied
one?

## The tool

`docs/probes/orun15/lag_term.py`, on the evaluations' seed traces and the
bundle's `tracking` block:

```
L=~/cadex-projects/leo
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/lag_term.py \
    $L/runs/sf-sole/train/gallop-task.json $L/runs/sf-sole/train/cat_model-model.xml \
    $L/evaluations/sf-sole-50 $L/evaluations/sp-sole-50
```

- **The clip's clock.** The task starts each episode at a random clip
  sample (`tracking.start` `random`, ADR-709), not recorded in the
  evaluation. The probe recovers it from the first solver frame's joint
  angles against `tracking.reset_qpos`: an exact match (error 0) on all 20
  seeds, the next row 129–591 deg² away. Each step's reward then reads the
  clip at `t / period + origin / 21`, as `cadex_train.tracking_vector`
  does one step on, with `ref_*_down` thresholded at 0.5.
- **The policy's contacts:** each paw body's collision geoms within
  `CadexEvaluation.STANCE_MM` (1 mm) of the floor, the evaluator's stance
  rule standing in for the trainer's contact flags. Its "together" share
  (RH's touchdown within 20 ms of LH's) runs higher than `clip-read.md`'s
  from the engine's `touchdowns_s` (sf-sole-50: 0.56 against 0.42); the
  term's score does not depend on it.
- **The candidate**, `hind_lag`:
  `|rl − rr| · (1 − |(cl − cr) − (rl − rr)|)`, `r` the clip's hind downs,
  `c` the policy's. It is 0 wherever the clip has both hinds in one state,
  +1 where the policy splits them the clip's way, 0 where it holds them
  together, −1 where it splits them the other way. The clip itself scores
  0.282 a step (6 of 21 samples).

## What it reads (10 seeds each, after the first second)

| evaluation | hind_lag a step | clip | `track_contact` hind half (w10) | `fore_sync` (w2) | RH after LH ms (seed medians) | together share (seeds) | r(hind_lag, together) |
|---|---|---|---|---|---|---|---|
| sp-sole-50 | **+0.104** (0.086–0.126) | 0.282 | 4.29 | 1.49 | −20 on 9, +0 on 1 | 0.36–0.72 | **−0.69** |
| sf-sole-50 | **+0.059** (0.044–0.084) | 0.282 | 4.22 | 1.45 | −20 / −10 / +0 | 0.36–0.68 | −0.31 |

- **The policies take a fifth to a third of what the clip would earn.**
  At weight 10 the gap to the clip is 1.8–2.2 a step, about three times
  the 0.7 `track_contact` puts on the hind order, and about 7% of a
  ~31 reward per step: a stake the policy notices, not one that
  outweighs `track_speed` (w20, ~20 a step at 2 m/s).
- **It separates the seeds the right way.** The more often a seed lands
  RH with LH, the less it scores (r −0.69 on sp-sole-50, −0.31 on
  sf-sole-50, whose tied shares spread less). sp-sole-50, which leads RH
  by 20 ms on 9 seeds, scores 1.8× sf-sole-50, which leads by 0–20.
- **It pays nothing for the fore pair** and nothing outside the clip's
  six lag samples, so it cannot pay a pronk or charge the stance terms.

## The screen: hl-sole (queued this iteration)

- sf-sole's 20-term task plus `hind_lag` (w10, a literal: the script is at
  the 64-parameter cap), on leo v04 (preload 10°), **cold**, 50
  iterations, 4096 envs, seed 0, `budget_s` 4,500 (50 × ~70 s + start-up,
  +20%). The script is `script.py` at `b32a6ace` with the term appended
  after `fore_sync`.
- Queued through `orun13/queue_run.py --after sfw-sole --build`, in its own
  `systemd-run --user --scope -p MemoryMax=30G`: built leo revision
  `dd9d802f` at 17:33 (project commit `c55d850`; bundle 21 terms, model
  `bce1020d`, v04's own, so the term is the one change), launched 17:51:36
  when sfw-sole was stopped. Timed: iteration 9 at 855 s, trainer ETA
  3,420 s more (about 85 s an iteration in the first ten, 4,275 s in all,
  inside the 4,500 s budget; sf-sole's 50 took 3,801 s). The cold curve
  tracks sf-sole's (20.2 / 13.6 a step at 0 / 9, against 20.3 / 13.7).
- **Judged at 25 and 50** with `p2_lag.py`, `clip_read.py`, `lag_term.py`
  and `paw_floor.py` against sf-sole-50. **Keep rule:** the hind pair's
  median lag at least 40 ms (O3) on at least 5 of 10 seeds with rotary
  order, U no worse than sf-sole-50's 0.29 on each leg, speed no lower than
  2.13 m/s (10% under 2.37). If the hinds still land within 20 ms at 50,
  the term is a dead end at this weight.
