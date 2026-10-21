# orun14 P1: s1-sole at 50, the sole clip alone, not kept

Verified against source: 2026-10-21. Follows `s1-sole-25.md`.

## The run and the judging

- **The run:** s1-sole, h1-meta's task on ADR-784's `flat_feet="sole"`
  clip, revision `d5192106`, cold, 4096 envs, seed 0. It ran all 50
  iterations in 3,768 s (exit 0, witness error 1.9e-7).
- **The checkpoint:** the final `gallop.cxpolicy` (iteration 49, the
  best), sha256 `142c4dcb`. Reward per step 32.1, against 16.5 at
  iteration 24; episodes 1,638 steps.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `s1-sole-50`, then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py`, `paw_floor.py`,
  `rod_gap.py`, `wrist_peak.py` and `paw_flat.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight strides / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s1-sole-25 | 0/10 | 0.93 / 1.02 / 1.17 | 0.06 / 0.06 (0/10, 0.055) | 0.00 / 0.03 | 16 / 14 | 0/10 (1.93) | 10/10 | 9/10 | −162 / −279 | 247 / 212 | 3.56 / 4.67 | 0.63 / 0.040 | 1.53 (j_spine) | 0.00 | 2.5 |
| p1-flat-50 | 0/10 | 1.20 / 1.46 / 1.60 | 0.31 / 0.52 (0/10, 0.305) | 0.37 / 0.53 | 3 / 1 | 0/10 (1.49) | 2/10 | 9/10 | 120 / −235 | 278 / 252 | 4.33 / 5.11 | 1.00 / 0.085 | 1.82 (j_hip_l) | 0.00 | 3.8 |
| **s1-sole-50** | 0/10 | 2.68 / **2.80** / 2.90 | **0.17 / 0.08** (0/10, 0.080) | 0.04 / 0.13 | 10 / 16 | 0/10 (1.96) | 9/10 | 10/10 (12.6) | 512 / −323 | 1071 / 568 | 2.89 / 4.56 | **1.00 / 0.170** | 1.60 (j_spine) | 0.00 | 4.1 |

- **Passing:** `no_fall` 10/10; `completes` and `upright` 9/10. Seed
  1007 stands at 34° tilt and takes no measured stride.
- **Left and right (O5):** heels 0.17 / 0.08 (52% apart); stride 1,071 /
  568 mm; touchdowns 2.89 / 4.56 Hz (37%). The legs differ more than at 25.

### The hind paws (`paw_floor.py`, `paw_flat.py`, medians over 10 seeds)

| leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|
| LH | 0.02 / 0.43 / 0.03 / **0.51** | 0.17 | +5.4 | +38.4 | 0.08 | 882 / 1353 | 227 | 0.00 |
| RH | 0.00 / 0.16 / 0.02 / **0.81** | 0.08 | **+30.8** | +51.8 | 0.64 | 336 / 1340 | 289 | 0.00 |

The paws fold toes-up of the floor, RH on 0.81 of its ground frames, with
its pin 52° toes-up in stance, near the 60° travel. This is g1-free-50's
habit (U 0.75 / 0.71), now on the sole clip. `spine_foot.py`'s sole check
agrees: heel-down frames are toes-up on 0.34 / 0.47. The pin's p95 rate
stays under O9's 900 °/s (LH 882, close); nothing flaps in swing.

### Gait, spine, O9

- **Pair lag (`p2_lag.py`):**
  - fore 0.308 of the stride, together on 0.17 of strides;
  - hind **0.048**, together on **0.67**: the hinds land nearly as a pair,
    half a bound;
  - rotary on 2/10 seeds (90 ordered strides of 94, 75 tied);
  - every ordered stride leads RH-first;
  - a flight on every stride, 0.170 s median, double p1-flat-50's.
- **Spine (`spine_foot.py`):** 31.5° a stride (both joints), 0.00 of
  frames at a stop, the cable gap at most 0.63°. Peak flexion falls at
  0.05 of the stride, extension at 0.35–0.38.
- **Rod loops (`rod_gap.py`):** `j_frodbot_l` reaches 4.14 mm and
  `j_frodbot_r` 3.08 mm, on 51 / 52 frames over 2 mm on 9 / 10 seeds.
  Every one is at wrist peak, which holds 0.76 / 0.83 of fore stance, with
  the carpus up to 27° past its stop (`wrist_peak.py`). This is the yield
  `wrist-peak.md` describes. The hind loops reach 2.26 mm on 2 frames.

## The decision: not kept

**Keep rule:** heel share above h1-meta-25's (0.07 / 0.04) on both legs,
with U share under 0.2. The heel shares pass (0.17 / 0.08), but the U
shares fail (0.51 / 0.81). The heel is down on a paw folded toes-up behind
it, which is O2's fault, not P1.

Between 25 and 50 s1-sole found speed, 1.02 → 2.80 m/s, the second-fastest
leo v03 policy after g1x-free-75 (2.85). It found it the way g1-free did:
the actor cannot see the pin and does not pay for the paw, so it folds the
paw toes-up and pairs the hinds. **The sole clip, without the pin
observed and `paw_flat`, does not hold the paw flat.** That is what
ps-sole adds.

## ps-sole, launched

- **The bundle:** ps-sole launched on revision `6caadfaa` at 10:10:04
  (built 09:49).
- **`clip_pad.py` on its own bundle:** heel, pad and toe at 0.0 mm on
  every heel-held sample, `_META` +5.8, the pin +3.8° toes-up, and the
  sole level at −61.9° on both legs. The clip is s1-sole's.
- **paw_flat's offset on the sole clip (the critic's check):**
  - the term carries C = +1.9, fitted on g1-free's traces;
  - refitted on sole-clip traces, C is +1.17 (s1-sole-25), +2.00
    (s1-sole-50) and +1.43 (s1-sole-25 with p1-flat-50);
  - F tracks the geometric floor pitch within 2.6° p10–p90 on each leg;
  - on ps-sole's clip samples F is −0.1 at C = 1.9, and −0.6 at the
    refit;
  - an offset error of 0.5–0.7° moves the pay by at most 0.05 of its
    15° half-width, so the term pays the sole clip's stance flat.
- **A caveat:** at the clip's exact poses the paw sits at 0 mm, so the
  contact channel `ch*_down` reads 0 and the term pays 0 on the clip
  samples. In simulation the loaded foot makes contact: the paw pays
  0.70–0.86 on flat paw-down frames in every judged trace. The clip is
  not paid more than a flat policy.
