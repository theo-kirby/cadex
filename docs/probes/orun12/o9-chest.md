# orun12 O9/Q2: the chest box meets the fore legs

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 4).

## The change

On v07-g1-best, the fore legs folded up into the chest frame by as much as
18.4 mm (`o9-baseline.md`). The chest frame's one collision box met only the
floor (contype 4, conaffinity 1), and the fore-limb geoms are group 3
(contype 8, conaffinity 11). The box also stopped at z 320, above the frame's
lower rails: the real mesh's lowest points are z 284–310 between x 10 and
130, and z 284 at x 190, 40–70 mm off the midplane.

feline-v07 was rebuilt with one script change, a contact parameter (O1):

| | size mm | centre mm | meets |
|---|---|---|---|
| before (`26f8972b`) | 260 × 200 × 200 | (170, 0, 420) | floor (conaffinity 1) |
| after (`ee2168d2`, digest `7f1adda6`) | 290 × 200 × 230 | (155, 0, 405) | floor, paws, limbs (conaffinity 11) |

The box now reaches z 290 and starts at x 10. Collision geoms carry no mass
(every body has an explicit `<inertial>`), so masses are unchanged. The
exported MJCF differs from heel2-s1's in that one `<geom>` line. The clip
and every other part of the gallop bundle are identical: heel_from 0.2, as
in heel2-s1. The rebuild took **552 s**, in the background.

## Checked on the traces and on the compiled MJCF

`chest_box.py` replays an evaluation's traces against a model's collision
geoms. It reports the box's distance to every paw and limb geom, frame by
frame. With `--at`, it also poses the full model at that frame from the
placements (hinge angles from relative body rotations; every body lands on
its placement to 0.00 mm) and lists the chest box's live contacts from
MuJoCo's own collision pass, with the filter and excludes applied.

```
PYTHONPATH=cli pixi run python docs/probes/orun12/chest_box.py \
    MODEL_XML ~/cadex-projects/feline-v07/evaluations/v07-g1-best --at 1001:2.76
```

On v07-g1-best's traces (4,510 frames after 1 s, 10 seeds):

| model | geom | filter | build pose mm | frames overlapping | deepest mm | at 1001, 2.76 s |
|---|---|---|---|---|---|---|
| v07-g1 (old box) | c_qdd_wrist_r | no | 44.0 | 54 | 2.5 | 3.1 clear |
| | c_qdd_wrist_l | no | 44.0 | 7 | 0.4 | 3.9 clear |
| | live contacts at 1001, 2.76 s | | | | | **none** |
| `ee2168d2` (new box) | c_qdd_wrist_r | yes | 14.0 | 1917 | 32.5 | −26.9 |
| | c_qdd_wrist_l | yes | 14.0 | 1842 | 30.4 | −26.1 |
| | c_forearm_l / _r | yes | 77.6 | 0 | 0 | 39 clear |
| | hind shins, hock drives | yes | ≥ 145 | 0 | 0 | ≥ 145 clear |
| | live contacts at 1001, 2.76 s | | | | | **c_qdd_wrist_r −26.9, c_qdd_wrist_l −26.1** |

- **At v07-g1's deepest wrist-in-chest frame, the compiled MJCF now
  collides.** Seed 1001 at 2.76 s, 18.4 mm on the real meshes, is now a live
  contact on both wrist drives. The old box was 3.1 to 3.9 mm clear of them,
  and its filter would have ignored them anyway.
- **The new box agrees with the real meshes on how often the leg was in
  the chest.** It overlaps the wrist drives on 1,842 and 1,917 frames. The
  real meshes were over 5 mm deep on 1,717 and 1,892 frames
  (`o9-baseline.md`). The box is the conservative side: up to 32 mm of box
  overlap where the real meshes reach 18 mm.
- **Standing, the box is clear.** It is 14 mm from the wrist drives in the
  build pose, and nothing behind the shoulder comes within 145 mm.
- **v07-g1 held its elbows near the chest a lot.** The wrist drives were
  within 5 mm of the new box on 47–56% of frames. That habit was learned
  without the contact, so the screen that tests the contact trains cold
  (O7).

The rods and battery are not covered directly. The fore cranks and rods
still carry no geom, and the battery is welded to the chest. The rods hang
below the elbow, and the wrist drive's sphere on the elbow axis now meets
the box first, so the rods should stay clear of the battery. The next
screen's evaluation, through `trace_check.py`, will show whether they do.

## Not changed, and why

- **Fore joint stops.** The engine's clearance sweep reports
  `c_chest_frame ∩ c_qdd_wrist_*` (1.1e4 mm³) through `j_shoulder_*`'s
  range, with 14 failing pairs in all. That is the same result as before
  this change: the sweep measures part meshes through joint ranges, and
  neither changed here. A shoulder stop tight enough to keep the wrist out
  of the chest would cut the leg's swing at every elbow angle. The box
  stops only the poses that actually meet the chest, so no stop was added.
- **The fore rod's solref.** The engine writes every `equality/connect`
  as `solref = [2 × timestep, 1]`, which is 0.004 here
  (`CadexDynamics.py`, the closure block). Two timesteps is the stiffest
  time constant MuJoCo's integrator accepts, and `solimp` is already
  0.99/0.9999. So `j_frodbot_r`'s 2.70 mm cannot be stiffened from the
  script. What is left within O1 is load: the gap opens under peak wrist
  torque and contact impulses. The next screen's loop gaps will show whether
  stopping the fore leg against the chest changes them.

## The next screen is queued

`queue_run.py` waits until the project has no live run and the machine's
training slot is free. Then it does the loop's `register`,
`retain_training_view` and `launch`, as an iteration would, inside its own
`systemd-run --user --scope -p MemoryMax=30G`. It refuses if the accepted
revision has moved on from the one it was queued on.

**o9-s1** is queued behind heel2-s1:
- the gallop task on `ee2168d2`, cold;
- 135 iterations, `budget_s` 21,300;
- 8192 envs, unroll 20, seed 0, a checkpoint every 25.

It changes one thing from heel2-s1, the chest box, so the two judge the
contact's cost head to head. Queue log: `~/orun12-queue/o9-s1.log`.

## heel2-s1 at iteration 25

Judged on `gallop_spec` (`evaluations/heel2-s1-25`), next to v07-g1 at the
same iteration:

| | pass | hock down LH / RH | hock at toe-off | heel height mm | top 2 s m/s med / max | worst RMS/rated | peak margin | loop gap max |
|---|---|---|---|---|---|---|---|---|
| v07-g1-25 | 0/10 | 0.28 / 0.03 | 0.19 / 0.01 | 6 / 24 | 0.69 / 1.21 | 1.31 (j_wrist_l) | 0.00 | 3.3 |
| heel2-s1-25 | 0/10 | 0.12 / 0.04 | 0.07 / 0.05 | 14 / 31 | 0.71 / 1.21 | 1.35 (j_wrist_l) | 0.00 | 3.5 |

Iteration 25 is too early to read the clip change from these numbers. v07-g1
had its heels down at 25 and lost them by 75, so the readings that matter are
heel2-s1's checkpoints at 75, 100 and 125.
