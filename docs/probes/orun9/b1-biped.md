# orun9 B1: the cold biped, set up by the recipe and blocked in the engine

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 7).

B1's biped half is a cold walk on `~/cadex-projects/orun9-biped` (a copy of
orun8-biped at `c6cc76f`, the 30 cm servo biped with six Feetech STS3215
servos), taking `training/RECIPE.md` step by step, as `b1-quad.md` did for
the quadruped. The task is written, but the engine refuses it at two
points. Neither can be worked around in the project without inventing a
step, so no biped run is launched and the project's accepted revision is
unchanged.

## The task as written

`~/orun9-progress/b1b/b1b-script.py` was built by `make_b1b.py` from the
accepted script.

- **Drive rating (recipe 0.2).** The catalog gives the STS3215 stall torque
  only (16.5 kg·cm at 6 V). Feetech's STS3215 C001 product page gives
  "Rated torque 6.5kg.cm@6V" (`feetechrc.com/74v-19-kgcm-...-steering-gear.html`,
  read 2026-10-17), which is 637.4 N·mm, 0.39 of the catalog's stall.
  - The same page also says "19.5kg.cm@6V" for stall, against the
    catalog's 16.5 at 6 V and 19.5 at 7.4 V (from the spec PDF). The two
    sources disagree.
  - `servo.actuator` takes no rating. So the script declares through
    `assembly.actuator` the same actuator that `servo.actuator` builds
    (stall clamp at 6 V, stall/5 per degree, a twentieth of that as
    damping), with `rated_torque_nmm` added.
- **Reward:** the quadruped's recipe terms, unchanged:
  - `alive` 2; speed as a kernel plus the share of the speed made good,
    weight 4;
  - tracking of pose 3, foot lift 1.5 and contact 1;
  - each drive's excess over rated, weight 2;
  - height, posture and heading.
  The robot's old hand-described walk terms are set aside (spread, slip,
  hover, stride, symmetry).
- **Reference:** a two-foot `walk` at the spec's 160 mm/s (ADR-754), with
  `reference_start="random"`.
- **Spec:** the robot's own walk spec, with W8 `within_rated` added.
- **New privileged observations:** `tau_<joint>` (actuator force) and
  `cl`/`cr` (foot contact).

## What refuses it

1. **A foot `contact` channel breaks the MJCF export check.** With the
   `cl`/`cr` contact observations, `cadex script --set` fails with "The MJCF
   exported for assembly output 'assembly' changed its observation values
   by 0.921986 relative; the accepted maximum is 1e-05"
   (`_verify_exported_sensors`, `CadexDynamics.py`).
   - The touch reading at the solved keyframe differs between the engine's
     compiled model and the reloaded XML.
   - The variant without the `tau_` channels fails the same way, so the
     contact channels alone cause it.
   - The biped's feet are twin-keel capsules. The quadruped's ball feet
     (`b1-quad.md`) pass the same check.
2. **A biped reward cannot name its reference's foot channels.** Without
   the contact channels, the build fails with "reward 'track_lift' names
   'ref_l_lift', 'ref_r_lift', which is not an observation channel of this
   task".
   - The reward vocabulary is first checked against
     `_tracking_candidates` (`CadexDynamics.py:12252`, called at 12881).
     That list hard-codes the four quadruped feet (`lf`, `rf`, `lh`, `rh`),
     while ADR-754's two-foot reference names its channels `ref_l_*` and
     `ref_r_*`.
   - orun8's biped walk task built with the reference only because its
     reward named no lift or down channel.
   - Recipe step 1.1 (track foot lift and contact) cannot be followed on a
     biped until the list carries the reference's own foot names.

## What follows

Both are engine fixes, each with an ADR: the candidate names, and the
contact channel's round trip on capsule feet. After them, `b1b-script.py`
should build as written, and the cold biped run is the next B GPU slot.

## Fixed (iteration 8)

Both refusals are engine fixes. Defect 2 is ADR-756: the candidate foot
channels come from the reference's own feet. Defect 1 is ADR-757. Its cause
was not the sensor. The keyframe stands the flat capsules exactly on the
floor, at −5.2e-18 m in the compiled model and at 0 in the reload, so the
touch read 0.92 N in one and 0 N in the other. A touch at tangency is no
longer compared on export. `b1b-script.py` now builds as written on a scratch
copy of the project; the project's accepted revision is still unchanged,
and no biped run has been launched.

## Launched (iteration 9)

The project now accepts `b1b-script.py` (revision `605e9bc8`, bundle
`b1_walk`, task file `18080849…/b1_walk-task.json`).

**Standing against moving** (orun8's `points` lesson, the same check as
`b1-quad.md`). Over one stride of the bundle's tracking table (47 samples),
a robot standing still at the build stance scores speed 0.135,
track_pose 0.771, track_lift 0.935 and track_contact 0.606 of 1. That is
6.86 a step from the positive terms, against 15.50 for tracking the
reference at 160 mm/s. Moving pays 2.26× standing, about the quadruped's
2.2×, so the weights are unchanged. The script is
`~/orun9-progress/b1b/stand_vs_move.py`.

**b1-b1.** Cold, 300 iterations, 8192 environments, unroll 20, seed 0, and
checkpoints every 50, with the same trainer settings as b1-q1 (recipe 3.1).
It was registered and launched through `cadex_cli.loop` with the dashboard
view retained, in the scope `orun9-b1-b1` (MemoryMax=30G), with a budget of
10,800 s. Each checkpoint is judged on the walk spec's 10 frozen seeds
(9101–9110) with `~/orun9-progress/b1b/judge_b1b.sh`.

At launch it ran at about 6.3 s an iteration on the GPU, an ETA of about
30 min for 300. The reward per step went from −11.6 at iteration 0 to
+0.41 at 9 and +2.87 at 12, much as b1-q1 did (−6.3 at 0, +0.49 at 6).
Not judged yet.
