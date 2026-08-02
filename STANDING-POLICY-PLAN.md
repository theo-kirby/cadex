# Standing policy, take four — plan

Working note in the `standing-policy` worktree. Untracked on purpose: promote
to a `docs/MUJOCO.md` M10 slice + ADR-103 when the shape is agreed, or delete.

Project lives at `~/cdx-mjc` (`mg-legs.cadex`, `rebuild.py`, `feasibility.py`,
`measure.py`, `compare.py`, `install_policy.py`, `runs/m9a|m9b|m9c`).

## State of play

Three runs, three tasks, zero recovering policies.

| run | ADR | iters | trainer best | engine survival | note |
|---|---|---|---|---|---|
| M9 (`stand2`) | 099 | 2000 | +0.5118 @1944 | 12/12 @500 → **0/12 @1700+** | in-place shove; braced |
| M9b (`stand3`) | 100 | 500 | +0.2149 @493 | **0/12 everywhere** | stepping task; legs moved |
| M9c (`stand4`) | 101 | 500 | +0.1751 @499 | **0/12 everywhere** | M9b bundle, fixed trainer |

Two blockers, and they are independent.

### Blocker 1 — hazard 19: the two simulators disagree (open, ADR-101 §7)

Same weights, same bundle, mean episode length moves **in opposite
directions**: MJX 58 → 149 steps while stock MuJoCo goes 162 → 39. The
trainer's episode-handling defect (ADR-101) was real, was fixed, and the
rerun reproduced the anti-correlation exactly — so it was not the cause.

Two candidates left. **(b) sampled vs mean action** is the cheap one and goes
first. **(a) MJX vs MuJoCo** is the expensive one and is the only candidate
that would also mean *a policy that stands in the viewport need not stand on
the bench*.

Nothing about the reward or the shove can be evaluated through this.

### Blocker 2 — the episode dies before it is ever pushed (new, from the m9c numbers)

Not previously written down. The M9b/M9c reset variation is

```
tilt 0–15°,  drop 15–45 mm,  spin ±90 °/s     (all three, every episode)
```

and the first shove window opens at **0.8–2.0 s**. Engine-measured episode
length peaks at **162 steps = 1.62 s** at iteration 125 and falls to 39 by
500. So a large fraction of episodes — most of them, late in the run — **end
before the first disturbance lands.** ADR-100 recorded the symptom ("it
cannot absorb its own 15–45 mm drop, folding through `collapsed` at 87.6 mm")
without drawing the consequence: the policy is not failing at stumble
recovery, it is failing at *landing*, and it never reaches the part of the
task the run exists to train.

ADR-100 applied "a curriculum inside the distribution" to the shove
(`newtons=[0.4, 2.0]` spans in-place through stepping) and, in the same pass,
made the *reset* uniformly hard. The reset needed the same treatment and did
not get it.

## Phase A — make the instrument trustworthy (no GPU, hours)

Nothing downstream is worth doing first.

**A1. Record `log_std` in the policy header; add `compare.py --sample`.**
`log_std` is a trained parameter (`training/cadex_train.py:736,806`) and it
reaches no output file, so candidate (b) cannot be tested locally today.
Additive header field; the engine reads with `.get`. Then play m9c's 20
checkpoints both ways. If sampled play reproduces the trainer's curve,
hazard 19 is (b) and is closed here.

**A2. The MJX/MuJoCo divergence harness.** Never been done. Load the same
`model-model.xml` into `mjx.put_model` and into stock `mujoco`, start both
from the identical `solved` keyframe, drive both with the *same fixed*
action sequence (open loop, so no policy feedback amplifies the difference),
and report per-step divergence in `qpos`, `qvel`, contact count and contact
force. One environment, CPU, seconds.

Read, in order:
- the warnings `mjx.put_model` emits and the trainer currently swallows;
- where divergence starts — free flight or first contact;
- what happens if the ground stops being a **box**. It is
  `<geom name="ground/collision0" type="box">`, so every foot contact in
  this model is **box–box**, which is the primitive pair MJX and MuJoCo
  agree on least well. A `plane` ground is the obvious control;
- `integrator="implicitfast"` vs `euler`;
- solver iterations: the export sets none, so MuJoCo runs Newton at 100/50
  and MJX runs its own defaults. Pin both explicitly and re-measure.

**A3. Land the answer as a test, not as a note.** An MJX-gated test in
`cadex_tests` that steps one model through both simulators and asserts they
track within tolerance — same shape as the existing `test_dynamics_policy_*`
suites, skipped in pixi, run from `~/cdx-mjc/.venv`. Hazard 19 cost three
runs because nothing measured this.

**A4. Make the trainer select checkpoints on the number that matters.**
Regardless of what A1–A3 find: the trainer already does a witness rollout per
checkpoint. Add a stock-MuJoCo evaluation there — a handful of episodes, one
env, CPU, seconds — and put **survival** and **engine episode length** into
`progress.json` and the header's curve rows. Then `best.cxpolicy` stops being
a filename that means nothing (hazard 19's closing line), the shell's
Training panel shows the honest number live, and `--iterations` can be
stopped on evidence. This is the change that makes every future run cheaper.

**Gate on Phase A: do not dispatch a GPU run until the trainer's episode
length and the engine's move in the same direction on the same weights.**

## Phase B — the task, once the instrument is honest

**B1. Put the reset on a curriculum inside its own distribution.**
`height_mm=[0.0, 45.0]`, `tilt_degrees=[0.0, 15.0]`, spin `±90 °/s` kept —
same worst case, but easy episodes are in the batch from iteration 0, which
is exactly the argument ADR-100 made for the shove. Re-run the engine's
sixteen-azimuth clearance check and take its number, not an estimate
(hazard 17).

**B2. Move the first shove window earlier and widen the recovery tail.**
0.8–2.0 s assumes the machine is settled by 0.8 s; from a 45 mm drop it is
not. Either delay the window or shorten the drop — but the two have to be
consistent, and today they are not.

**B3. Sagittal first.** ADR-100 §8 parked `direction="sagittal"` and ADR-100
§2 explains why lateral is capped by the mechanism: no ankle roll, no hip
yaw, so effective lateral reach is ~±32 mm against ±50 geometric. Proving
stumble-recovery in the sagittal plane is the achievable demo; asking for
omnidirectional first mixes a mechanism limit into the learning signal. The
azimuth split in `compare.py` already exists to make that call on data.

**B4. What the policy cannot see.** There is no foot-contact channel —
`touch` and `contact_force` are both in `DEFERRED_OBSERVATION_KINDS`
(`CadexDynamics.py:4962`) with stated reasons. A stepping controller
normally wants to know which foot is loaded. Worth costing, **not** worth
doing before Phase A: it is an engine surface, three evaluators, tests and
its own ADR, and it is not on the critical path to the first recovering
policy.

**B5. Budget.** Every run so far has been 500–2000 iterations. ADR-100 §7's
own estimate for learning a stepping recovery from scratch is 10–100× a
500-iteration probe. That spend is only worth making after Phase A.

## Phase C — the run

Feasibility gate (already re-specified as the reach question, ADR-100 §6),
dispatch detached via `remote_train.sh`, watch **engine episode length** (new
in A4) rather than reward, `compare.py --task` against the run's own bundle,
install on survival. Keep the run's bundle beside its checkpoints in
`runs/m10/`, per ADR-099 §5.

## Explicitly not in this pass

- Ankle-roll or hip-yaw servos. A mechanism change; let B3's azimuth data
  argue for it.
- `assembly.reset_joints`. ADR-100 §8 parked it and the reason holds.
- Walking. The toe is still welded.
