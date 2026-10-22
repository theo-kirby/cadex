# orun15 B1: sp-sole at 25 and 50, tr-sole's task on leo v04's sprung paw pin

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 2).
Follows `b1-ready.md`, which launched sp-sole.

## The run and the judging

- **The run:** sp-sole is tr-sole's task (19 terms, `flat_feet="sole"` +
  `trail_feet` clip) on leo v04 (revision `e560f053`, task `8f3cb972`,
  model `bce1020d`). The return spring on the paw pin is the one change.
  Cold, 50 iterations, 4096 envs, seed 0, launched 13:41:36.
- **The checkpoints:** `gallop.000025.cxpolicy` (sha256 `46f29e35`,
  landed 14:16, reward per step 15.4 at 23); the final `gallop.cxpolicy`, iteration 49 (sha256 `f81c5889`, done 14:46, 3,794 s, reward per step 29.3 and still climbing; the trainer's `best` is an earlier iteration, so the final one is judged). Both evaluations record `trained_task_sha256` `8f3cb972`.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU (evaluations `sp-sole-25`, `sp-sole-50`); then
  `orun11/summarize.py`, `orun12/legs.py`, `orun13/p2_lag.py`,
  `orun13/spine_foot.py` and `orun14/paw_floor.py`.

```
R=~/cadex-projects/leo/runs/sp-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy sp-sole-25
python3 docs/probes/orun12/legs.py $E/tr-sole-25 $E/sp-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/sp-sole-25
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/sp-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sp-sole-25
```

## What the clip asks for (ladder step 4)

The bundle's `reference` block (`p2_lag.py`'s clip block, `clip_spine.py`):

- **0.70 m at 2.40 Hz = 1.68 m/s**, duty 0.2, 21 samples of 19.8 ms. The
  Froude number is 0.67, under the generator's natural gallop range
  (≥ 2.5). `track_speed` pays up to 2.0 m/s, so policies run past the clip.
- **Pair lag 0.15 of the cycle on both pairs, 62.5 ms**: LH 0, RH 0.85,
  LF 0.35, RF 0.50, rotary. The generator already reaches O3's 40 ms with
  22 ms to spare (`orun13/clip_lag.md`: RH-leading lags reach 0.15 at
  0.70–0.75 m; RH-trailing lags are refused at a knee stop).
- **Heels down 4 of 5 stance samples** (0.8) on each hind leg, from
  `heel_from` 0.2.
- **Flight:** two a cycle, 60 ms each.
- **Spine:** 7° a joint each way, 14.0° peak to peak a joint (28° in all),
  `j_spine2` equal to `j_spine` on every sample.

So the clip asks for more than every criterion's bar on lag and heel, and
for less speed than the policies already run.

## The judged runs against the baselines

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | heel stance height mm | U LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share / s | rotary seeds | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tr-sole-25 (v03) | 0/10 | 0.47 / 0.59 / 0.71 | 0.14 / 0.01 | 0.00 / 0.00 | 5 / 8 | 0.07 / 0.16 | 0/10 (4.8) | 10/10 | −183 / −95 | 378 / 153 | 2.67 / 3.28 | 0.00 / 0.000 | – | 2.60 (j_tail1) | 0.00 | 1.9 |
| **sp-sole-25** | 0/10 | 0.46 / **0.63** / 0.92 | **0.13 / 0.12** (0.114) | 0.02 / 0.00 | 10 / 6 | **0.13 / 0.11** | 0/10 (2.43) | 10/10 | −200 / −190 | 189 / 125 | 3.28 / 2.78 | 0.08 / 0.000 | 3/10 | 2.05 (j_spine) | 0.00 | 2.6 |
| tr-sole-50 (v03) | 0/10 | 2.14 / 2.40 / 2.59 | 0.34 / 0.19 | 0.27 / 0.38 | 3 / 6 | 0.34 / 0.63 | 0/10 (2.08) | 9/10 | +440 / +144 | 896 / 542 | 2.61 / 5.28 | 1.00 / 0.135 | 0/10 | 1.61 (j_hip_r) | 0.00 | 3.2 |
| **sp-sole-50** | 0/10 | 2.08 / **2.18** / 2.29 | **0.41 / 0.26** (0.257) | 0.31 / 0.07 (0.071) | 2 / 11 | **0.32 / 0.29** | 0/10 (1.80) | 10/10 | +247 / −46 (0/10) | 823 / 528 | 2.78 / 4.00 | 1.00 / 0.115 | **0/10** | 1.93 (j_spine) | 0.00 | **4.8** |
| p1-flat-50 (v03) | 0/10 | 1.46 | 0.31 / 0.52 | | | 0.22 / 0.38 | | | | | | | 10/10 | | | |
| g7-hock75 (v02, welded) | | 2.60 | 0.46 / 0.41 (`hock_down` 6/10) | | | – | | | | | | | | | | |
| heel5c-s1 (feline v07) | P1 8/10 | 2.91 | 0.60 / 0.61 | | | (folded) | | | | | | | | | | |

The baselines' rows are the charter's numbers; tr-sole's are from
`docs/probes/orun14/tr-sole.md`. Passing at 50: `completes`, `no_fall`,
`upright` (17.2°), `straight` (14.7°) and `every_stride` 10/10. Failing:
`top_speed`, `hock_down`, `hock_at_toeoff`, `no_tap` and `overreach`.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|
| sp-sole-25 | LH | 0.10 / 0.75 / 0.01 / **0.13** | 0.10 (0.13) | +1.5 | +18.0 | +21.9 / +0.2 | 269 / 752 | 136 | 0.00 |
| sp-sole-25 | RH | 0.11 / 0.78 / 0.00 / **0.11** | 0.11 (0.12) | +1.4 | +13.7 | +26.1 / +1.0 | 308 / 729 | 130 | 0.00 |
| sp-sole-50 | LH | 0.22 / 0.43 / 0.04 / **0.32** | 0.23 (0.41) | +1.9 | +18.2 | +42.0 / −3.2 | 748 / 1061 | 275 | 0.00 |
| sp-sole-50 | RH | 0.07 / 0.58 / 0.07 / **0.29** | 0.07 (0.26) | +3.7 | +26.0 | +46.1 / −1.8 | 775 / 1251 | 316 | 0.00 |

`fold_term.py` on sp-sole-50 (against tr-sole-50):

| leg | U frames: paw down / heel only | U floor pitch ° q1 / med / q3 | U past `paw_flat`'s 15° | `fold` charges U | `fold` on F / R / T |
|---|---|---|---|---|---|
| LH | 383 / 62 (422 / 2) | +18 / +25 / +32 (+18 / +25 / +35) | 0.86 (0.87) | 1.00 | 0.008 / 0.002 / 0.000 |
| RH | 381 / 5 (669 / 86) | +16 / +23 / +29 (+23 / +35 / +44) | 0.79 (0.89) | 1.00 | 0.025 / 0.007 / 0.000 |

- At 25, as on every slow v03 policy, both paws are flat (U 0.13 / 0.11),
  but at 0.63 m/s. The heel share is now even (0.13 / 0.12 against
  tr-sole-25's 0.14 / 0.01).
- At 50 the spring took **RH's fold from 0.63 to 0.29** and its depth
  from a median +35° to +23° toes-up of the floor. **LH's did not move**
  (0.34 → 0.32, +25° median either way). The fold is still a paw down and
  folded past `paw_flat`'s band (79–86% of U frames).
- The pin's p95 rate is 748 / 775 °/s, under O9's 900, with no flapping.
  Its swing p95 rose from 249 / 355 to 275 / 316 °/s. A stiffer spring
  has only 125–150 °/s of p95 margin left.

### Gait and spine at 50

- **Pair lag (`p2_lag.py`):** fore 0.065 of the stride (together on 0.49
  of strides), hind 0.091 (together on 0.44); flight 0.115 s, every
  stride; **rotary on 0/10 seeds** (63 rotary of 66 ordered strides, 123
  tied). The clip asks 0.15 on both pairs. The policy pronks its pairs
  more than tr-sole-50 did (0.209 / 0.278). The fore paws tap: 1.80 fore
  touchdowns per hind stride (`no_tap` 0/10).
- **Spine (`spine_foot.py`):** 46.3° a stride for both joints together (the
  clip asks 28°), 0.00 of frames at a stop, cable gap at most 0.45°.
  At 25: 21.1° a stride, 0.04 at a stop.
- **Drives (O6):** the worst RMS over rated is 1.93 on `j_spine`; the peak
  margin is 0 (a drive reaches peak, as on every orun14 screen).
- **Loops (O9):** the largest push-rod gap is 4.8 mm, over the 2 mm
  bound (tr-sole-50: 3.2 mm).
- **Left and right (O5):** heels 0.41 / 0.26, toe-off 0.31 / 0.07, stride
  823 / 528 mm, touchdowns 2.78 / 4.00 Hz. The right hind still steps
  short and often, as on v03 (`orun14/rh-mirror.md`: the policy's).

## The decision: not kept

**Keep rule** (`b1-ready.md`): U under 0.2 on both legs, at a speed within
tr-sole-50's spread (2.14–2.59 m/s), with heel share no worse than
tr-sole-50's (0.34 / 0.19).

- Speed 2.18 m/s: inside the spread, near its floor (−9% on the median).
- Heel 0.41 / 0.26: better on both legs.
- **U 0.32 / 0.29: fails on both legs.**

The 4 N·mm/deg spring halves the right hind's fold and makes it
shallower. It does not change the left's, and it does not bring either leg
under 0.2. At the pin's median angle at lift (+42 / +46° toes-up of the
metatarsus) the coil returns about 210 N·mm, small against a stance push.
That is as the owner meant it: easy. It gives the fold a cost but does not
undo it. sp-sole also lost the rotary order (0/10) and pronks both pairs.

**B1's first screen is judged**, so B1 has its evidence: bundle, spring,
stand, timing, and sp-sole at 25 and 50 against the four baselines.

## The next lever (ladder step 3, U still high)

The ladder names two, in order:

1. **The spring's rate or preload (O1, kept easy).** The pin's p95 rate is
   748–775 °/s, so a stiffer coil has little room under O9's 900 (v06's
   stiffer sprung pin flapped at 900). A larger preload raises the return
   at every angle without raising the rate. It is a model change: a
   write-up, a 12–15 minute rebuild, clearance and a `leo-v04.1` tag.
2. **The contact-gated `fold` term** (`orun14/fold_term.py`, fd-sole's
   `paw_fold`, never judged). On sp-sole-50 it charges 100% of U frames
   and at most 0.025 a frame on flat or rolling paws. It is a task change
   only.
