# orun15 B1: leo v04 ready to train, and the first screen launched

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 1).

## The bundle

`leo-v04` (project git `939cfb1`, `cadex script --set leo_v04.py`) is
tr-sole's script (`~/orun14-tr.py`, revision `32890126`) plus the easy
return spring on each paw pin. The diff is only the spring: `PAW_K,
PAW_PRELOAD = 4.0, 10.0`, a `spring_h*` coil part welded to the metatarsus,
the hinge's `spring_nmm_per_deg` / `spring_rest_deg`, and a comment that
orun14's `paw_fold` is not in the task. The task is tr-sole's 19 terms on
the `flat_feet="sole"` + `trail_feet` clip.

- Accepted revision **`e560f053`**, digest `13bd96b9`; bundle task
  `8f3cb972`, model `bce1020d`.
- **The spring is in the bundle** (`runs/sp-sole/train/cat_model-model.xml`):
  `j_pawpin_l` and `j_pawpin_r` carry `stiffness="0.229183"` N·m/rad
  (= 4 N·mm/deg) and `springref` ±0.174533 rad (10°) on the toes-down side
  of the flat stop (left range −60..0° with rest +10°; right 0..60° with
  rest −10°). Damping 0.171887 N·m·s/rad (3.0 N·mm·s/deg), friction
  0.005 N·m, as v03.
- **Clearance** (`cadex clearance`, then `--sweep`, project commits
  `b61d663` and `35cf83d`, 9,180 static pairs, against v03's 8,911: the
  coil adds pairs): `orun13/clearance_diff.py` against orun14's baseline
  (`clearance-baseline.md`, project `77a02d8` / `825ddec`) gives **static
  14 → 14, swept 8 → 8 distinct pairs, 0 new**. The build's assembly
  validation is `solved`.

## The stand with the spring (`orun14/stand_pin.py`)

On the v04 model, held at the keyframe on every drive for 3 s:

| t s | chest z mm | pitch ° | pin L / R ° |
|---|---|---|---|
| 0.5 | −9.5 | 1.3 | 0.3 / −0.3 |
| 3.0 | −11.6 | 1.0 | 0.3 / −0.3 |

- No NaN. Each pin seats on its flat stop, 0.3° into the soft limit on the
  toes-down side, so the coil presses it there with 4 × 10.3 ≈ 41 N·mm.
  Pin peak speed 99°/s while settling (v03: 105).
- The paws are on the floor (−0.3 mm), the heels 64 mm up: at the hock-0
  home the foot stands on its toes, as on v03. The stand is v03's to
  0.1 mm, so **`scan_stand` stays −25.2**.
- **The clip:** 21 samples over 23 joints, `j_spine` −6.98..+6.98° with
  `j_spine2` equal on every sample (0.000°); the clip's pin −8.4..0° (left)
  and 0..7.4° (right), ADR-785's trailing paw.

## The first screen: sp-sole

- tr-sole's task on v04 (`e560f053`), cold, so the spring is the one
  change against tr-sole: 50 iterations, 4096 envs, seed 0, unroll 20, a
  checkpoint every 25, `budget_s` 4,800, through `orun13/queue_run.py`
  (`cadex_cli.loop` `register`, `retain_training_view`, `launch`) with
  `--expect-revision e560f053`, in its own
  `systemd-run --user --scope -p MemoryMax=30G`. Launched 13:41:36.
- **Timing (O8):** iteration 9 at 855 s, iteration 6 at 648 s: **69 s per
  iteration** at 4096 envs (v03: 69), about 230 s of compile before
  iteration 0. The trainer's ETA at iteration 9 was 3,419 s for 40 more
  (85 s/it with its checkpoint rollouts): about 4,270 s in all, inside the
  4,800 s budget. Later v04 bundles: budget 85 s/it plus 20%.
- Iteration 9: 13.73 reward/step, episode 82.7 steps (from 24.4 at 1),
  rising; σ 0.895.

It is judged at 25 and 50 on the engine (`orun11/judge.py`, seeds
1001–1010) with `orun14/paw_floor.py` for U, against orun14's tr-sole-50
(2.40 m/s, heels 0.34 / 0.19, U 0.34 / 0.63, rotary 0 / 10), p1-flat-50
(1.46 m/s, heels 0.31 / 0.52, U 0.22 / 0.38, rotary 10 / 10), orun13's
g7-hock75 (heels 0.46 / 0.41, `hock_down` 6 / 10, 2.60 m/s) and orun12's
heel5c-s1 (P1 8 / 10, heels 0.60 / 0.61, 2.91 m/s). **Keep rule:** U under
0.2 on both legs at a speed within tr-sole-50's spread (2.14–2.59 m/s),
with the heel share no worse than tr-sole-50's.
