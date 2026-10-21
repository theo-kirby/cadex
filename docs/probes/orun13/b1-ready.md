# orun13 B1: leo v02 ready to train, and the first screen launched

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 1).

## The bundle

The accepted revision of `~/cadex-projects/leo` is `a26dcc27` (digest
`6470befd`), the project's git `3bab5a2`, which is the `leo-v02` tag. It
already retains a `gallop` task bundle (`gallop-task.json`, model
`cat_model-model.xml`), so nothing was rebuilt. The gallop task carries 17
reward terms, `heel_pitch` among them (weight 10, the metatarsus pitch with
the spine counted twice: `2 * q_spine`), 90 observation channels, and
`gallop_spec`'s ten predicates on seeds 1001–1010.

## The clip bends both spine joints (`clip_spine.py`)

The bundled reference has 21 samples over 21 joints, `j_spine` and
`j_spine2` among them. On every sample `j_spine2` equals `j_spine`
(largest difference 0.0°), from −6.98° to +6.98°: the charter's 7° a
joint, 14° of bend in all at each extreme (27.9° peak to peak), a sine over
the stride. The clip's chest sits at −60 mm (the clip's
60 mm body drop from the keyframe) and pitches 4.0–8.0° nose-up.

## `scan_stand` (`stand_hold.py`)

`scan_4` is the chest frame's origin height over the floor (training's
`height_scan_vector`); the keyframe `solved` puts it at 0 mm. Held at the
keyframe angles for 3 s on every drive:

| model | chest z after 0.5 s | after 3 s | pitch | NaN |
|---|---|---|---|---|
| leo v02 `a26dcc27` | −9.4 mm | −10.8 mm | 1.1° | no |
| feline v07 `7ccbf80f` | −10.5 mm | −11.8 mm | 0.8° | no |

leo stands 1.0 mm higher than v07 under the same hold, and v07's
`scan_stand` is −25.2 mm, the value leo carries (it was measured on a
policy's stand, not this hold). The 1 mm difference is under the
parameter's resolution for what it sets (the `height_over_ground` target and
the `collapsed` bar at −95.2 mm, 35 mm under the clip's −60), so
`scan_stand` stays −25.2 and the task stands in the same relation to the
model as heel5's did on v07. Assumption: a policy's stand on leo sits as
far below this hold as v07's did; a stand policy would measure it directly.

## The first screen: g1-s1

- Cold, 50 iterations, 4096 envs, seed 0, unroll 20, a checkpoint every 25,
  `budget_s` 6,000, registered through `queue_run.py` (`cadex_cli.loop`
  `register`, `retain_training_view`, `launch`) with `--expect-revision
  a26dcc27`, in its own `systemd-run --user --scope -p MemoryMax=30G`.
- Launched 2026-10-20 20:58:38.
- **Timing (O8):** iterations 0–9 took 727 s from launch, compile
  included; the trainer's ETA for the remaining 40 was 2,516 s, so
  **about 63 s per iteration** at 4096 envs, against feline v07's ~67 s.
  The second spine joint and its cable did not slow the step. 50
  iterations ≈ 3,250 s; the 6,000 s budget does not bind.
- At iteration 9 the trainer's reward is 10.64/step and the episode 125
  steps (from 53 at 0), rising.

It is judged at 25 and 50 on the engine against orun12's heel5c-s1 final
(910cdb5a: P1 8/10 seeds, heels 0.60/0.61, 2.91 m/s).
