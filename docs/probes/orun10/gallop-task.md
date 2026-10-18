# orun10 S1: the gallop sprint task, and its first run (s1-g1)

Verified against source: 2026-10-17. Frozen evidence (orun10, iteration 2).

## Why a task of its own, trained cold

The fastest policy on this cat, orun9's c1-c6, runs a trot clock (2.74 m/s,
`sprint-baseline.md`). A warm start from it onto a gallop is refused by the
trainer. The reference clip and the goal draws are task keys that a
curriculum step may not move (`check_curriculum_change`, RECIPE §3.5). The
refusal is right: the actor reads only the clock's phase (`ref_sin`,
`ref_cos`), and that phase means a trot to c1-c6's weights. orun7 reached its
gallop the same way, cold on a rotary-gallop reference (f1-g1, then
f1-g2 warm with reward-only changes). Separate policies are allowed (O4).

## The reference: as long a stride as the legs reach at 2.4 Hz

`CadexGait.generate` on the exported model (`f321f89c`, keyframe `solved`).
The probe is `~/orun10-progress/s2/reach*.py`, outside the repo. At 2.4 Hz
it gives:

| duty | stride 600 | 700 | 800 | 900+ |
|---|---|---|---|---|
| 0.25 (rotary gallop) | ok | ok (swing 60 mm) | refused | refused |
| 0.20 | ok | ok | refused | refused |
| 0.15 | ok | ok | ok (swing 60) | refused |

At 800 mm or more, the right fore cannot reach its swing target at 0.29–0.33
of the stride: `j_shoulder_r` and `j_wrist_r` are at a stop. At 1–2 m the
hind (knee, hock, paw pin) or the left scapula and wrist miss by 2–104 mm.
The clip is kinematic, with the body at a fixed height. Its stride is
therefore the stance sweep plus the swing, not the flight distance, so it
cannot show a 1.8 m stride. It sets the **timing**. The task uses the rotary
gallop at duty 0.25, a 700 mm stride and 1.68 m/s, which is 2.4 Hz. That is
orun7's 600 mm, one step longer. The clip has two flights a stride (0.35–0.5
and 0.85–1.0).

## The task (`gallop`, revision `e6e3c0eb`)

The task is modelled on f1-g2's reward, which reached 4.25 m/s on orun7's
model. It has 12 terms:

- **alive** (4);
- **track_speed** (9): `min(comv_x, 5500) / 5500`, linear up to 5.5 m/s;
- **track_pose** (1.5), **track_lift** (1.5) and **track_contact** (4),
  against the clip;
- **near_peak** (−0.5): `(tau/peak)^10`, summed over the 22 drives;
- **height over the ground** (`scan_4`), **posture**, **sideways**,
  **yaw rate**, **heading** (`imu_qz`) and **tail**.

Rated RMS is not priced (O3): it is reported. Drives are clamped at peak by
the model. There are no goals: it is one speed, straight along +x (O5). The
actor reads the height scan, as C1 does, so a leaping task on the same inputs
may warm from it. Its spec, `gallop_spec`, is the sprint spec without goals:
`completes`, `no_fall`, `upright` ≤ 30°, `straight` ≤ 25°, and
`max_forward_speed_2s_mm_s` ≥ 5000, on seeds 1001–1010.

## s1-g1

The run was registered through `cadex_cli.loop` with `retain_training_view`,
and launched in its own scope (`systemd-run --user --scope -p
MemoryMax=30G`). The task digest is `db88833c…`. The run is cold, with
8192 environments, unroll 20, 300 iterations and a checkpoint every 50. It
trains at about 13.7 s an iteration on the 5090. Its checkpoints at 50–300
are judged on `gallop_spec` with the engine, each one, by a later
iteration.
