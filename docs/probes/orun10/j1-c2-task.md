# orun10 J1: j1-c2 and j1-c3, the leap task without a wall at the face

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 17).

## Why

j1-c1 was judged 0/10 at every checkpoint (`j1-c1-judged.md`). From
iteration 75 the cat parks its chest at the 300 mm face. The leap task's
`collapsed` termination was `scan_4 < scan_stand − 70 = −95.2 mm`, where
`scan_4` is the chest frame's height over the ground under it. That
termination is a wall at x = 3000: an episode ends unless the chest is
already about 230 mm up as it crosses the face. All 7 early ends fell on
that wall. The reward already pays a leap (13.94 a step against a hold's
9.2–9.6), so this run changes the termination, not the reward or the spec.

## The task (orun10-jump `c65cf762`)

The script (`~/orun10-progress/s14/leap4-script.py`; project commits
`296ed46` and `d9ee0e1`) adds the parameter `leap_floor`. Its default is
0, which leaves every task as it was. At 1, the leap task's collapse is a
floor in the world:

- `com_z < 250 mm`, where `com_z` is the whole cat's centre of mass (the
  `subtreecom` of `c_chest_frame`);
- this is the flat turning task's collapse in the same script;
- the stance's centre of mass is 345.2 mm over the chest frame, so on flat
  ground 250 is the old bound: −95.2 + 345.2 = 250.

`check_c2.py` compared the rebuilt bundle against j1-c1's trained bundle:

- **only `termination` differs**: `scan_4 < −95.2` becomes `com_z < 250`,
  and `tipped` is unchanged;
- reward, goals and observations are equal;
- the trainer loads the bundle;
- the trainer's warm-start check from j1-c1's best policy (iteration 138)
  passes and names `['termination']`, a curriculum key.

## Per-step check (`com_check.py`)

`com_check.py` rebuilds `com_z` on every frame of a judged episode. It uses
each body's mass and inertial offset from the exported model, placed by the
trace's component placements. The rebuilt `com_z` starts at 346.2–348.0 mm
on every seed, against the model's 345.2 at the build pose. Both
terminations were then replayed on every judged episode:

| episodes | n | old collapse (scan wall) fires | new floor fires | lowest `com_z` |
|---|---|---|---|---|
| j1-c1, all 7 checkpoints | 70 | 7 (all 7 early ends, at the face) | 1 | 225.1 mm |
| j1-s1 and j1-s2, all checkpoints | 100 | 2 | 6 | 221.1 mm |

- **At the face the floor never fires.** In j1-c1's 7 early ends, `com_z`
  is 324–333 mm on the frame where the old collapse ended the episode.
- **On flat ground the two agree on a real collapse.** j1-s1 seed 1003 at
  75 and j1-s2 seed 1005 at 25 ended on the old collapse at steps 449 and
  461. The floor would end them at 447 and 460.
- **The floor is not exactly the old bound.** On 5 flat episodes, `com_z`
  dips to 225–240 mm while the chest frame stays above −95.2 mm: a low,
  pitched crouch. Those episodes ran on under the old collapse and would
  end under the floor:
  - j1-c1 at 25, seed 1009, at step 46;
  - j1-s1 seeds 1003 and 1005;
  - j1-s2 seed 1003.

  None of j1-c1's checkpoints from 50 on comes near it: their lowest `com_z`
  is 312.2 mm. The engine's `no_fall` counts a fall lower down, at half the
  first height over the ground (about 173 mm). If j1-c2 is cut off in a
  take-off crouch, the floor is the next thing to lower.

## The runs

Both runs warm from j1-c1's `leap.best.cxpolicy` (iteration 138) with a
10-iteration critic warm-up. The trainer carries σ = 0.383 and the
normaliser's 22.8 M samples from the source. Each is a 100-iteration
screen with 8192 envs and a checkpoint every 25. Each was registered through
`cadex_cli.loop` with `retain_training_view` and launched in its own
`systemd-run --user --scope -p MemoryMax=30G` (`~/orun10-progress/s14/`).

- **j1-c2, at the default learning rate (3e-4), is a dead end.** It took
  `training/RECIPE.md` 3.3's curriculum warm start at face value. 3e-5 is
  written there for a base fine-tune (3.6). Through the warm-up the reward
  per step held at 8.30–8.31, the hold. The first actor update, at
  iteration 11, threw σ from 0.383 to 0.640 and the reward per step fell to
  3.27. That is 3.6's failure: the warm start is lost. It was stopped at
  iteration 11 (`loop.request_stop`, 04:27).
- **j1-c3 is the same run at 3e-5** (j1-s2's rate). Its first actor updates
  keep σ at 0.384 and the reward per step at 8.33–8.36 (iterations 11–13).
  It launched at 04:28 on 2026-10-18 (scope `o10-j1-c3`) and is not judged
  yet.

On this cat, then, a warm start onto a changed task needs 3e-5 too, not only a base
fine-tune.
