# orun15 P1: hk12-sole judged at 25 and 50 (hlk8-sole's task on leo-v04.3, cold)

Verified against source: 2026-10-22. Frozen evidence (orun15, iteration 17).
Follows `leo-v04.3.md` (PAW_K 8 → 12, the write-up, the build, the stop
and keep rules, written before launch) and `hlk8-sole.md` (the same task
on leo-v04.2: the hinds split, the second hind to land, LH, still folded,
U 0.29 / 0.02).

## The run

- hlk8-sole's 21-term task (`hind_lag` w10, `fore_sync_w` 2, `paw_fold`
  w −10) on leo-v04.3, revision `7a69ad4a`; cold (the trainer refuses a
  warm start across a robot change), 50 iterations, 4,096 envs, seed 0,
  `budget_s` 5,500. Launched 00:02:49.
- +25's checkpoint `94a8dd71`, judged on its own bundle.

```
R=~/cadex-projects/leo/runs/hk12-sole/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.000025.cxpolicy hk12-sole-25
python3 docs/probes/orun12/legs.py $E/hlk8-sole-25 $E/hk12-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/hlk8-sole-25 $E/hk12-sole-25
python3 docs/probes/orun13/p2_lag.py $R/gallop-task.json $E/hlk8-sole-25 $E/hk12-sole-25
```

## Judged at 25 (10 seeds, CPU)

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | on-ground F / R / T / U, LH | on-ground F / R / T / U, RH | stride mm LH / RH | flight s | hind lag / together | fore lag / together | rotary seeds (ordered) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-25 (v04.2) | 0/10 | 0.48 / 0.69 / 0.85 | 0.13 / 0.35 | 0.00 / 0.05 | 0.01 / 0.19 | 0.13 / 0.85 / 0.01 / 0.01 | 0.27 / 0.50 / 0.00 / 0.19 | 93 / 131 | 0.000 | 0.333 / 0.00 | 0.204 / 0.00 | 9/10 | 208 / 129 (140 / 99) | 2.13 (j_spine) | 0.00 | 2.0 |
| **hk12-sole-25 (v04.3)** | 0/10 | 0.45 / **0.77** / 0.89 | 0.10 / 0.13 | 0.13 / 0.00 | **0.12 / 0.07** | 0.08 / 0.79 / 0.00 / 0.12 | 0.10 / 0.79 / 0.00 / 0.07 | 143 / 106 | 0.000 | 0.293 / **0.00** | 0.409 / 0.00 | 2/10 (8 seeds < 5 ordered strides) | 261 / 204 (170 / 179) | 2.07 (j_tail1) | 0.00 | 2.3 |

- At 25 a cold run is still a shuffle (0.77 m/s, no flight), as
  hlk8-sole-25 was (0.69). The hinds stay split: together on 0.00 of
  strides, lag 0.293 of the stride. LH leads on 0.54–0.92 of strides.
- U 0.12 / 0.07: both legs under the stop rule's 0.25; RH's share fell
  from hlk8-sole-25's 0.19. Most on-ground frames are the pin's roll (R),
  heel up with the paw flat.
- Rotary counts only 2/10 because 8 seeds have fewer than 5 ordered
  strides (the fores are still loose: lag 0.409); no transverse stride on
  any seed.
- `evaluation.json` checked at source: `top_speed` median 773 mm/s,
  `hock_down` median 0.0731, `straight` 4/10.

**Verdict at 25: runs on.** The stop rule (hinds together on > 0.2 of
strides, or either hind's U ≥ 0.25) does not fire.

## Judged at 50 (`hk12-sole-50`, 10 seeds, CPU)

The run finished at 50 at 01:07 (reward per step 29.4 at 49, still
rising: 26.7 at 44; hlk8-sole 30.5 at 50). Final policy `d0d260e3`,
judged on its own bundle (`7a69ad4a`). The commands are the ones above
with `000025` → `gallop.cxpolicy`, plus `orun14/lead_order.py` and
`orun13/spine_foot.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | **U LH / RH** | on-ground F / R / T / U, LH | on-ground F / R / T / U, RH | heel mm in stance LH / RH | stride mm LH / RH | touch-down Hz LH / RH | flight s | overreach (passes, median mm) | straight (passes, median °) | hind lag / together | fore lag / together | rotary seeds (ordered) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-50 (v04.2) | 0/10 | 2.09 / 2.17 / 2.19 | 0.44 / 0.36 (0.357) | 0.18 / 0.72 (0.178) | 0.29 / 0.02 | 0.22 / 0.46 / 0.01 / 0.29 | 0.34 / 0.63 / 0.00 / 0.02 | 3 / 3 | 868 / 878 | 2.44 / 2.44 | 0.140 | 8/10, +8 | 10/10, 11.9 | 0.101 / 0.10 | – | 10/10 | 760 / 310 (363 / 156) | 1.92 (j_spine) | 0.00 | 4.0 |
| **hk12-sole-50 (v04.3)** | 0/10 | 1.87 / **1.91** / 1.98 | 0.51 / **0.20** (0.204) | 0.28 / 0.36 (0.271) | **0.07 / 0.02** | 0.47 / 0.45 / 0.02 / 0.07 | 0.20 / 0.60 / 0.18 / 0.02 | 1 / 6 | 789 / **505** | 2.67 / **3.89** | 0.140 | 0/10, −127 | **0/10, 28.0** | 0.381 / 0.05 | 0.270 / 0.08 | 9/10 | 781 / 468 (424 / 373) | 1.69 (j_spine) | 0.00 | 4.0 |

- **The fold is out on both hinds.** RH lands first on every ordered
  stride (`lead_order.py`: 83 rotary, RH then LH, LF then RF, as the
  clip), so LH is the second hind, and its U fell **0.29 → 0.07**; RH's
  stays 0.02. Floor pitch in stance +0.9 / +2.2°; heel-down frames flat
  0.92 / 1.00 (`spine_foot.py`). No paw lifts toes-up of the floor.
- **The cost is on RH.** RH now steps short and often: 3.89 touch-downs a
  second against LH's 2.67, stride 505 mm against 789, 35 toe-offs
  against 24, taps 0.56 a step. Its heel share fell 0.36 → **0.20**,
  and it stands on its toes on 0.18 of its on-ground frames. This is
  orun14's RH pattern (`rh-mirror.md`: the policy's, by mirror test).
  With the hinds stepping unequally the cat yaws: `straight` 10/10 →
  **0/10** (median 28°), and `overreach` 8/10 → 0/10 (RH −127 mm).
- Speed 2.17 → **1.91 m/s**; flight 0.140 s on every stride.
- Hinds split on every seed: lag 0.381 of the stride (0.136–0.429 per
  seed, at 2.38 Hz ≥ 57 ms), together on 0.05.
- SP: spine 30.8° a stride (both joints), 0.00 of the time at a stop,
  cable gap max 0.35° (O9's 1° holds).
- O6: worst drive `j_spine` 1.69 × rated RMS, peak margin 0.00. O9: loop
  gap max 4.0 mm (the front push-rod loop, as on every fast v04 policy);
  pins p95 781 / 468 °/s, swing 424 / 373, none over 900 in swing, no
  flapping.
- `evaluation.json` checked at source: `top_speed` median 1,913 mm/s,
  `hock_down` median 0.204, `hock_at_toeoff` 0.271, `straight` 0/10
  (median 28.0°), policy `d0d260e3`, revision `7a69ad4a`.

## Verdict at 50

| keep clause (`leo-v04.3.md`) | needs | hk12-sole-50 | |
|---|---|---|---|
| second hind's U (LH) | < 0.2 | 0.07 | pass |
| first hind's U (RH) | ≤ 0.05 | 0.02 | pass |
| speed | ≥ 2.0 m/s | 1.91 | **fail** |
| hinds ≥ 40 ms apart | ≥ 5 seeds | 10 | pass |
| heel share each leg | ≥ 0.3 | 0.51 / 0.20 | **fail (RH)** |
| pins p95, no flapping | < 900 °/s | 781 / 468, none | pass |
| heel at toe-off (reported) | – | 0.28 / 0.36 (hlk8-sole-50 0.18 / 0.72) | |

**The screen moved the measure the change was for** (the second hind's
U, 0.29 → 0.07, the first split-gait policy with both hinds under 0.2),
**but its keep rule fails on two clauses**: speed (1.91 m/s, 12% under
hlk8-sole-50) and RH's heel share (0.20). hk12-sole is not kept as a
policy. leo-v04.3 is **not yet decided**: one cold seed cannot tell the
spring's effect from the seed's, and RH's short stepping is a habit
orun14 traced to the policy, not the hardware. It stays the project's
revision while a replication judges it.

## The next screen: hk12-s1 (f30-sole stopped)

- **f30-sole** (hk12-sole's task with `paw_fold` −10 → −30, queued
  00:39:33 and built as revision `68214869`, its model byte-identical to
  hk12-sole's and its task differing only in that weight) launched at
  01:08:12 and was **stopped at once** (`loop.request_stop`, state
  `stopped`): it was the fallback for a fold that hk12-sole-50 no longer
  has. Its scoring stays as evidence: `orun14/fold_term.py` on
  hlk8-sole-50 charges LH's U frames 0.395 a frame (floor pitch
  +13 / +16 / +19°), its flat frames 0.030, its rolling ones 0.007; at
  −10 a folded stance costs about 2 a step against `track_speed`'s 20,
  at −30 about 6.
- **hk12-s1:** hk12-sole's bundle rebuilt from the same script
  (`~/orun15-queue/orun15-v043.py`), seed 1, cold, 50 iterations, 4,096
  envs, `budget_s` 5,500, queued 01:09:25 behind f30-sole
  (`~/orun15-queue/hk12-s1.log`). It asks whether U < 0.2 on both hinds
  is the spring's or seed 0's, and whether RH's short steps come with it.
  - **Stop at 25** if either hind's U is ≥ 0.25 or the hinds tie on
    > 0.2 of strides (hk12-sole-25: 0.12 / 0.07, 0.00).
  - **At 50, leo-v04.3 is kept** if both hinds' U is under 0.2 again
    (seed 0 and seed 1 both); then the open clauses are RH's heel share
    and speed, worked on the policy side. If seed 1 folds (second hind's
    U ≥ 0.2), hk12-sole-50 was the seed's and v04.3 is not kept.
- **Launched:** the rebuild accepted revision `7a69ad4a` again (01:13:03,
  hk12-sole's, so the bundle is the same), and hk12-s1 launched at
  01:13:06.
