# orun14: g1x-free at 75, stopped early (O8)

Verified against source: 2026-10-21. Follows `g1-free-50.md` and
`rh-mirror.md`.

## The run and the judging

- **The run:** g1x-free is g1-free's final policy continued warm on the
  same bundle (leo v03 `bc287c9c`), critic warmup 5, 4096 envs. Its
  checkpoint at its own iteration 25 is overall iteration 75
  (`gallop.000025.cxpolicy`, sha256 `4e48ebb6`). It ran at about 82 s an
  iteration. The trainer read 35.5 reward/step there, still rising.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010,
  on the CPU, evaluation `g1x-free-75`. Then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py` and `paw_floor.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | no_tap | every_stride | overreach mm LH / RH (spec) | stride mm | touchdown Hz | flight stride share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g1-free-50 | 0/10 | 2.19 / 2.24 / 2.49 | 0.30 / 0.16 (0/10, 0.164) | 0.15 / 0.29 | 0/10 (2.31) | 10/10 | 451 / 47 (10/10, 47.1) | 895 / 475 | 2.44 / 5.50 | 1.00, 0.160 | 1.67 (j_spine) | 0.00 | 3.9 |
| **g1x-free-75** | 0/10 | 2.74 / **2.85** / 2.91 | **0.36 / 0.18** (0/10, 0.182) | 0.23 / 0.33 | 0/10 (2.05) | 10/10 (0.98) | 603 / −118 (3/10, −118) | 1160 / 587 | 2.33 / 4.89 | 1.00, 0.160 | 1.71 (j_hip_r) | 0.00 | 3.7 |

- **Passing:** `completes`, `no_fall`, `upright` (18.1°), `straight`
  (10.9°), `every_stride` (0.98).
- **Failing medians:** `top_speed` 2.85 m/s, `hock_down` 0.182,
  `hock_at_toeoff` 0.23, `no_tap` 2.05, and `overreach`, now 3/10 at
  −118 mm (RH lands behind the fore paw).
- **The stride clock is LH's.** `no_tap` and `every_stride` clock the
  stride on LH (`footfall_metrics`' reference anchor). RH's two contacts
  a stride (4.89 Hz against LH's 2.33) fail `no_tap`. A double-contacting
  LH would fail `every_stride` instead.
- **Left and right differ (O5).** Heels 0.36 / 0.18, stride 1160 / 587
  mm, touchdowns 2.33 / 4.89 Hz. Q1's 20% bar fails on all three, as at
  50. `rh-mirror.md` showed this asymmetry is the policy's.

## The hind paws: more toes-up, not less

`paw_floor.py`, medians over 10 seeds:

| evaluation | leg | on-ground F / R / T / U | floor pitch ° in stance | pin ° in stance | pin ° / floor pitch ° at lift | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping swings |
|---|---|---|---|---|---|---|---|---|---|
| g1-free-50 | LH | 0.02 / 0.22 / 0.00 / 0.76 | +32.8 | +43.8 | +48.9 / +7.0 | 0.50 | 614 / 1185 | 219 | 0.00 |
| g1-free-50 | RH | 0.03 / 0.19 / 0.01 / 0.77 | +25.7 | +38.1 | +37.9 / +20.0 | 0.63 | 589 / 1326 | 327 | 0.00 |
| **g1x-free-75** | LH | 0.01 / 0.14 / 0.01 / **0.84** | **+42.0** | +53.1 | +60.5 / +14.2 | 0.55 | 534 / 1183 | 232 | 0.00 |
| **g1x-free-75** | RH | 0.01 / 0.18 / 0.02 / **0.80** | **+29.0** | +41.1 | +41.4 / +21.3 | 0.66 | 475 / 1076 | 315 | 0.00 |

Seed 1001, 2.0–3.0 s:

    LH  .....UUUUURR...............UUUUUUT.............UUUR
    RH  .....UU......UU...........UU........UU........UUU..

- **The heel share rose on a toes-up paw.** Every LH stance lands on the
  heel and the rear of the pad with the paw 40–55° toes-up of the floor.
  The LH pin sits at +53° in stance, close to its 60° travel stop, and
  reaches it (+60.5°) at lift. Not one RH stance frame in the seed above
  is flat.
- So the gain from 0.30 / 0.16 to 0.36 / 0.18 is O2's fault growing. It
  is not P1 coming closer.
- **Pin speed (O9):** 534 / 475°/s p95, swing 232 / 315°/s p95, no swing
  frame over 900°/s, no flapping.

## Gait, spine, torque

- **Pair lag (`p2_lag.py`):** fore 0.122 of the stride (about 51 ms),
  hind 0.386 (about 162 ms; together on 0.15 of strides). 3/10 seeds read
  rotary on 8 of 10 strides. Every ordered stride is rotary from RH; none
  is transverse.
- **Flight:** every stride, 0.160 s.
- **Spine (`spine_foot.py`):** 25.6° a stride (sum of the two joints),
  0.00 of frames at a stop, the cable gap at most 0.52° (O9: 1°).
- **Torque:** the worst RMS drive is `j_hip_r` at 1.71× rated; the peak
  margin is 0.00, as on every leo policy so far. Rod loops are open to
  3.7 mm (O9: 2 mm).

## The decision: stop at 75

g1x-free's written stop rule (`g1-free-25.md`: under 1.5 m/s, or heels
under 0.10) does not fire: 2.85 m/s, heels 0.36 / 0.18. It was stopped
anyway, after 30 of its 50 iterations (80 overall; it wrote no final
policy, only the 75 checkpoint and `gallop.best`), under O8's early-stop rule, because the measure
it was run for went the wrong way:

- its question was whether the heel comes down by 100. It does, slightly,
  but only on a paw folded further toes-up. The U share rose from
  0.76 / 0.77 to 0.84 / 0.80, and the floor pitch from +32.8 / +25.7 to
  +42.0 / +29.0;
- both queued screens, h1-meta and p1-flat, start cold, so the remaining
  20 iterations would have fed no screen in the queue;
- stopping started h1-meta at 07:15:57, about 25 minutes sooner, and
  with it p1-flat's build (`orun14-p1.py`), which the queue starts once
  h1-meta registers.

The 75 checkpoint stays as the fastest v03 policy so far (2.85 m/s,
flight every stride). Do not warm-start a P1 screen from it: its habit is
the toes-up landing that P1 forbids.
