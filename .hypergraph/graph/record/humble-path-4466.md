---
node_id: 036c63ff-b815-5f50-af58-b57f5c9aa3c0
slug: humble-path-4466
title: 'Prehistory: mg-legs and the RL grind'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- open-key-6334
summary: Making a two-legged MG90S machine stand and recover. Almost every finding was a lying instrument; B6 is the first policy that steps and lands.
---
## What

The longest continuous investigation in the project: making a two-legged machine
stand, and then recover from a shove. Slices M9, M9b and M9c and their follow-ons
— ADR-088, 090, 092…101, 103…107, 112, 116, 131, 132, 134, 135. The machine is
**`mg-legs`**: a pelvis and two legs built from **MG90S servos**, designed in
Cadex, solved as an assembly, exported to MJCF and trained on MuJoCo/MJX.

## Why

Follows the merge. Once dynamics was ordinary product surface, the author wanted
to know whether it actually worked — and a real machine, trained end to end, is
the only thing that answers that.

## Method

The order is load-bearing and is written down in `docs/MUJOCO.md` §7 because
three machines have now gone through it identically: author the mechanism in an
ordinary xscript project; `assembly.mjcf` exports it with exact OCCT inertias;
`assembly.task` states the control problem as data; `training/cadex_train.py`
solves it on the GPU box; `assembly.policy` verifies the returned weights
against a recorded **witness**; `assembly.rollout` plays it. Evaluation is local,
in stock MuJoCo, over twelve seeds. Every step but the last is cheap; the last
costs hours of GPU time, which is why a feasibility gate runs first.

## Result — and almost every finding is about an instrument, not a policy

- **The leg could not push** (ADR-090): 26.9 N·m needed to hold a crouch against
  12 given, so **0 of 27** scripted push-offs left the ground and no policy could
  ever have hopped. The previous ADR had read that collapse as a deliberate tuck.
- **A tensor core rounded the witness, and four hours died of it** (ADR-094).
- **The policy stood by bracing, not balancing** (ADR-096) — three motors above
  95 % of stall on 100 % of frames — and the task could not have told the
  difference. Found in one glance by a panel that plots each actuator's command
  against its own derived limit.
- **The trainer never ended an episode** (ADR-101): `horizon` was read and never
  used again, so an environment whose policy did not fall over never reset — past
  the last shove window it stood still collecting the alive bonus. **Every reward
  figure recorded before this is non-comparable.**
- **The evaluator compounded its own domain randomisation** (ADR-103 §9):
  `evaluate_episode` multiplies randomisation into the model in place and never
  restores it, and the comparison script reused one model, so after 72 episodes
  link masses and inertias stood at 0.23×–3.9× their exported values, drifting
  the same way down every table. This **withdrew** the headline reward-versus-
  survival inversion that three separate candidates had been queued to explain.
- **The frame was read 90° wrong** (ADR-107): `azimuth_degrees` is about world
  +X and mg-legs faces +Y, so the "forward/backward" columns held the *lateral*
  pushes for an entire investigation, inverting the motivation for adding ankle
  roll.
- **No reward term had ever named the feet** (ADR-112). Both spatial terms
  measured the centre of mass against the fixed floor point the machine stood on
  at t=0, so moving a foot changed the reward by nothing and a *completed* step
  cost −0.57/step for ever. The machine was never refusing to move its feet; it
  was stepping in place.

Re-referencing both spatial terms to the foot centroid and adding a
capture-point term produced **B6**: 2,500 iterations, 3.9 h, and checkpoint 2400
scores **6/12 on "stepped AND survived" — a number that had been zero in every
run this project had ever done**, across five prior runs and all their
checkpoints. Selection was by stepping-and-surviving, **not by reward**, for the
third measured time.

Two engine capabilities came out of the grind and cost one table row each:
`centre_of_mass_velocity` (ADR-112) and `centroidal_angular_momentum`
(ADR-116) — the second because every B6 death is `tipped` and not one is
`collapsed`, so the failure this project keeps measuring is rotational.

Also settled here: MJX and stock MuJoCo agree to float64 machine epsilon with
collision disabled and with a `plane` floor, and differ **only about box against
box** — which is what `export_mjcf` writes for every grounded body (ADR-103).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW rl-training-loop — a real biped, a policy that steps and lands, and a long list of instruments that lied.
- target: NEW dynamics-and-control — two new observation kinds; MJX and MuJoCo agree except about box-against-box contact.
