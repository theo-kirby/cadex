# orun12 P1 (O2a): heel7-s1, heel_pitch on the flat clip with a damped paw pin

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 16).
Queued, not yet trained.

## Why this screen

- heel5-s1 (`heel5-final.md`): `heel_pitch` on the old clip put the heels
  down 0.37/0.36 at 100 iterations, with toe-off 0.84/0.57. It is the P1
  lead, and it continues as heel5c-s1.
- heel6-s1 (`heel6-final.md`): the `flat_feet` clip without `heel_pitch`
  reached 0.19/0.23. It is dominated by heel5-s1, but its clip asks for a
  metatarsus at 7.5° (not 18–22°). In the sim the heel is down at 5–10° on
  0.72–0.77 of stance frames, and above 15° almost never.
- `pin-candidate.md`: the hind paw pin's snaps above 900°/s (11–16% of
  frames on every v07 policy, an O9 failure) are forced by the floor at
  about load ÷ damping. `pin_damp` 3.0 holds a 1 N·m push to 321°/s.

heel7 combines all three: heel5-s1's task, with its 18 terms and
`heel_pitch` weight 10, on the `flat_feet` clip, with `pin_damp` 3.0
(was 0.4). Nothing else changes, and the speed command is not raised
(O2a). `pin_damp` is a declared tuning parameter inside its 0–5 range (O1).
It changes the model digest, and the trainer refuses a warm start across a
changed digest (`training/cadex_train.py:1079`), so the screen is cold.

## The revision

`/tmp/o12/v07-heel7.py` is the accepted heel5 script (`44411418`), changed
in three places:

- `flat_feet=True` on `HEEL_CLIP`;
- `pin_damp`'s declared value is 3.0 instead of 0.4;
- comments.

It is built with `cadex script --set` as feline-v07 revision `de868f8f`,
digest `b1b1245c`. The built bundle was checked against heel5-s1's and
heel6-s1's:

- its 18 reward terms equal heel5-s1's, `heel_pitch` included;
- its clip and tracking table equal heel6-s1's, and `clip_flat.py`
  regenerates the clip exactly (metatarsus 7.5° on both legs while the heel
  is held);
- the MJCF's `j_pawpin_l/r` damping is 0.1719 N·m·s/rad, which is 3.0
  N·mm·s/deg.

## The run

- Cold, 100 iterations, 4096 envs, seed 0, a checkpoint every 25.
- `budget_s` 9,000: heel6-s1 took 7,070 s for 100 iterations on the same
  envs, plus 20% (O8).
- Queued with `queue_run.py --expect-revision`, so it starts when heel5c-s1
  ends and refuses if the project has moved on.
- The first ten iterations are to be timed, since the stiffer pin may
  change the step time.

The stop rule is O2a's: if both heels are under 0.15 at 50, stop it.

It is judged against heel5-s1 and heel5c-s1 at the same iterations, on:

- the heels, toe-off and metatarsus pitch (`legs.py`, `stance_pose.py`);
- the pin's snap share (`paw_pin.py`);
- the loop gap.
