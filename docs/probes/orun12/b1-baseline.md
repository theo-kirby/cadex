# orun12 B1: v07-g1, the baseline, judged

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 1).

## The run

v07-g1 is the owner's baseline: `~/cadex-projects/feline-v07` at revision
`9eaff867` (digest `fc218916`), orun11's 17-term plantigrade gallop clip,
trained cold. It was asked for 300 iterations but its 14,400 s budget ran
out at **110** (`training-status.json`: `budget_exhausted`), about **131 s
an iteration** on the 5090. A 300-iteration run of this bundle needs about
39,000 s of training, 47,000 s with O8's 20%. Reward per step: 14.9 (it 24),
21.0 (49), 25.3 (74), 27.4 (99), best 27.5 (103), 27.1 (109): flat over its
last ten iterations.

Every checkpoint it left was judged on the bundle's own `gallop_spec`,
seeds 1001–1010, with the engine's evaluation on the CPU (no GPU):

```
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.<tag>.cxpolicy v07-g1-<n>
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/v07-g1-*
```

The reports are `feline-v07/evaluations/v07-g1-{25,50,75,100,best}/evaluation.json`.
`gallop.best.cxpolicy` is the iteration-99 policy (the last checkpoint
entry tagged best); its evaluation equals iteration 100's seed for seed.
`legs.py` (new, standard library) prints the tables below: each
predicate's passes and median, each hind leg's values with the left/right
spread, the footfall order, flight, torque and the loop gap.

## Predicates (passes, median)

| evaluation | pass | completes | no_fall | upright | straight | top_speed | hock_down | hock_at_toeoff | no_tap | every_stride | overreach |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v07-g1-25 | 0/10 | 10/10 (1) | 10/10 (0) | 10/10 (23.8) | 10/10 (12.1) | 0/10 (689) | 0/10 (0.0306) | 0/10 (0.0147) | 0/10 (1.62) | 10/10 (1.12) | 0/10 (-418) |
| v07-g1-50 | 0/10 | 10/10 (1) | 10/10 (0) | 10/10 (17.7) | 10/10 (5.81) | 0/10 (2.38e+03) | 0/10 (0) | 0/10 (0) | 0/10 (1.82) | 10/10 (1.03) | 9/10 (9.92) |
| v07-g1-75 | 0/10 | 10/10 (1) | 10/10 (0) | 10/10 (14.1) | 10/10 (5) | 0/10 (3.05e+03) | 0/10 (0) | 0/10 (0) | 0/10 (1.91) | 10/10 (1.03) | 10/10 (156) |
| v07-g1-100 | 0/10 | 10/10 (1) | 10/10 (0) | 10/10 (14.9) | 10/10 (3.05) | 0/10 (3.22e+03) | 0/10 (0) | 0/10 (0) | 0/10 (1.66) | 10/10 (0.98) | 10/10 (234) |
| v07-g1-best | 0/10 | 10/10 (1) | 10/10 (0) | 10/10 (14.9) | 10/10 (3.05) | 0/10 (3.22e+03) | 0/10 (0) | 0/10 (0) | 0/10 (1.66) | 10/10 (0.98) | 10/10 (234) |

`top_speed` is in mm/s, `overreach` in mm (the worse hind), `no_tap` and
`every_stride` the highest and lowest paw touchdown rate over the stride
rate. Every checkpoint completes upright and straight with no fall.

## Hind legs, left / right (spread)

| evaluation | hock down LH / RH (spread) | hock at toe-off | heel stance height mm | overreach mm | touchdown Hz | stride mm |
|---|---|---|---|---|---|---|
| v07-g1-25 | 0.28 / 0.03 (89%) | 0.19 / 0.01 (92%) | 6 / 24 (75%) | -322 / -418 (23%) | 3.17 / 3.44 (8%) | 148 / 144 (2%) |
| v07-g1-50 | 0.15 / 0.00 (100%) | 0.00 / 0.00 (–) | 10 / 32 (69%) | 202 / 10 (95%) | 2.44 / 2.61 (6%) | 970 / 976 (1%) |
| v07-g1-75 | 0.00 / 0.00 (–) | 0.00 / 0.00 (–) | 27 / 76 (65%) | 301 / 156 (48%) | 2.44 / 2.44 (0%) | 1235 / 1234 (0%) |
| v07-g1-100 | 0.00 / 0.00 (–) | 0.00 / 0.00 (–) | 31 / 75 (59%) | 358 / 234 (35%) | 2.33 / 2.44 (5%) | 1324 / 1329 (0%) |
| v07-g1-best | 0.00 / 0.00 (–) | 0.00 / 0.00 (–) | 31 / 75 (59%) | 358 / 234 (35%) | 2.33 / 2.44 (5%) | 1324 / 1329 (0%) |

Medians over seeds; the spread is |L − R| / max (Q1's bar is 20%).
Fore touchdown rates, LF / RF Hz: 2.44 / 2.44 (25), 4.33 / 2.44 (50),
4.56 / 4.39 (75), 2.44 / 3.94 (100) — the clip's stride is 2.44 Hz, so a
fore taps at every checkpoint from 50 (`no_tap` 1.66–1.91).

## Gait and torque

| evaluation | top 2 s m/s min / med / max | flight stride share | flight s | rotary strides | stride Hz | worst RMS/rated | peak margin | loop gap max mm | falls |
|---|---|---|---|---|---|---|---|---|---|
| v07-g1-25 | 0.59 / 0.69 / 1.21 | 0.92 | 0.080 | 57/128 (60 unordered) | 2.38 | 1.31 (j_wrist_l) | 0.00 | 3.3 | 0 |
| v07-g1-50 | 2.32 / 2.38 / 2.41 | 1.00 | 0.100 | 23/133 (169 unordered) | 3.12 | 1.97 (j_spine) | 0.00 | 2.6 | 0 |
| v07-g1-75 | 2.99 / 3.05 / 3.15 | 1.00 | 0.100 | 44/100 (289 unordered) | 4.66 | 2.11 (j_spine) | 0.00 | 2.6 | 0 |
| v07-g1-100 | 3.20 / 3.22 / 3.23 | 1.00 | 0.200 | 153/194 (14 unordered) | 2.38 | 2.07 (j_spine) | 0.00 | 2.7 | 0 |
| v07-g1-best | 3.20 / 3.22 / 3.23 | 1.00 | 0.200 | 153/194 (14 unordered) | 2.38 | 2.07 (j_spine) | 0.00 | 2.7 | 0 |

Stride Hz and flight are clocked on the left fore's landings, so a tapping
LF (50, 75) halves the stride and doubles the rate there. Rotary counts
strides with all four paws landing; at 100 the dominant order is
LF RF RH LH (147 of 194 seeds' strides), rotary with a left-hind lead.
The peak margin is 0 on every checkpoint: on all ten seeds the elbows,
wrists, hips, hocks, spine and first two tail drives reach their clamp
(peak ratio 1.00, never above it; O4 holds). The worst RMS is the spine at
about 2.1× rated, then the right elbow and wrists at 1.4×. The largest loop
gap is a fore rod's lower end (`j_frodbot_r`, 2.6–3.3 mm max, 0.1–0.3 mm
median); the hind rods stay under 1.7 mm. A 3.3 mm worst case is over O9's
2 mm, so Q2 would fail on these traces at the fore rod.

## Against v06-g1

| | v06-g1 (final numbers) | v07-g1 (best, it 99–100) |
|---|---|---|
| passes | 0/10 | 0/10 at every checkpoint |
| best speed | 3.72 m/s at it 150 | 3.22 m/s at it 100 (3.20–3.23), budget-cut at 110 |
| hock-down share | ≤ 0.12, 0 at the end | 0.28 LH / 0.03 RH at it 25, 0 / 0 from 75 on |
| overreach | 355–474 mm | 358 LH / 234 RH mm |

## What it shows

- **Neither heel is plantigrade after iteration 50.** The heels are down
  only at iteration 25, while the cat barely moves (0.69 m/s), and only
  the left (0.28 of stance against 0.03). From 75 on both shares are 0. The
  heel rides 31 mm (LH) and 75 mm (RH) up in stance. The policy lifts the
  heel as it learns to run, as v06-g1 did.
- **The left/right asymmetry is back on v07.** The left hind's heel sits
  lower (31 against 75 mm, a 59% spread) and it overreaches further (358
  against 234 mm). Its stride length and touchdown rate match the right's
  within 5%. The model is meant to be mirrored and the clip has no hind
  lead, so O3's checks (mirror test of the model and the clip, mirrored
  seeds) come next, before any reward or hardware explanation.
- **The fores tap** at 1.6–1.9× the stride rate from 50 on, one side or the
  other. That is `no_tap`'s failure and orun11's pattern.
- **Speed is 3.22 m/s at 110 iterations,** still short of v06-g1's 3.72 at
  150. The reward has flattened over the last 10 iterations, so this
  baseline is not a strong reason to extend it as it is.
- **Every major drive reaches its clamp on every seed;** the spine runs
  at 2.1× rated RMS.
