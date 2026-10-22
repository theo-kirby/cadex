# orun16 B1: leo v05 ready to train, and the first screen launched

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 1).

## The bundle

`leo-v05` (project git `64df6aa`, tagged by the owner) is leo-v04.3's
script with two changes (`git diff a6225ab leo-v05 -- script.py`): pin
damping 3.0 → 5.0 N·mm·s/deg on `j_pawpin_*`, and `hock_at_toeoff` out of
`gallop_spec` when the paw is free (`RIGID_FOOT and FREE_PAW`). Accepted
revision **`15d9feb4`** (tag message: sweep 12, static 14, the baseline;
panels pass).

The v05-s1 bundle (`runs/v05-s1/train/`) against hk12-s1's
(`runs/hk12-s1/train/`, leo-v04.3, `7a69ad4a`), compared key by key:

- `gallop-task.json` differs in two places only: the model digest, and
  the success spec, 10 → 9 predicates, `hock_at_toeoff`
  (`heel_down_at_toeoff_share_min`) gone. Rewards, observations, clip,
  terminations: identical, so this is hk12-s1's task.
- `cat_model-model.xml`: `j_pawpin_l` / `j_pawpin_r` damping 0.171887 →
  **0.286479** N·m·s/rad (5.0 N·mm·s/deg); stiffness 0.687549 N·m/rad
  (12 N·mm/deg), springref ±10°, range 0..60° toes-up, friction 0.005:
  unchanged.

## The first screen: v05-s1

- hk12-s1's task on leo-v05 (`15d9feb4`), cold (the trainer refuses a
  warm start across a robot change), seed 1 (hk12-s1's), 50 iterations,
  4,096 envs, unroll 20, a checkpoint every 25, `budget_s` 6,500, through
  `orun13/queue_run.py --expect-revision 15d9feb4` (`cadex_cli.loop`
  `register`, `retain_training_view`, `launch`) in its own
  `systemd-run --user --scope -p MemoryMax=30G`. Launched **07:00:50**
  (`~/orun16-queue/v05-s1.log`).
- **Timing (O8):** iteration 9 at 07:16:15, **15.4 min after launch**
  (hk12-sole 16.6); the trainer's ETA then was 3,414 s for 40 more,
  **~85 s per iteration** with its checkpoint rollouts, ~4,340 s in all.
  The budget (6,500 s) is a cap above the 50 × 85 s + 20% ≈ 5,100 s
  O8 asks plus compile; later v05 bundles: 85 s/it + 20%.
- **The curve tracks hk12-s1's:** reward per step at iterations 0 / 5 / 9
  is 20.58 / 15.86 / 14.66 (hk12-s1: 20.69 / 15.91 / 14.49), episode 75.9
  steps at 9 (80.4), σ 0.858.

## How it is judged

At 25 and 50 on the engine (`orun11/judge.py`, seeds 1001–1010), with
`orun14/paw_floor.py` (U, floor pitch at lift, lifts toes-up of floor),
`orun13/p2_lag.py` and `orun12/legs.py`, against:

| policy | m/s | heels LH / RH | U LH / RH | rotary | flight s | overreach | straight | pin p95 °/s LH / RH (swing) |
|---|---|---|---|---|---|---|---|---|
| hk12-s1-50 (v04.3) | 2.40 | 0.32 / 0.35 | 0.16 / 0.01 | 10/10 | 0.16 | 1/10 | 10/10 | 852 / 577 (385 / 277) |
| hk12-s1x-50 (v04.3) | 2.49 | 0.33 / 0.24 | 0.15 / 0.03 | 10/10 | 0.08 | 0/10 | – | – |

**The question:** does damping 5 bring the pin under O9's 900 °/s p95
(LH max 1,052 on hk12-s1-50), and at what cost in speed, heel share and
U? **Keep v05's damping** if at 50 both pins' p95 is under 900 °/s with
both hinds' U < 0.2 and speed within 0.1 m/s of hk12-s1-50's 2.40;
**stop at 25** only on a blow-up (NaN, collapse) — a cold run at 25 is
still a shuffle (hk12-sole-25: 0.77 m/s), so its speed is not judged.
