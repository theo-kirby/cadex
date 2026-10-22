# orun15 P1: leo-v04.2, the paw spring's rate doubled (O1 write-up)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 8).
Written before the build, as O1 asks. Follows `sfw-sole.md`.

## The measurement

- **RH's fold has not moved under four levers.** U (the share of on-ground
  frames with the paw toes-up of the floor past 5°, `orun14/paw_floor.py`):

| policy | lever | U LH / RH | m/s |
|---|---|---|---|
| sp-sole-50 | the v04 coil (4 N·mm/deg, rest 10°) | 0.32 / 0.29 | 2.18 |
| sf-sole-50 | + contact-gated `paw_fold` | 0.29 / 0.29 | 2.37 |
| sfp-sole-50 | + preload 30° (leo-v04.1) | 0.23 / 0.28 | 2.35 |
| sfw-sole-25 | sf-sole warm +25 at 3e-5 | 0.25 / 0.29 | 2.42 |

  P1 needs U under 0.2 on each leg. The preload, which adds a constant
  torque, moved LH (0.29 → 0.23) and not RH. In stance the pin sits at a
  median +17 / +26° toes-up of the metatarsus (sf-sole-50), where v04's
  coil returns 108 / 144 N·mm: 3–4.5% of a ~3.2 N·m pad push.
- **The rate is what has not been tried.** v04.1 rejected a higher rate
  for fear of flapping (the pin's p95 748 / 775 °/s against O9's 900, and
  v06's stiffer pin flapped). That fear does not survive the pin's own
  numbers, measured this iteration on sf-sole's bundle model
  (`/tmp/pinfreq.py`, not committed: the pin's diagonal of the mass
  matrix at the keyframe, against its stiffness and damping):

| | k N·m/rad | inertia at the pin kg·m² | f_n Hz | damping ratio ζ | return time constant c/k s |
|---|---|---|---|---|---|
| v04 (4 N·mm/deg) | 0.229 | 1.51e-4 | 6.2 | 14.6 | 0.75 |
| v04.2 (8 N·mm/deg) | 0.458 | 1.51e-4 | 8.8 | 10.3 | 0.38 |

  The pin is **an order of magnitude past critical damping** at either
  rate, so the coil cannot ring or flap: v06 flapped because its pin had
  no damper (v07 added it). The 750–885 °/s p95 rates are the floor's
  impacts, not the spring's. What the coil sets is how fast the damper
  lets the paw return: at 30° toes-up, (θ + 10°) / (c/k) is 53 °/s on
  v04 and 107 °/s at 8, over a ~0.4 s stride. v04's coil is too slow to
  return the paw in one swing.
- **The stand, measured before the build** (`orun14/stand_pin.py` on
  sf-sole's bundle model with only `stiffness` doubled to 0.458366
  N·m/rad, `/tmp`, not committed): no NaN; both pins seat 0.3° into the
  flat stop as on v04; pin peak 92 °/s while settling (v04: 99); chest
  (−11.6 mm at 3 s), pitch (1.0°), paws (−0.3 mm) and heels (64.1 mm up)
  equal to v04's.

## The change

- **`PAW_K` 4 → 8 N·mm/deg.** `PAW_PRELOAD` stays 10° (v04's, not v04.1's:
  v04.1 was not kept). Nothing else changes: the coil's part reads
  neither number (it is `SPRING_R`, `SPRING_W`), so the geometry and every
  clearance pair are v04's. The bundled model should differ from
  sf-sole's only in the pin's `stiffness`.
- **The curve:**

| pin toes-up of the metatarsus | v04 N·mm | v04.2 N·mm | share of a 3.2 N·m pad push, v04.2 |
|---|---|---|---|
| 0° (flat, on the stop) | 40 | 80 | 2.5% |
| 8.4° (the clip's swing pin) | 74 | 147 | 4.6% |
| 17 / 26° (stance median, LH / RH) | 108 / 144 | 216 / 288 | 7–9% |
| 30° | 160 | 320 | 10% |
| 46° (at lift) | 224 | 448 | 14% |
| 60° (the toes-up stop) | 280 | 560 | 17.5% |

- **Still easy (O1):** at flat it presses the paw onto its stop with
  80 N·mm, about twice the paw's own weight (~36 N·mm), so it seats the
  paw and cannot hold it off the floor (the stop is at flat). Through
  stance it is 7–10% of a pad push, so the floor still lays the paw flat
  and the heel still lifts on a flat paw at push-off. At the toes-up stop
  it reaches 17.5%, more than v04.1's 11%; that is where the heel lifts
  furthest, and the screen's heel share and `hock_at_toeoff` are the
  check that it has not stopped the heel lifting.

## Expected effect

- The fold costs twice the torque per degree, and the paw returns twice
  as fast in swing, so it lands nearer flat.
- **The expected result:** U falls on both legs, RH by at least 0.05
  (the lever none of the four moved); the speed within 10% of sf-sole-50's
  2.37 m/s; the heel at toe-off no lower than sf-sole-50's 0.38 / 0.15;
  the pin's p95 under 900 °/s.
- **The hypothesis it tests:** that RH's fold is a torque balance a rate
  can move where a constant preload could not. If RH's U stays at
  0.28–0.29 here as well, the fold is the policy's handed half-bound
  (`rh-mirror.md`), and the lever is the hind order (hl-sole's term) or
  the clip, not the spring.

## The build, the gates and the screen

- **The script:** `script.py` at `b32a6ace` (sf-sole's task, v04's coil;
  `script_history/0035`) with the one line `PAW_K, PAW_PRELOAD = 8.0, 10.0`
  and its comment (`~/orun15-queue/orun15-v042.py`). The task is
  sf-sole's 20 terms, without hl-sole's `hind_lag`, so the rate is the
  one change against sf-sole.
- **The screen, k8-sole:** sf-sole's task on v04.2. Cold, 50 iterations,
  4,096 envs, seed 0, `budget_s` 5,600 (50 × ~90 s, hl-sole's pace on
  this machine now, plus start-up, +20%). Queued through
  `orun13/queue_run.py --after hl-sole --build`, which builds now and
  launches when hl-sole frees the machine lock; judged at 25 and 50 with
  `orun14/paw_floor.py` against sf-sole-50.
- **Clearance and tag:** after the build, `cadex clearance` and
  `--sweep`, `orun13/clearance_diff.py` against v04's reports; tagged
  `leo-v04.2` only if no pair is new (`~/orun15-queue/v042-chain.sh`).
- **Keep rule:** RH's U falls by at least 0.05 against sf-sole-50 with
  LH no worse, or U is under 0.2 on both legs; the speed within 10% of
  sf-sole-50's median; the pin's p95 under 900 °/s with no flapping in
  swing. If RH's U has not moved by +25, stop it there (O8).

## Built (after the write-up above)

- **The build:** `cadex script --set` from `queue_run.py --after hl-sole
  --build`, project commit `6040c4f`, accepted revision **`568d38a9`**,
  3.6 min (18:13:31 → 18:17:09).
  - Every verdict in the attempt's `result.json` equals sf-sole's
    revision `b32a6ace` (955 verdict fields compared, 0 differ).
  - The bundled `cat_model-model.xml` differs from `b32a6ace`'s only in
    the two pins' `stiffness`: 0.229183 → 0.458366 N·m/rad. `springref`
    (±10°), damping, friction and range are v04's. Model `b2bb0efe`.
- **Clearance** (`~/orun15-queue/v042-chain.sh`): `cadex clearance` rc 0,
  `--sweep` rc 0, `orun13/clearance_diff.py` against v04's reports:
  **static 14 → 14, swept 8 → 8, 0 new**, leo's baseline.
- **The stand on the built model** (`orun14/stand_pin.py`): no NaN, both
  pins 0.3° into the flat stop, pin peak 92 °/s while settling, paws at
  −0.3 mm, heels 64.1 mm, the clip's `j_spine2` equal to `j_spine`.
- **Tagged `leo-v04.2`** at project `6040c4f`. `leo-v02`, `leo-v03`,
  `leo-v04` and `leo-v04.1` are untouched.
- **k8-sole** is queued with the revision `568d38a9` expected and starts
  when hl-sole frees the machine lock (`~/orun15-queue/k8-sole.log`).

## Judged (iteration 10): kept

k8-sole-50 (`k8-sole.md`) passes every clause of the keep rule: U 0.29 /
0.29 → **0.11 / 0.20** (RH −0.09, LH −0.18), 2.58 m/s against 2.37, pin
p95 854 / 865 °/s with no swing over 900 and no flapping. **leo-v04.2 is
kept.** What it costs: the heel at toe-off fell 0.38 / 0.15 → 0.13 / 0.09,
and the pin's whole-stride p95 is within 50 °/s of O9's 900.
