# orun14 P1: s1-sole at 25, the sole clip alone

Verified against source: 2026-10-21. Follows `p1-flat-50.md` (s1-sole's
design and keep rule) and `wrist-peak.md`.

## The run and the judging

- **The run:** s1-sole is h1-meta's task on ADR-784's `flat_feet="sole"`
  clip. Revision `d5192106` (leo git `22b5e19`), model 4c9de98d's, cold,
  4096 envs, seed 0. Launched 09:05:09.
- **Timing (O8):**
  - iteration 1 landed at 293.6 s, compile included;
  - iteration 10 landed at 917 s, so 69.3 s an iteration;
  - 50 iterations come to about 3,690 s, inside the 4,800 s budget (+30%);
  - the curve matches p1-flat's and h1-meta's: reward 20.2 / 14.7 / 13.3
    at iterations 0 / 5 / 10, and 16.5 at iteration 24, with episodes 3,151
    steps long.
- **The checkpoint:** `gallop.000025.cxpolicy`, sha256 `b618262b`.
- **The judging:**
  - `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on the CPU,
    evaluation `s1-sole-25`;
  - then `orun12/legs.py`, `orun13/p2_lag.py`, `orun13/spine_foot.py`,
    `paw_floor.py`, `rod_gap.py` and `wrist_peak.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight strides / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h1-meta-25 | 0/10 | 0.61 / 0.73 / 0.85 | 0.07 / 0.04 (0/10) | 0.04 / 0.00 | 10 / 10 | 0/10 (2.10) | 9/10 | 2/10 (26.4) | −222 / −177 | 173 / 192 | 2.78 / 3.00 | 0.10 / 0.000 | 1.86 (j_tail1) | 0.00 | 2.1 |
| **s1-sole-25** | 0/10 | 0.93 / **1.02** / 1.17 | **0.06 / 0.06** (0/10, 0.055) | 0.00 / 0.03 | 16 / 14 | 0/10 (1.93) | 10/10 | 9/10 (22.2) | −162 / −279 | 247 / 212 | 3.56 / 4.67 | **0.63** / 0.040 | 1.53 (j_spine) | 0.00 | 2.5 |

- **Passing:** `completes`, `no_fall` and `upright` 10/10 (15.2°).
- **Left and right (O5):** heels 0.06 / 0.06; stride 247 / 212 mm;
  touchdowns 3.56 / 4.67 Hz, a 24% spread.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|
| h1-meta-25 | LH | 0.05 / 0.79 / 0.01 / 0.13 | 0.07 | +1.3 | +17.5 | 0.11 | 298 / 830 | 131 | 0.00 |
| h1-meta-25 | RH | 0.04 / 0.79 / 0.00 / 0.15 | 0.04 | +2.3 | +17.2 | 0.13 | 329 / 785 | 131 | 0.00 |
| **s1-sole-25** | LH | 0.01 / 0.58 / 0.01 / **0.41** | 0.06 | +2.6 | **+34.0** | 0.16 | 432 / **1314** | 143 | 0.00 |
| **s1-sole-25** | RH | 0.05 / 0.77 / 0.01 / 0.16 | 0.06 | +1.2 | +21.4 | 0.10 | 401 / 922 | 156 | 0.00 |

The feet are on their pads, heels up (`R`). LH's pin sits 34° toes-up in
stance, double h1-meta's, and lands toes-up of the floor on 0.41 of its
ground frames. That is g1-free-50's habit coming back on a paw the actor
cannot see. The pin's p95 rate stays under O9's 900 °/s, but its
maximum is 1,314 °/s.

### Gait, spine, O9 (`p2_lag.py`, `spine_foot.py`, `rod_gap.py`, `wrist_peak.py`)

- **Pair lag:**
  - fore 0.364 of the stride, hind 0.363;
  - pairs land together in 0.07 / 0.23 of strides;
  - rotary on 4/10 seeds (87 of 146 strides);
  - a flight on 0.63 of strides, 40 ms median.
  - Every RH-first stride is rotary, and LH-first strides are transverse
    (e.g. seed 1001: 0/10 rotary).
- **Spine:** 33.2° a stride (both joints), against p1-flat-25's 19.8°; 0.03
  of frames at a stop; the cable gap is at most 0.35°.
- **Rod loops:**
  - `j_frodbot_l` reaches 2.49 mm on 8 frames over 6 seeds, and
    `j_frodbot_r` 2.04 mm on 1 frame;
  - every frame over 2 mm is at wrist peak;
  - the hind loops stay under 1.8 mm.
- **The wrist:** at peak on 0.44 / 0.29 of fore stance frames, and 0.11 /
  0.08 of frames sit past the stop by up to 15.8°. That is the carpus-stop
  yield `wrist-peak.md` describes.

## The decision: not kept; ps-sole queued, s1-sole runs on to 50

**Keep rule:** heel share above h1-meta-25's on both legs, with U share
under 0.2. It fails:
- LH: 0.06 against 0.07, with U 0.41;
- RH: 0.06 against 0.04 passes, with U 0.16.

The sole clip alone did not bring the heel down by 25. Without the pin in
view, LH folded the paw toes-up as g1-free did. It did make leo faster and
airborne earlier: 1.02 m/s against 0.73, and flight on 0.63 of strides
against 0.10.

**s1-sole is not stopped.** It runs to 50, finishing about 10:06. Its last
25 iterations overlap ps-sole's build, so stopping it would only idle the
GPU. Its 50 checkpoint answers whether the heel comes down between 25 and
50 on the sole clip, as it did on p1-flat (0.01 → 0.31 / 0.52). It is
not kept unless 50 passes the keep rule.

**Next: ps-sole.** This is the critic's item 3. Its trigger, the heel
moving, did not fire. It is queued anyway because it is the screen the
measurements point at:
- p1-flat-50's pin channels and `paw_flat` held U to 0.22 / 0.38;
- s1-sole shows that without them the paw folds;
- p1-flat's remaining fault was the clip's pad-in-floor stance, which the
  sole clip removes.

ps-sole is described here:
- **The script:** `~/orun14-ps.py` is p1-flat's script (`orun14-p1.py`:
  pin encoders observed, 122 channels, and `paw_flat` w10, 19 terms) with
  s1-sole's `flat_feet="sole"` hunk. It is a clip and task change, so the
  model is unchanged and gets no tag.
- **The queue:** `orun13/queue_run.py ps-sole 4800 50 --envs 4096 --after
  s1-sole --build ~/orun14-ps.py`, cold. Queued 09:41:32, and the build
  started then. It launches when s1-sole ends.
- **The keep rule:** heel share above h1-meta-25's on both legs, with U
  share under 0.2, judged at 25 and 50 against p1-flat at the same
  checkpoints.
