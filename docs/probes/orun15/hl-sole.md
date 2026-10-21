# orun15 P2: hl-sole judged at 25 and 50 (the hind-lag term, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iterations 8 and 9).
Follows `lag-term.md`, which queued it.

## The question

Does `hind_lag` (w10) split the hind pair the clip's way, where every
fast v04 policy lands the hinds within 0–20 ms? The critic's rule: stop
at 25 if the hinds still land within 20 ms.

## The run

- sf-sole's task plus `hind_lag`, leo v04 `dd9d802f`, model `bce1020d`, 21
  terms; cold, 50 iterations, 4,096 envs, seed 0, `budget_s` 4,500.
  Launched 17:51:36. Iterations 13 → 25 took 75 s each (the first ten
  ~85 s). Reward per step 20.2 at 0, 12.9 at 13, 15.0 at 25.
- +25's checkpoint `076f05d4`. **Not stopped:** the hinds are split (below).

## Judged at 25 (`hl-sole-25`, 10 seeds, CPU)

```
R=~/cadex-projects/leo/runs/hl-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy hl-sole-25
python3 docs/probes/orun12/legs.py $E/sf-sole-50 $E/sf-sole-25 $E/hl-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sf-sole-50 $E/hl-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/hl-sole-25   # and $E/sf-sole-25
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/hl-sole-25
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/lag_term.py $R/train/gallop-task.json \
    $R/train/cat_model-model.xml $E/hl-sole-25 $E/sf-sole-25
```

The like-for-like comparison is sf-sole at the same cold checkpoint (25);
sf-sole-50 is the fast reference.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | **U LH / RH** | stride mm LH / RH | flight s | overreach (passes, median mm) | **hind lag (share) / hinds together** | fore lag / together | **rotary seeds** | `hind_lag` a step (clip 0.282) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 | 0.29 / 0.29 | 981 / 964 | 0.180 | 10/10, +81 | 0.043* / 0.83* | 0.200* | 0/10 | 0.059 | 1.86 (j_spine) | 0.00 | 3.7 |
| sf-sole-25 | 0/10 | 0.83 / 0.85 / 1.09 | 0.00 / 0.04 (0.003) | 0.00 / 0.00 | – | 245 / 192 | 0.000 | 0/10, −309 | 0.150 / 0.27 | 0.381 / 0.00 | 1/10 | 0.098 | 1.56 (j_wrist_l) | 0.00 | 2.2 |
| **hl-sole-25** | 0/10 | 0.51 / 0.76 / 0.85 | 0.02 / 0.23 (0.017) | 0.00 / 0.07 | **0.05 / 0.19** | 122 / 115 | 0.000 | 0/10, −206 | **0.405 / 0.00** | 0.143 / 0.19 | **9/10** | **0.240** | 2.09 (j_spine) | 0.00 | 2.0 |

\* from `sfw-sole.md` / `lag-term.md`.

- **The term moves its measure.** The hinds land together on 0.00 of
  strides (sf-sole-25: 0.27), the hind lag is 0.405 of the stride, RH
  leading on 60–90% of strides, and 9 of 10 seeds read rotary (all of
  them RH-first; seed 1010 has no ordered stride). The policy takes 0.240
  of the clip's 0.282 a step, 2.4× sf-sole-25 at the same checkpoint.
  `legs.py`: 119 of 131 strides rotary, 25 tied.
- **But it is a cold policy at 25, not a gallop:** 0.76 m/s, strides of
  ~120 mm, flight on 0.05 of strides with no measured flight time, every
  hind spec at its floor. Every cold v04 screen is this slow at 25
  (sf-sole-25 0.85, sp-sole-25 0.63 m/s); sf-sole reached 2.37 only by 50.
  So 25 cannot test the keep rule's speed or U, only whether the term
  splits the hinds, and it does.
- **U 0.05 / 0.19** is a slow shuffle's (pin rate p95 300 / 171 °/s), and
  LH stands on its toes (heel share 0.02, heel 16 mm up; RH 0.23, 4 mm).
  It says nothing yet about the fold at speed.
- `spine_foot.py`: the spine runs 27.2° a stride (both joints), 0.13 of
  the time at a stop; cable gap max 0.24° (O9's 1° holds). Heel-down
  frames flat 1.00 / 0.92.
- O6: worst drive `j_spine` 2.09 × rated RMS, peak margin 0.00. O9: loop
  gap max 2.0 mm, at the 2 mm line.

## Verdict at 25

The critic's stop condition (hinds within 20 ms) is not met: the hinds
are as split as the clip asks, and more rotary than any v04 policy so far.
**hl-sole runs on to 50**, where the keep rule (`lag-term.md`) applies:
hind lag ≥ 40 ms on ≥ 5 seeds with rotary order, U ≤ 0.29 each leg,
≥ 2.13 m/s. The risk to watch at 50 is that the split holds only at a
shuffle's speed, as sf-sole-25's 1/10 rotary became sf-sole-50's 0/10.
k8-sole (`leo-v04.2.md`) is queued behind it.

## Judged at 50 (`hl-sole-50`, 10 seeds, CPU)

The run finished at 50 in 3,790 s (76 s an iteration), reward per step
29.2. The final policy `gallop.cxpolicy` is `849aa2e7` (the trainer's
`best` is `4394c710`); the evaluation is on revision `dd9d802f`. The
commands are the ones above with `000050` → `gallop.cxpolicy`, and
`clip_read.py` on sf-sole-50 and hl-sole-50 for the touchdown lag in ms.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | **U LH / RH** | stride mm LH / RH | touchdown Hz LH / RH | flight s | overreach (passes, median mm) | **RH after LH ms (pooled q1 / q3)** | **hinds in one frame** | fore LF / RF after LH ms | **rotary seeds** | `hind_lag` a step (clip 0.282) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 | 0.29 / 0.29 | 981 / 964 | 2.50 / 2.56 | 0.180 | 10/10, +81 | +0 (−20 / +0) | 0.42 | +40 / +160 | 0/10 | 0.059 | 1.86 (j_spine) | 0.00 | 3.7 |
| **hl-sole-50** | 0/10 | 2.08 / 2.12 / 2.19 | 0.49 / 0.18 (0.183) | 0.43 / 0.33 | **0.31 / 0.01** | 867 / 770 | 2.61 / 3.00 | 0.140 | 7/10, +7 | **−40 (−60 / −40)** | **0.02** | +120 / +140 | **9/10** | **0.222** | 1.76 (j_spine) | 0.00 | 3.5 |

- **The split holds at speed.** Every seed's median RH touchdown is 40 ms
  before LH's (sf-sole-50: 0 to −20 ms on every seed), RH lands in LH's
  20 ms frame on 4 of 215 LH touchdowns (sf-sole-50: 91 of 218), and 9 of
  10 seeds read rotary, all RH first (`p2_lag.py`: hind lag 0.103 of the
  stride, 0.13 of strides tied; `legs.py`: 129 of 129 ordered strides
  rotary). The policy takes 0.222 a step of the clip's 0.282 (sf-sole-50
  0.059). 40 ms is O3's floor, two 20 ms frames: the clip asks 62.
- **RH's fold is gone; LH's is not.** RH's U fell from 0.29 to 0.01 (roll
  ≥ 3 frames 0.06, against 0.44; pin p95 272 °/s), the leg that the coil,
  the 30° preload, `paw_fold` and the warm run never moved. Split from LH,
  RH stands on a pad with its heel near the floor (heel 6 mm up, sole
  8 mm toes-low) for a 0.18 heel share, and taps on 0.61 of its strides
  (3.00 Hz against LH's 2.61). LH, now the trailing hind, takes the heel
  (0.49, 1 mm) and keeps the fold (U 0.31, roll ≥ 3 frames 0.48).
- **The fore pair has closed instead:** LF +120, RF +140 ms after LH, in
  one frame on 0.54 of strides (`p2_lag.py` fore lag 0.049); sf-sole-50's
  fore pair was 120 ms apart. P2 needs both pairs at 40 ms.
- Speed 2.12 m/s, 10.5% under sf-sole-50; flight 0.140 s on every stride;
  overreach 7 of 10 at +7 mm median (sf-sole-50 10/10, +81).
- `spine_foot.py`: 34.2° a stride (both joints), 0.00 of the time at a
  stop, cable gap max 0.41° (O9's 1° holds); heel-down frames flat
  0.96 / 1.00.
- O6: worst drive `j_spine` 1.76 × rated RMS, peak margin 0.00. O9: loop
  gap max 3.5 mm, over the 2 mm line as on every fast v04 policy; pins
  under 900 °/s at p95 (734 / 272) with no flapping swing.

## Verdict at 50

Against `lag-term.md`'s keep rule:

| clause | needs | hl-sole-50 | |
|---|---|---|---|
| hind lag | ≥ 40 ms on ≥ 5 seeds, rotary | 40 ms on 10/10, rotary 9/10 | passes |
| U | ≤ 0.29 each leg | 0.31 / 0.01 | LH misses by 0.02 |
| speed | ≥ 2.13 m/s | 2.12 | misses by 0.01 |

**The policy is not kept**: it misses two clauses, if only narrowly. **The
term is kept** (O7): it is the only lever on v04 that has moved the hind
lag, from 0 to 40 ms at 2.1 m/s, and with it RH's fold. What it leaves:
LH's fold (0.31), the fore pair now tied, RH's taps, and 0.25 m/s.

Next, as the critic asked when the split holds: **hlk8-sole**, hl-sole's
21-term task on leo-v04.2 (`PAW_K` 8, `leo-v04.2.md`), cold, 50
iterations, 4,096 envs, seed 0, `budget_s` 4,600 (hl-sole's 3,790 s plus
20%). Script `orun15-hlk8.py` is `orun15-v042.py` plus the `hind_lag`
block, with no other change. It is queued at 18:58 behind k8-sole
(`queue_run.py --after k8-sole --build`, its own `MemoryMax=30G` scope),
so it builds while k8-sole trains and launches when k8-sole frees the
lock. It is judged against hl-sole-50 and k8-sole-50. **Keep** if LH's U
falls ≥ 0.05 with RH's U ≤ 0.1, the hind split ≥ 40 ms on ≥ 5 seeds, and
≥ 2.0 m/s. **Stop at +25** if the hinds land within 20 ms there.

The build landed at 19:02 as revision `1412f4af` (project commit
`e11bd4f`); its script diff against leo-v04.2's (`6040c4f`) is the 9-line
`hind_lag` block and nothing else. k8-sole is training on `568d38a9`
(launched 18:56:12).
