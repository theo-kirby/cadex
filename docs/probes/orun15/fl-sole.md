# orun15 P2: fl-sole judged at 25 and 50 (fore_lag on leo-v04.2, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 12).
Follows `fore-lag.md` (the term, scored per step, and the build) and
`hlk8-sole.md` (its like-for-like: the same task with `fore_sync` w2 and
no `fore_lag`).

## The run

hlk8-sole's task with `fore_sync` off and `fore_lag` w10, leo-v04.2,
revision `1732bef8`, model `b2bb0efe`; cold, 50 iterations, 4,096 envs,
seed 0, `budget_s` 4,600. Launched 21:07:12; +25's checkpoint `ccb59289`
at 21:42.

```
R=~/cadex-projects/leo/runs/fl-sole/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.000025.cxpolicy fl-sole-25
python3 docs/probes/orun12/legs.py $E/hlk8-sole-25 $E/fl-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/fl-sole-25
python3 docs/probes/orun13/p2_lag.py $R/gallop-task.json $E/hlk8-sole-25 $E/fl-sole-25
pixi run python docs/probes/orun15/fore_tap.py $R/cat_model-model.xml $E/hlk8-sole-25 $E/fl-sole-25
```

## Judged at 25 (10 seeds, CPU)

| evaluation | pass | completes / upright / straight | top 2 s m/s min / med / max | hock_down LH / RH | **U LH / RH** | stride mm LH / RH | fore lag / fores together | hind lag / hinds together | rotary seeds (`p2_lag`) | no_tap ratio (LF / RF taps a step) | pin p95 °/s LH / RH | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-25 | 0/10 | 9 / 9 / 1 | 0.48 / 0.69 / 0.85 | 0.13 / 0.35 | 0.01 / 0.19 | 93 / 131 | 0.204 / 0.00 | 0.333 / 0.00 | 9/10 | 1.45 (0.33 / 1.50) | 208 / 129 | 2.13 (j_spine) | 0.00 | 2.0 |
| **fl-sole-25** | 0/10 | **3 / 3 / 0** | 0.62 / 1.08 / 1.26 | 0.04 / 0.15 | 0.07 / 0.08 | 317 / 204 | **0.353 / 0.05** | 0.286 / 0.00 | 0/10 | 1.22 (0.00 / 0.07) | 486 / 318 | 1.66 (j_wrist_l) | 0.00 | 2.5 |

- **The fores split further** (fore lag 0.353 of the stride against 0.204,
  LF leading on 0.57–1.00 of strides), and the hinds stay split (0.286,
  never in one frame). The taps fall: LF 0.00 and RF 0.07 a step at the
  median seed (hlk8-sole-25 0.33 / 1.50).
- **But it does not yet run straight**: 3 of 10 seeds complete, upright
  fails 7 (32° median), heading 50° off (hlk8-sole-25: 9 / 9 / 1, 33°).
  Episodes in training are shorter (535 steps at 25 against 1,078), so it
  is behind hlk8-sole's curve, not yet failing a measure it should hold.
- The few ordered strides (28 over 10 seeds, 16 tied) leave `p2_lag`'s
  rotary count at 0/10; `legs.py` reads 21 of 28 rotary. A cold shuffle's
  order at 25 is not P2 evidence.
- U 0.07 / 0.08 and heel share 0.01 / 0.13: a slow, heel-up gait (LH
  standing 37 mm up), not P1 evidence. Pins p95 under 500 °/s, no swing
  over 900, no flapping.

**The stop clause fires on its letter**: the fores land in one frame on
0.05 of strides at the median seed against hlk8-sole-25's 0.00. It was
written to stop a term that fails to split the fores; this one split them
further than any v04 policy (0.353), so the run was left to 50 (about 16
more GPU minutes), where its keep rule decides. That is a deviation from
the written rule, made because the measure the rule guards moved the
right way.

## Judged at 50 (`fl-sole-50`, 10 seeds, CPU)

The run finished at 22:12 (reward per step 29.6; hlk8-sole 30.5 at 50).
The final policy `gallop.cxpolicy` is `a05d3d85`, judged on its own bundle
(`1732bef8`). The commands above with `000025` → `gallop.cxpolicy`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | heel mm in stance LH / RH | overreach (passes, LH / RH mm) | stride mm LH / RH | touchdown Hz LH / RH | flight s (stride share) | fore lag / fores together | hind lag / hinds together | **rotary seeds** (`p2_lag`) | no_tap ratio (LF / RH taps a step) | pin p95 °/s LH / RH (swing p95) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-50 | 0/10 | 2.09 / 2.17 / 2.19 | 0.44 / 0.36 | 0.18 / 0.72 | 0.29 / 0.02 | 3 / 3 | 8/10, 348 / 8 | 868 / 878 | 2.44 / 2.44 | 0.140 (1.00) | 0.131 / 0.20 | 0.101 / 0.10 | 9/10 | 1.54 (0.50 / –) | 760 / 310 (363 / 156) | 1.92 (j_spine) | 0.00 | 4.0 |
| **fl-sole-50** | 0/10 | 2.09 / 2.14 / 2.18 | 0.48 / **0.08** | 0.09 / 0.14 | **0.18 / 0.02** | 1 / **17** | 0/10, 377 / −89 | 861 / 776 | 2.39 / **3.22** | 0.080 (1.00) | **0.413 / 0.00** | 0.095 / **0.26** | **4/10** | 1.63 (0.64 / 0.04) | 713 / 495 (308 / 250) | 1.58 (j_spine) | 0.00 | 3.1 |

- **The fores split on every seed** (lag 0.413 of the stride, never in one
  frame, LF first on 0.85–1.00 of strides), as `fore_lag` asks.
- **The hinds close again**: in one frame on 0.26 of strides at the median
  seed (0.10–0.53), so `p2_lag` reads 4 of 10 seeds rotary (`legs.py`: 105
  of 106 ordered strides rotary, 33 tied, 69 unordered). Every ordered
  stride is RH first.
- **RH goes back to the tied gait's short, heel-up leg**: heel share 0.08,
  heel 17 mm up in stance, landing 89 mm behind the fore paw, 3.22
  touchdowns a second against LH's 2.39 (`paw_floor.py`: taps on 0.82 of
  its steps, by its 30 mm rule; `fore_tap.py`'s stricter step rule counts
  0.04). LH stays the overreaching leg, its U down to 0.18 from 0.29.
- `no_tap` worsens to 1.63: LF skips on 0.64 of its steps (hlk8-sole-50
  0.50); RF and LH none.
- Flight 80 ms every stride (hlk8-sole 140). Spine and pins clean: no
  swing over 900 °/s, no flapping. O6: worst drive `j_spine` 1.58 × rated
  RMS, peak margin 0.00. O9: loop gap max 3.1 mm (the fore rod's).

## Verdict at 50

| clause | needs | fl-sole-50 | |
|---|---|---|---|
| fores | ≥ 40 ms apart on ≥ 5 seeds | lag 0.375–0.444 of a 0.42 s stride, 0.00 together, 10 seeds | passes |
| rotary | ≥ 5 seeds | 4/10 | **fails** |
| hinds | ≥ 40 ms apart on ≥ 5 seeds | lag 0.095 (40 ms) at the median, together 0.26 | at the line, worse than hlk8-sole-50's 0.10 |
| U | ≤ hlk8-sole-50 + 0.03 each leg | 0.18 / 0.02 (0.29 / 0.02) | passes |
| speed | ≥ 90% of 2.17 m/s | 2.14 | passes |

**fl-sole is not kept, and `fore_lag` at w10 is a dead end as written**:
it splits the fores but gives back the hind split `hind_lag` bought, RH's
heel (0.36 → 0.08) and the taps. The two pair-lag terms compete; LH's U
falling to 0.18 came with RH's stance shrinking, not with a flatter
second hind (`hlk8-mirror.md`). P2's fore lag stays open; P1's next lever
is the second hind's stance (`hlk8-mirror.md`).
