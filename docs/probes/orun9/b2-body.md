# orun9 B2: the canonical body on two exported robots

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 10).

ADR-755's implementation is the engine's `api.task(body=...)` resolved into
the bundle's `body`, plus the trainer's `--init-from-base`. Here it is run on
scratch copies of B1's two robots (`/tmp/b2-quad` from `orun9-quad`,
`/tmp/b2-biped` from `orun9-biped`; each is its project's `b1_walk` task with
one `body=` argument added). The check script is outside the repo, at
`~/orun9-progress/b2/real_remap.py`, with its output in `real_remap.txt`.

## What the engine resolved

Both scripts were accepted by `cadex script --set` (quad revision `776d068c`,
biped `8bfd24ed`). Each slot reads `(joint, sign, offset in deg, action)`:

| robot | leg | abd | hip | knee |
|---|---|---|---|---|
| quad | fl | j_abad_fl +1, 0, 0 | j_hip_fl −1, 0, 1 | j_knee_fl −1, 0, 2 |
| quad | fr | j_abad_fr −1, 0, 3 | j_hip_fr −1, 0, 4 | j_knee_fr −1, 0, 5 |
| quad | hl | j_abad_rl +1, 0, 6 | j_hip_rl −1, 0, 7 | j_knee_rl −1, 0, 8 |
| quad | hr | j_abad_rr −1, 0, 9 | j_hip_rr −1, 0, 10 | j_knee_rr −1, 0, 11 |
| biped | l | j_roll_l +1, 0, 0 | j_pitch_l −1, 0, 1 | j_knee_l −1, 0, 2 |
| biped | r | j_roll_r −1, 0, 3 | j_pitch_r −1, 0, 4 | j_knee_r −1, 0, 5 |

- Both robots build their hinges the same way (a +x roll axis on both sides,
  a +y pitch axis), so the derived signs agree across them. The right
  abduction is −1 because outward is −x there. Hip and knee are −1 on every
  leg because forward is −y.
- The offsets are 0 because both reset keyframes are the build pose.
- `body.quat` and `body.gyro` resolved to the IMU's `rot_q*` and `gyro_*`.
- Every actor input on both robots has a canonical name: 33 of 33 on the
  quad (24 slot channels, 7 IMU, the clock), 21 of 21 on the biped.

A copy with abd and hip swapped is refused: "body slot l.abd ('j_pitch_l')
turns about [0.0, 1.0, 0.0] in the IMU's frame, not about its slot's axis
[1.0, 0.0, 0.0] (|cos| 0.000 < 0.9)".

## What the trainer does with it

- **Identity on a real policy.** b1-q1's policy at iteration 150 (the cold
  quadruped that passes its walk spec 10/10) was stamped with the scratch
  quad's layout and passed `check_base_fits`. `remap_from_base` onto the same
  robot then gives a maximum weight difference of 0, a mean difference of 0
  and a std ratio of exactly 1. Of the inputs, 33 were copied, 0 folded and 0
  zero-initialised; of the actions, 12 were copied.
- **The trainer's path runs.** The stamped policy was trained for 2
  iterations at 256 envs (`--init-from-base`, `--critic-warmup 1`, the
  b1-q1 network: 512 256 128, swish) on the scratch quad bundle. It started
  warm, at +12.9 reward a step at iteration 0 (b1-q1's cold start was −6.3).
  The witness agrees to 1.8e-7, and the header records `body` and
  `init_from.base` with the counts and the source's digests.
- **Another family is refused:** "the policy's body is quadruped v1 and this
  bundle's is biped v1".
- `training/test_canonical_body.py` holds the permuted case on a synthetic
  biped: channels and actions reordered, one encoder reversed, and a tail
  added. The remapped policy plays the same actions, and the tail's action
  is 0.

## Not shown here

No warm start across robots has trained yet. That is B3's proof, which
needs a base trained on a randomised family. The cat was not rebuilt with
a `body` block in this iteration. Its ADR-755 mapping (32 of 48 joint
inputs and 16 of 24 actions on slots) is still the decision's text, not a
measurement.
