# orun13 B1/P1: g2-heel5 at 25 moves; hind_flat retargeted to leo's flat sole

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 4).

## g2-heel5 at 25 (`gallop.000025.cxpolicy`, sha256 `f083c3c7`)

g2-heel5 is heel5's stored task on the 62.5 ms RH-lead rotary clip
(revision `e46d3273`, `stand-cause.md`), cold, 4096 envs, seed 0. Its
checkpoint 25 was judged as `g1-s1-25.md`, on the bundle's `gallop_spec`,
seeds 1001–1010, on the CPU (`judge.py`, `legs.py`, `p2_lag.py`,
`spine_foot.py`, `trace_check.py`). The trainer read 17.23 reward/step at
iteration 24.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5c-s1-final (orun12, v07) | 0/10 | 2.81 / 2.91 / 3.01 | 0.60 / 0.61 | 1.00 / 1.00 | 10/10 | 10/10 | 279 / 286 | – | – | 2.01 (j_spine) | 0.00 | 2.9 |
| heel5-s1-25 (orun12, v07) | – | 1.16 (median) | – | – | – | – | – | – | – | – | – | – |
| g1-s1-50 | 0/10 | 0.24 / 0.32 / 0.45 | 0.09 / 0.21 | 0.09 / 0.00 | 4/10 | 9/10 | −186 / −148 | 92 / 93 | 2.44 / 2.44 | 1.98 (j_tail1) | 0.00 | 2.7 |
| **g2-heel5-25** | 0/10 | **0.73 / 0.96 / 1.09** | 0.24 / 0.57 | 0.18 / 0.55 | 0/10 | 10/10 | −209 / −227 | 170 / 153 | 2.78 / 3.78 | 1.95 (j_spine) | 0.00 | 2.5 |

- **It moves.** 0.96 m/s at the median, three times g1-s1's and 83% of
  v07's heel5-s1 at the same checkpoint (1.16). The stride nearly doubled
  (92 → 170 / 153 mm). It is over the 0.6 m/s stop line (O8), so it runs
  on to 50.
- `completes`, `no_fall` and `upright` (16.7° median) pass 10/10;
  `every_stride` 10/10.
- **`straight` fails 10/10**: maximum heading 34.6° at the median, over
  25°. It veers, which g1-s1 (standing) did not.
- **P1 0/10.** `hock_down` passes 1/10 (worst-leg median 0.235);
  `hock_at_toeoff` 0/10 (0.176). The right heel is down 0.57 of stance,
  the left 0.24: a 59% spread (Q1).
- **`no_tap` 0/10** (1.83 fore touchdowns per hind stride at the median).
- **Footfalls (`p2_lag.py`).** Fore lag 0.39 of a cycle, hind lag 0.30
  (about 125 ms at 2.38 Hz), so the pairs are no longer tied: 31 of 93
  strides tied, against 14 of 27. But the fore paws step at 1.79 Hz and
  the hinds at 1.30, and 55 strides have no clean order; 4/10 seeds read
  rotary. Flight: 0.46 of strides, 0.000 s at the median. It is not yet a
  gallop.

## Spine and feet (`spine_foot.py`)

- **Spine.** Both joints run from about −26° to +2° (to +16° on two seeds),
  9–13° each per stride, 19.8° in all at the median, against g1-s1's 14.4°.
  At a stop 0.05 of frames at the median (0.38 on seed 1006). Peak flexion
  at 0.26–0.50 of the left hind's stride, peak extension at 0.33–0.75.
- **The cable holds.** Largest `|j_spine2 − j_spine|` 0.40° (judge.py
  closure median 0.017°), under O9's 1°.
- **Rigid foot**, medians over seeds:

| leg | heel share of stance (engine) | heel-down frames flat | toes-up | sole tilt mm (toes − heel) | heel mm in stance |
|---|---|---|---|---|---|
| LH | 0.24 (0.24) | 0.55 | 0.45 | −5.5 | 5.0 |
| RH | 0.57 (0.57) | 0.65 | 0.35 | −0.8 | 0.4 |

When the heel is down the foot is now flat 0.55 / 0.65 of the time
(g1-s1-50: 0.10 / 0.17). The rest is toes-up.

## Real meshes (`trace_check.py`)

- Nine pairs that are apart in the build pose interpenetrate past 5 mm,
  all brief: the right hind paw into the right elbow drive (12.5 mm, 2
  frames, seed 1005) and into the right fore paw (8.1 mm, 74 frames, seed
  1006), and seven more at 5.1–7.3 mm. g1-s1, which stood, had none. The
  hind paw reaching the fore leg is the overreach clash O4 foresaw.
- Front paw meshes 13.5 / 14.5 mm under the floor (the 18 mm mesh offset of
  `g1-s1-25.md`). Loop gap max 2.5 mm (front rod), over O9's 2 mm, as
  before.

## hind_flat on leo's rigid foot (`hind_flat_target.py`, new)

`hind_flat` (weight 6) paid 0 on leo (`stand-cause.md`): its target, a paw
pitch sine of 0.588 (+36°), was feline v07's pinned paw lying flat.

`docs/probes/orun13/hind_flat_target.py` takes the heel and paw collision
geoms in the paw body's frame (they move 0.00 mm against each other over
the 21 clip samples: the foot is rigid) and pitches the foot about world y:

- **The sole is flat** (the paw's and heel's lowest points level) at a paw
  body pitch of **−59.4°**, `2 qw qy` = −0.861, on both legs.
- v07's +36° is, on leo, the heel 74 mm above the toes. The old term could
  only ever pay a foot standing on its toes.
- `heel_pitch`'s metatarsus angle is the paw pitch plus exactly 63.9° on
  every clip sample, so **the sole is flat at `heel_pitch` +4.5°**.
  `heel_pitch` pays full anywhere under 10°, toes-up included (toes up is
  the angle going negative). That is why g1-s1-50 sat on its heels with
  the toes up in 0.83–0.90 of heel-down frames without losing reward.

A sine near −0.86 is a poor channel (it flattens towards −1, so a
toes-up foot would still earn 0.44 of it), so the retarget is on the
angle `heel_pitch` already computes: **full at +4.5°, nothing 15° either
way, paid in the clip's hind stance** (`ref_*h_down`), weight 6 as
before.

`reward_terms.py`, means per step after 0.5 s:

| bundle | hind_flat hold | keyframe | clip | total clip |
|---|---|---|---|---|
| g2-heel5 (`e46d3273`) | 0.000 | 0.000 | 0.000 | 32.38 |
| retargeted | 0.257 | 0.000 | 1.059 | 33.44 |

Every other term is unchanged. The clip's own stance pays 1.06 of a
possible 6 × its stance share: the clip's heel-down samples are not flat
either, as on v07.

## g3-flat, queued

- `~/orun13-scripts/leo-flat.py` (leo's script with the term above),
  built by `queue_run.py --after g2-heel5 --build` at 22:17 as revision
  **`a280b070`** (project git `e613db1`). The bundle's 18 terms equal
  g2-heel5's except `hind_flat`, whose expression is the one scored above;
  tracking, terminations and observations are equal and the model XML is
  byte-identical (`a18e3a4c`). A task change, not a model change (O1).
- **g3-flat**: cold, 50 iterations, 4096 envs, seed 0, `budget_s` 6,000;
  registers when g2-heel5 frees the machine (about 22:45).
- The question: does a two-sided flat-sole term raise the flat share of
  heel-down frames, and the heel share, against g2-heel5 at the same
  checkpoints, without costing its speed?
