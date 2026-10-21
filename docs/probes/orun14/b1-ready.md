# orun14 B1: leo v03 ready to train, and the first screen launched

Verified against source: 2026-10-21. Frozen evidence (orun14, iteration 1).

## The bundle

`leo-v03` (project git `ea9554e`, revision `12e665a4`) is g4-peak's script
(`b4680361`) plus the free paw pin and orun13's `roll_brake` (g9-roll's
term, weight −4, stopped at 37 iterations and never judged). The charter
starts from g4-peak's task, and `roll_brake` charges the hock's heel-up
speed while the paw is down and the heel up: on the free pin that is the
push-off roll the pin is for (O2). It is now added only `if not FREE_PAW`
(the welded-paw path keeps it). No geometry changed.

- Rebuilt: revision **`bc287c9c`**, project git `36b4a4c`
  (`cadex script --set orun14-g1.py`), 18 reward terms (g4-peak's 18:
  `heel_pitch` peaked on the flat sole, `hind_flat`, `plantigrade` among
  them), task `736a013a`, model `c31ad2fc`.
- Verdicts: static clearance 14 failing pairs (heel/metatarsus 168 / 154
  mm³, front and hind crank/rod at 0 mm), against the baseline's 16; the
  joint sweep 12 failing pairs, all front-leg parts against the chest
  through the shoulder and scapula, against 12–13; mounting pass (30/30);
  panels 0 failing. No new pair. Same model as `leo-v03`, so these are
  its verdicts too.

## The stand on the free paw, and the clip (`stand_pin.py`)

On the v03 model, held at the keyframe on every drive for 3 s:

| t s | chest z mm | pitch ° | pin L / R ° |
|---|---|---|---|
| 0.5 | −9.5 | 1.3 | 0.3 / −0.3 |
| 3.0 | −11.6 | 1.0 | 0.3 / −0.3 |

- No NaN. Each pin rests on its flat stop (0.3° into the soft limit), at
  most 105°/s while settling. The paws are on the floor (−0.3 mm) and
  the heels 64 mm up: at the hock-0 home the foot stands on its toes.
- `j_pawpin_*`: range 0..60° toes-up (left −60..0, right 0..60), no
  stiffness, damping 3.0 N·mm·s/deg, friction 5 N·mm, as built.
- v02 settled to −10.8 mm under the same hold (orun13 `b1-ready.md`);
  v03 sits 0.8 mm lower, under what `scan_stand` resolves, so
  **`scan_stand` stays −25.2**. A policy's stand would measure it
  directly.
- **The clip's spine:** 21 samples over 23 joints, `j_spine` −6.98..+6.98°,
  `j_spine2` equal on every sample (largest difference 0.000°).
- **The clip's paw pin:** the solved reference turns the pin 0 to 27.0°
  (left) and 0 to 32.3° (right) toes-up of the metatarsus. The policy
  does not act on it; it is the reference's kinematics.

## The first screen: g1-free

- g4-peak's task on v03 (`bc287c9c`), cold, 50 iterations, 4096 envs,
  seed 0, unroll 20, a checkpoint every 25, `budget_s` 4,000, through
  `orun13/queue_run.py` (`cadex_cli.loop` `register`,
  `retain_training_view`, `launch`) with `--expect-revision`, in its own
  `systemd-run --user --scope -p MemoryMax=30G`. Launched 05:29:47.
  Cold, not warm from g4-peak-50: that policy's habits are the welded
  paw's toe-off roll and RH taps, the things the pin is meant to undo.
- **Timing (O8):** iteration 0 at 221 s (compile), iteration 9 at 844 s:
  **69 s per iteration** at 4096 envs (v02: 63). The trainer's ETA for the
  remaining 40 was 3,377 s (84 s/it with its checkpoint rollouts), so
  50 iterations may reach ~4,200 s against the 4,000 s budget: it may end
  `budget_exhausted` a few iterations short of 50, after the 25
  checkpoint. Later bundles on v03: budget about 85 s/it plus 20%.
- Iteration 9: 13.90 reward/step, episode 90 steps (from 47), rising.

It is judged at 25 and at its end on the engine against orun13's
g4-peak-50 (heels 0.44 / 0.22, 2.43 m/s), g7-hock75 (heels 0.46 / 0.41,
`hock_down` 6/10, 2.60 m/s) and orun12's heel5c-s1 (P1 8/10, heels
0.60 / 0.61, 2.91 m/s).
