# orun14 P1: hw-sole at 50, and tr-sole (ADR-785's trailing paw) launched

Verified against source: 2026-10-21. Follows `hw-sole-25.md` and
`leo-v03.1.md`.

## hw-sole at 50

- **The checkpoint:** the final `gallop.cxpolicy` (iteration 49, the best,
  reward per step 26.9), sha256 `7a42e596`, revision `9820961f`, cold from
  hw-sole's launch. Exit 0, 50 iterations.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `hw-sole-50`; then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py` and `paw_floor.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hw-sole-25 | 0/10 | 0.38 / 0.49 / 0.58 | 0.02 / 0.01 (0/10) | 0.00 / 0.00 | 7 / 9 | 1/10 (1.79) | 10/10 | 0/10 (31.8) | −190 / −100 | 148 / 155 | 2.67 / 2.22 | 0.00 / 0.000 | 2.29 (j_tail1) | 0.00 | 1.8 |
| ps-sole-50 | 0/10 | 2.50 / 2.60 / 2.66 | 0.37 / 0.19 (0/10) | 0.33 / 0.21 | 4 / 14 | 0/10 (1.64) | 10/10 | 9/10 (20.7) | 526 / 191 | 1042 / 984 | 2.44 / 3.22 | 1.00 / 0.160 | 1.82 (j_spine) | 0.00 | 3.4 |
| **hw-sole-50** | 0/10 | 1.41 / **1.46** / 1.54 | **0.20 / 0.24** (0/10, 0.195) | 0.05 / 0.36 | 5 / 3 | 0/10 (2.16) | 10/10 | 8/10 (20) | 191 / −129 | 554 / 314 | 3.50 / 5.17 | 1.00 / 0.120 | 1.81 (j_hip_l) | 0.00 | 3.6 |

- **Left and right (O5):** heels 0.20 / 0.24 (19%), but stride 554 / 314
  mm (43%), touchdowns 3.50 / 5.17 Hz (32%) and overreach +191 / −129 mm:
  the right hind steps short and often.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|
| LH | 0.16 / 0.63 / 0.00 / **0.19** | 0.16 (0.20) | +3.3 | +16.1 | +32.6 / +1.3 | 613 / 1511 | 220 | 0.00 |
| RH | 0.09 / 0.30 / 0.00 / **0.58** | 0.13 (0.24) | +7.7 | +21.4 | +27.4 / +3.2 | 617 / 1112 | 259 | 0.00 |

- LH stands flat (its heel-down frames 1.00 flat). RH folds toes-up of the
  floor on 0.58 of its ground frames, and 0.60 of its heel-down frames are
  toes-up.
- The pin's p95 rate is under 900 °/s on both legs, with no flapping (O9).

### Gait and spine

- **Pair lag (`p2_lag.py`):** fore 0.121 of the stride (together on 0.10),
  hind 0.434 (together on 0.22); flight 0.120 s; **rotary on 10/10 seeds**
  (172 of 176 ordered strides), the first v03 screen to read rotary. Its
  hind lag is far from O3a's fast end and the right hind's stride is short,
  so it reads as a slow rotary canter.
- **Spine (`spine_foot.py`):** 20.4° a stride (both joints), 0.01 of
  frames at a stop, cable gap at most 0.41°.
- **Drives (O6):** the worst RMS over rated is 1.81 on `j_hip_l`; the peak
  margin is 0.

### The decision: not kept

**Keep rule** (from `hw-sole-25.md`): heel share reaching ps-sole-50's (0.37
/ 0.19) with U under 0.2 on both legs. LH: heel 0.20 < 0.37, U 0.19. RH:
heel 0.24 ≥ 0.19, U 0.58. It fails on both legs. Doubling `heel_pitch`
halved ps-sole-50's speed and did not undo the fold on the right hind.
The lever that is left is the clip, which pays the fold in swing
(`leo-v03.1.md`).

## tr-sole: ps-sole's task on a clip whose paw trails (ADR-785)

- **The change, policy side (O1: the policy first):** ADR-785 adds
  `trail_feet` to the gait generator. A flat foot is laid flat only while
  it is down, so through the heel's ease after toe-off the paw trails the
  leg instead of staying level as the heel rises. The engine change is
  `0b853890`.
- **The clip (`clip_trail.py`, ps-sole's bundle regenerated exactly, then
  with `trail_feet`):**

| clip | leg | pin ° in stance | pin ° in swing | largest step ° | pin per sample ° |
|---|---|---|---|---|---|
| sole | LH | 1.6..3.8 | 0..57.7 | 57.5 | 2 4 4 4 4 25 42 58 0 0 0 0 0 0 0 0 0 2 3 3 2 |
| sole | RH | 0.0..3.8 | 0..56.0 | 53.8 | 4 4 25 41 56 2 0 0 0 0 0 0 0 1 1 1 0 0 0 4 4 |
| **sole + trail** | LH | 1.6..3.8 | 0..**8.4** | 7.2 | 2 4 4 4 4 8 7 0 0 0 0 0 0 0 0 0 0 2 3 3 2 |
| **sole + trail** | RH | 0.0..3.8 | 0..**7.4** | 6.6 | 4 4 7 7 0 0 0 0 0 0 0 0 0 1 1 1 0 0 0 4 4 |

  The stance is unchanged (four heel-down samples a leg, pin 0–3.8°), the
  largest IK miss is 0.12 mm, and the swing pin stays under 30°.
- **The run:** `~/orun14-tr.py` is `orun14-ps.py` with
  `trail_feet=True` in the gallop clip (one literal): p1-flat's task (pin
  encoders, `paw_flat` w10, `heel_pitch` w10, 19 terms). It was built by
  `orun13/queue_run.py` behind hw-sole and accepted as revision
  `32890126`. The model is unchanged (leo v03), so nothing is tagged. The
  bundled clip in `runs/tr-sole/train/gallop-task.json` carries
  `"trails": true` on both hind legs, with the swing pin at most 8.4 / 7.4°.
  Launched at 12:20:28: cold, 50 iterations, 4096 envs, seed 0, budget
  4,800 s.
- **Timing (O8):** iteration 25 landed at 12:55:18, 2,090 s after launch
  (hw-sole's took 2,095 s), so 50 iterations end near 13:30, inside the
  budget.
- **Keep rule:** the stance fold falls, with U under 0.2 on both legs at 25
  or 50, and heel share over ps-sole-25 (0.03 / 0.17) at a speed within
  ps-sole's spread at the same checkpoint. If U stays at ps-sole's 0.8,
  the clip's swing was not what taught the fold.
