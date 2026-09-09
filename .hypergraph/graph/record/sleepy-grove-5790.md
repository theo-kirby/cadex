---
node_id: 38af6a52-33e9-586a-b007-8d954352874d
slug: sleepy-grove-5790
title: A task MJX cannot build is refused where it is written
created_at: '2026-09-09T04:04:22+00:00'
parents:
- sharp-vine-8567
summary: ''
---
## What

`assembly.task` now refuses a model MJX cannot build, at the moment the
task is declared. ADR-281, one commit (`eed442cd`).

`CadexDynamics.candidate_collision_pairs` writes out MuJoCo's static
contact filter — explicit `<pair>` rows, exclusion signatures, the
same-weld and parent-child filters, the contype/conaffinity masks —
and `mjx_unsupported_collision_pairs` reports the survivors whose geom
type pair MJX has no contact function for. `task_records` raises
`mjx_unsupported_collision_pair` naming both geoms, both bodies and both
kinds. `assembly.mjcf`, `assembly.rollout` and the simulation trace are
untouched.

Docs: ADR-281, `docs/MUJOCO.md` §5 hazard 20, `docs/CLI.md` §2 rewritten
from "the refusal is the trainer's" to what the engine now does, ROADMAP
line. Both doc dates bumped.

## Why

The overseer's dispatch, and charter criterion **"The walk exists and is
tested headlessly"** (`crisp-reef-5607`) — the single defect standing
between the fresh walk and the criterion.

`golden-dune-8756` measured it: `ot4-mix52` passed design from nothing in
1,135.85 s (four-body closed-loop slider-crank, mobility 1, worst closure
residual 0.0015 mm) and died 2.27 s into `train` on `mjx.put_model`
raising `NotImplementedError: (mjGEOM_CYLINDER, mjGEOM_BOX)`. ADR-280 made
that legible; this stops it.

**The overseer's hypothesis was that the exporter emits a pair MJX
rejects. It does not.** The script authored
`assembly.collision("cylinder", radius_mm=rd/2, length_mm=rail_len)` for
the frame's guide rail; the exporter emitted exactly that. The cylinder is
legal MuJoCo, stock MuJoCo simulates it against a box, and every engine
check passed. So this is a **real MJX kernel limit**, not an exporter
defect — and the fix that serves the criterion is not to change the
geometry but to move *when the author finds out*. A task is only ever read
by the offboard trainer (ADR-084), so refusing there costs no other
surface and lands the message in the design turn that chose the shape.

Assumption taken without a human: refuse rather than warn. Reversible (one
call site), and a warning on a leg nobody watches is what ADR-280 already
had to fix once.

The short plan's unit 1 — trimming the scaffold guide to carry this
constraint in prose — is now largely redundant: the engine states it, by
name, with the correction. Left for the planner rather than folded in
here.

## Method

1. Reproduced from the artifacts the last walk left on disk: the trainer,
   run against `runs/fresh52/train/slider_tracking-task.json` in
   `~/cadex-train-venv` with `JAX_PLATFORMS=cpu`, `--iterations 1
   --envs 4`. No model dispatch, no `--resume`. Same `NotImplementedError`.
2. Read `mjx._src.io._put_model_jax` and `collision_driver.geom_pairs` to
   find which pairs are actually enumerated, and printed the full
   `has_collision_fn` matrix: four unimplemented pairs among the kinds a
   Cadex script can write plus ellipsoid — box/cylinder, cylinder/mesh,
   box/ellipsoid, ellipsoid/mesh.
3. Confirmed the offending pair is `comp_frame/collision1` (cylinder,
   frame) against `comp_coupler/collision0` (box, coupler) — two joints
   apart, so neither the joint exclusions nor the parent-child filter
   separates them.
4. Wrote the filter in `CadexDynamics` and cross-checked it against
   `mjx.geom_pairs` on the walk's own exported XML from the train venv:
   3 pairs each, sets identical. Checked the static table against
   `mjx.has_collision_fn` from the same venv: exact match.
5. Wired the refusal into `task_records`, on `reloaded` — the model
   compiled from the exported bytes, which is what the trainer loads.
6. Wrote `test_dynamics_mjx_geom_pairs.py` (6 tests + 1 MJX-gated).

**One claim did not survive its own test.** The first correction text
offered `collides_with=[]` as the escape for a decorative shape. The test
that asserted it failed: MuJoCo's mask test is an `or` over both
directions, so a shape declaring it collides with nothing is still
touchable by a shape that collides with everything. The module's own
`contact_masks` docstring says so and I had written past it. Correction
and tests now say both sides must agree, and two tests pin the difference.

## Result

**Green.** Engine suite 2,099 passed / 54 skipped in 266 s. CLI suite 289
passed in 231 s. The MJX-gated table test skips under pixi and matches
real MJX when run from the training venv.

The refusal, verified against the model that actually failed:

    task would train a model MJX cannot build: comp_frame/collision1 on
    comp_frame and comp_coupler/collision0 on comp_coupler can touch, and
    MJX has no cylinder/box contact.

This does not by itself close `crisp-reef-5607`. What is still missing:
a fresh walk whose design turn, now told at task-declaration time, authors
a trainable mechanism and gets through `train`, `declare`, `rollout` and
the four eyes. That is the next unit and it costs a model dispatch. Two
outcomes are both informative: the design turn takes the correction and
the walk completes, or it does not and the refusal itself is the evidence
that the guide, not the engine, is where the constraint has to live.

The unreconciled tail is now 2 nodes; a maintainer pass is due soon.

Dispatch closed: 1 unit — assembly.task refuses the four geom pairs MJX
cannot build, naming the geoms, bodies and kinds, with a regression that
fails on the previous source; ADR-281, both suites green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: eed442cd0e37b094af5bf316b5dde95612b5b539

## State Impact

- target: crisp-reef-5607 — the walk's train leg no longer fails opaquely inside MJX: assembly.task refuses the four collision type pairs MJX has no contact function for (box/cylinder, cylinder/mesh, box/ellipsoid, ellipsoid/mesh), naming both geoms, both bodies and both kinds at declaration time. Verified against the ot4-mix52 model that failed. The criterion still needs a fresh walk that gets through train and the four eyes.
- target: salty-isle-4063 — CadexDynamics gains candidate_collision_pairs (MuJoCo's static contact filter, written out because the engine may not import MJX) and mjx_unsupported_collision_pairs; task_records raises mjx_unsupported_collision_pair. The filter reproduces mjx.geom_pairs exactly on the walk's exported model and the table matches mjx.has_collision_fn. assembly.mjcf and assembly.rollout are unchanged.
