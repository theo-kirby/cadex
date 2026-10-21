# orun14 P1: p1-flat at 50, and the sole clip (ADR-784)

Verified against source: 2026-10-21. Follows `p1-flat-25.md`.

## p1-flat-50

- **The policy:** p1-flat's final, `gallop.cxpolicy` at iteration 50, sha256
  `ac9a3030`. Cold from `4c9de98d`, 4096 envs. The run ended itself at
  08:57 (exit 0). The trainer read 25.8 reward/step at iteration 49, with
  episodes of 1,743 steps. Episodes fell to 205–309 steps at iterations
  33–36 and recovered.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `p1-flat-50`, verdict `fail`. Then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py`, `paw_floor.py` and
  `rod_gap.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h1-meta-25 | 0/10 | 0.61 / 0.73 / 0.85 | 0.07 / 0.04 (0/10) | 0.04 / 0.00 | 0/10 (2.10) | 9/10 | 2/10 | −222 / −177 | 173 / 192 | 2.78 / 3.00 | 0.000 s | 1.86 (j_tail1) | 0.00 | 2.1 |
| p1-flat-25 | 0/10 | 0.36 / 0.41 / 0.57 | 0.00 / 0.01 (0/10) | 0.00 / 0.00 | 0/10 (3.50) | 7/10 | 5/10 | −206 / −144 | 188 / 150 | 2.50 / 1.78 | 0.000 s | 2.25 (j_tail1) | 0.00 | 1.9 |
| **p1-flat-50** | 0/10 | 1.20 / **1.46** / 1.60 | **0.31 / 0.52** (0/10, 0.305) | 0.37 / 0.53 (0/10) | 0/10 (1.49) | 2/10 (0.68) | 9/10 (19.4) | +120 / −235 | 278 / 252 | 4.33 / 5.11 | **0.085 s, every stride** | 1.82 (j_hip_l) | 0.00 | 3.8 |

- **Passing:** `completes`, `no_fall` 10/10, and `upright` 10/10 (23.2°).
- **Left and right (O5):** heels 0.31 / 0.52, a 41% spread. Stride 278 /
  252 mm. Touchdowns 4.33 / 5.11 Hz. The heel's median stance height is
  3 / 1 mm.
- **Gait (`p2_lag.py`):** rotary on 10/10 seeds, 170 of 189 strides (12
  tied). Fore lag 0.094 of the stride (about 39 ms at 2.38 Hz, under O3's
  40 ms). Hind lag 0.429. Flight 0.085 s on every stride.
- **Spine (`spine_foot.py`):** 14.9° a stride (both joints), 0.00 of frames
  at a stop. `j_spine` stays flexed, about −23° to −5°. The cable gap is at
  most 0.41°.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| leg | on-ground F / R / T / U | heel share | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | flapping | heel-down frames flat / toes-up |
|---|---|---|---|---|---|---|---|---|
| LH | 0.22 / 0.55 / 0.00 / **0.22** | 0.31 | +2.8 | +9.9 | 0.10 | 314 / 737 | 0.00 | 0.86 / 0.14 |
| RH | 0.33 / 0.29 / 0.00 / **0.38** | 0.52 | +3.6 | +8.6 | 0.15 | 322 / 919 | 0.00 | 0.63 / 0.37 |

- RH's pin peaks at 919°/s. Its p95 is 322°/s, under O9's 900.

### Rod loops (`rod_gap.py`)

`j_frodbot_l` has 39 frames over 2 mm, on 10 seeds, with a 3.80 mm
maximum. `j_frodbot_r` has 25 frames, with a 2.89 mm maximum.
`j_rodbot_l` has 4 frames, with a 2.60 mm maximum and the hock at 0.95
of peak. On every front frame over 2 mm, the front wrist drive is at
its peak. `p1-flat-25.md` already reads this.

## The decision: not kept, a dead end as a screen

**Keep rule (`p1-flat.md`):** the U share under 0.2 on both legs, with
heel share and speed no worse than h1-meta-25's. Heel share (0.31 / 0.52
against 0.07 / 0.04) and speed (1.46 against 0.73 m/s) pass. The U share
fails: 0.22 / 0.38. RH stands toes-up of the floor on 0.37 of its
heel-down frames.

So p1-flat is not kept. It is still the first orun14 policy:
- with the heel down on more than 0.3 of stance on both legs;
- with a flight phase every stride;
- rotary on 10 of 10 seeds.

Between 25 and 50 the paw did not go toes-up the way g1-free's did (U
0.76 at g1-free-50). The pin observation with `paw_flat` held it to
0.22 / 0.38.

## The next screen: s1-sole (ADR-784)

- **The change:** `flat_feet="sole"`. The clip holds the paw at its level
  pitch while the heel is held. `clip_sole.py` regenerates p1-flat's
  bundled clip exactly, then with the option:
  - the sole pitch is −61.90° on both legs;
  - on every heel-held sample, heel, pad and toe are 0.0 mm above the
    ground (`clip_pad.py`, against 3.7–13.3 mm into the floor before);
  - `_META` is +5.8 and the pin 3.8° toes-up;
  - the largest IK miss is 0.12 mm.
- **The script:** `orun14-s1.py` is h1-meta's script (`orun14-h1.py`) with
  `flat_feet="sole"` in the gallop clip, under `FREE_PAW`.
  - It is h1-meta's task, not p1-flat's, because p1-flat failed its keep
    rule.
  - It is a clip change, not a model change (O1). No tag.
- **The queue:** `orun13/queue_run.py s1-sole 4800 50 --envs 4096 --after
  p1-flat --build orun14-s1.py`, cold.
  - Queued 08:41; the build started then.
- **Judge at 25:**
  - against h1-meta-25: heel share, floor pitch and U share;
  - `clip_pad.py` on the bundled clip: pad ≈ 0 and `_META` ≈ +6 in
    stance.
- **Keep rule:** heel share above h1-meta-25's on both legs, with the U
  share under 0.2.
- **If it moves the heel:** the next screen puts the sole clip under
  p1-flat's task. p1-flat-50's pin channels and `paw_flat` held the paw
  flatter than any earlier screen.
