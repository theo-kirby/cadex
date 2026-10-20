# orun12 P1 (O2a): heel3-s1 at 75 and 100, and heel4-s1's timing

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 8).

## heel3-s1 at 75 and 100

heel3-s1 (`ac32d3b0`, digest `814e5213`; `heel3-screen.md`) finished all
100 iterations (exit 0, 7,072 s wall, best reward/step 37.4 at 99). Its
iteration-75 checkpoint and its final policy (`gallop.cxpolicy`, iteration
100) were judged on the bundle's `gallop_spec`, seeds 1001–1010, on the CPU:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000075.cxpolicy heel3-s1-75
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.cxpolicy heel3-s1-100
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel3-s1-{25,50,75,100}
python3 docs/probes/orun12/hock_stance.py ~/cadex-projects/feline-v07/evaluations/heel3-s1-{75,100}
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel height mm LH / RH | top 2 s m/s min / med / max | overreach mm LH / RH | touchdown Hz LH / RH | stride mm LH / RH | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 0.07 / 0.07 | 0.00 / 0.03 | 41 / 50 | 1.41 / 1.55 / 1.71 | −78 / −140 | 3.67 / 3.67 | 537 / 547 | 1.54 (j_spine) | 0.00 | 3.4 |
| 50 | 0/10 | 0.17 / 0.07 | 0.00 / 0.00 | 12 / 25 | 2.92 / 3.02 / 3.10 | 283 / 221 | 2.50 / 2.78 | 1195 / 1188 | 2.15 (j_spine) | 0.00 | 3.6 |
| 75 | 0/10 | 0.25 / 0.09 | 0.16 / 0.00 | 8 / 28 | 3.20 / 3.34 / 3.48 | 366 / 311 | 2.33 / 2.44 | 1345 / 1345 | 2.14 (j_spine) | 0.00 | 4.2 |
| 100 | 0/10 | 0.27 / 0.02 | 0.33 / 0.00 | 4 / 36 | 3.25 / 3.38 / 3.48 | 325 / 244 | 2.39 / 2.44 | 1369 / 1371 | 2.10 (j_spine) | 0.00 | 4.0 |

Spec predicates at 100: overreach 10/10 (median 244), every_stride 10/10,
no_tap 3/10 (median 1.12), straight 10/10; `hock_down` 0/10 (median of each
seed's worse leg 0.019), `hock_at_toeoff` 0/10. Flight on every stride,
0.18 s. No falls.

- **The left heel comes down; the right does not.** The left climbs on
  every checkpoint: heel share 0.07 → 0.17 → 0.25 → 0.27, heel down at
  toe-off 0.00 → 0.00 → 0.16 → 0.33, heel height 41 → 4 mm. This is the
  first policy this run where one hind heel takes weight at toe-off. It
  is still short of P1's 0.40 bar. The right went the other way after
  50: 0.07 → 0.09 → 0.02, height 25 → 36 mm. The left/right spread on
  heel share is 93% (Q1's bar is 20%). Stride length and touchdown rate
  match within 2%, so the legs share one cadence and only the foot
  differs.
- **The left heel follows the hock.** The left's stance hock gap to the
  clip's heel-down angle fell from +27° at 50 to +13° at 75 and 100. The
  right's gap at 100 is −1°, on the clip's angle, yet its heel sits 36 mm
  up. So on the right, the hock angle is not what holds the heel off. The
  rest of the leg (hip and knee) carries the metatarsus high, or the
  probe's lowest-quarter stance proxy (`hock_stance.py`) catches swing
  frames on that side. This is not resolved here.
- **The speed cap does not hold the speed.** Speed pay stops at 2 m/s,
  but the policy settles at 3.3–3.4 m/s.
- **O4.** A drive sits at its clamp on every checkpoint (peak margin
  0.00). The worst RMS is 2.1× rated, on j_spine.
- **O9.** The worst loop gap is 4.0–4.2 mm at 75/100, over the 2 mm bar.

This is the same handedness v06-g1 showed (only the left hind put its
hock down). `mirror-policy.md` showed that handedness is policy-learned,
not in the model. O2a defers symmetry work until both heels are down.
This screen has one heel half-down, so the deferral still stands.

## heel4-s1: timed (O8)

heel4-s1 (`5bcadba8`, digest `39165e25`, heel3-s1 plus `track_ankle`,
`heel4-ankle.md`) launched from the queue at 22:53:43, when heel3-s1
ended.

- It reached iteration 7 743 s after start (the compile included).
- It ran iterations 7 → 15 in 540 s, which is **67.5 s an iteration** at
  4096 envs. heel3-s1 ran at about the same rate.
- The whole run projects to about 743 + 92 × 67.5 ≈ 6,950 s.
  heel3-s1's wall time was 7,072 s.

`budget_s` 9,000 covers that with about 29% to spare, so it is left as it
is.

heel4-s1 differs from heel3-s1 in one term. The O5 test of `track_ankle`
is heel4-s1 at 25 and 50 against the rows above. Both rows give heel share,
toe-off share and height per leg, plus `hock_stance.py`'s gap. Those
checkpoints land about 40 and 70 minutes after launch.
