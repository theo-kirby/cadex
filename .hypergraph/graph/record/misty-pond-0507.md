---
node_id: 5e26d0e6-dfce-5ecd-aafb-89fae66d2643
slug: misty-pond-0507
title: 'Ouroboros run: nt1 [c4f946c1] — operator directive'
created_at: '2026-09-05T22:02:08+00:00'
parents:
- damp-wolf-0705
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

This directive supersedes `damp-wolf-0705`: the operator edited the goal and restarted the run.

## Why

The goal document, verbatim:

# Goal: nt1 — cadex night test one

## Mission

One night of autonomous, reviewable progress on cadex, in this priority order:

1. **File lifecycle (broken)** — the most fragile part of the product.
2. **The robot lifecycle loop, end to end, agent-driven, headless, in the repo.**
   Ideation → design (xscript parts) → assembly (joints, masses, actuator torque,
   sensors) → RL training environment (MJCF export, task) → policy design →
   training → experiment and rollout review → **iterate**: change what did not
   work, update the policy, retrain, compare. Every step must work with no human
   in the loop, driven by the product agent, with every artifact landing in the
   project directory under version control. It must also work with the GUI up
   and with training on a remote machine, without the loop changing shape.
   Part of this: **treat each cadex project directory as its own codebase.** A
   project (say, an actuator) carries the documents a good agent keeps for a
   codebase: `ARCHITECTURE.md`, `DECISIONS.md` (ADRs), `PROGRESS.md`, and domain
   docs it creates and maintains as it works — gear ratios and why a reduction
   went two-stage, the sensor list, actuator selection, what was tried and
   rejected. Version-controlled, agent-maintained, read on every visit.
3. **Inherited-tree reduction.**
4. **Parts library L2/L3.**
5. **RL loop follow-ups** that are not already covered by item 2.

Every unit lands as one small commit plus one record node, verified by the gate
AGENTS.md names for the zone touched. The philosophy holds all night: remove
more than we add.

## Done criteria

File lifecycle:

- [ ] Opening a `.blend` beside its `.cadex` hydrates the model (`load_post`
      queues a rebuild; a test asserts `model_objects_on_open > 0`).
- [ ] A project locked out by a digest-moving change shows the re-accept box in
      the chat panel (failure code cached on the per-root state) and
      `write_script` recovers it from the UI.
- [ ] Save-As carries `.cxpolicy` forward (the shell suffix list).

Robot lifecycle loop:

- [ ] **The walk exists and is tested headlessly.** One documented entry point
      (a CLI prompt or a headless script) takes a mechanism from design →
      assembly → MJCF → task → toy-scale local CPU training → policy verify →
      rollout → review, on this machine, with no human step. The rehearsal in
      `gilded-trail-2519` named the gaps; they are closed or recorded as the
      lifecycle frontier.
- [ ] **Iterate works.** Change a part or a policy parameter, retrain, compare
      against the previous run, and the comparison lands in the project's
      `PROGRESS.md` with the numbers.
- [ ] **Project as codebase.** Creating or first visiting a project scaffolds
      `ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md`; the agent tool surface
      reads and updates them; a convention for domain docs (e.g.
      `docs/gear-ratios.md`, `docs/sensors.md`) is documented and used by the
      walk. Everything is committed in the project directory.
- [ ] **Three modes, one shape.** The walk runs headless (tonight), with the
      GUI attached (documented, not exercised tonight), and with training on a
      remote machine (the handoff is documented and scripted, not executed
      tonight). The loop's steps and artifacts are the same in all three.

Inherited-tree reduction:

- [ ] At least two Phase 13b shell-side removals landed under the two-commit
      protocol (disable commit, delete commit, DECISIONS entry).
- [ ] The exploded-view import in `cadex_assembly_worker.py` is resolved, or a
      record node says why not.

Parts library:

- [ ] An L2 boards family exists over `CadexCatalog`, with tests that include a
      real-kernel build, and the packaged lifecycle gate passes.

Every unit:

- [ ] The zone's gate ran and the output is reported honestly; a record node
      with real `## State Impact` targets; ROADMAP checkbox and ADR line where
      AGENTS.md asks for them.

## Horizon ladder

What to do if this runs for:

- **the next hour:** orient on STATE.md. Take file lifecycle first: hydrate on
  open (`load_post` -> `on_file_changed` -> queue a rebuild), with a test.
- **the next day:** the lockout re-accept box; the `.cxpolicy` Save-As suffix.
  Then the **lifecycle audit**: run the existing rehearsal path headlessly,
  list every step that still needs a human or a guess, and record the result
  as the lifecycle frontier (a decision node with `NEW` impacts). Then the
  **project-as-codebase scaffold**: `ARCHITECTURE.md`, `DECISIONS.md`,
  `PROGRESS.md` created with the project, read by the agent on every visit,
  with a test. Then the first two Phase 13b shell-side disable commits.
- **the next week:** close the lifecycle gaps one unit each — the CLI's shell
  access for the trainer, `put_asset` to bring a policy home, the iterate step
  with a recorded comparison, domain-doc conventions, the remote-training
  handoff script and doc, the GUI-attached mode doc. Resolve the exploded-view
  import, then the Phase 8 delete commit for `src/Gui`. Phase 13b engine side.
  Parts library L2 boards, then L3 motors and mechanisms. The `hide_render`
  shell bug from `docs/IDEAS.md`.
- **the next month:** run the whole lifecycle walk on a second mechanism to
  prove the shape holds; mg-legs tipping at the declared shove band, backward
  first; 25T horns and servo pigtails from manufacturer STEP sources; reduce
  the fork's delta against upstream wherever a change makes it smaller.
- **the next year:** keep every gate green, every doc true to the code, the
  delta manifest honest, the project docs current, and the frontier short.
  Maintenance is real work.

## Constraints

- **AGENTS.md is the contract. Obey all of it.** Change-policy zones, the
  two-commit removal protocol, the manifest-and-notice discipline for inherited
  files, the LGPL/GPL one-way boundary, no UI in the engine, protocol changes
  update `docs/INTEGRATION.md` and the shell client in the same commit.
- **Training is offboard by design and stays so.** `training/` never enters
  CMake, a payload, or `pixi.toml`. The engine verifies policies; it never
  produces them.
- **Training tonight is local CPU, toy scale, bounded**: at most 15 minutes of
  wall clock and 3 GB of memory per training run, in the `training/` venv per
  `training/SETUP.md`. **Never dispatch to the GPU box** (B7 stays blocked) and
  never touch its checkout. Remote training is documented and scripted, not run.
- **Do not start a replacement engine or shell** (Phases 11 and 12 are
  unscheduled by decision).
- Never commit `shell/lib/<platform>` contents. Never commit secrets or machine
  paths. Never hand-edit `STATE.md`. Never write state nodes; the maintainer
  pass reconciles.
- **Headless only tonight.** Never run `pixi run app` or `pixi run
  install-app`; never launch the GUI. Use `pixi run build-shell`, `pixi run
  gate`, `pixi run build-release`, and the pytest suites.
- Builds are long. One unit includes at most one full build. If a gate cannot
  finish inside the iteration, record exactly what was verified and what was
  not, and leave the tree building.
- Fix forward. Never rewrite or revert earlier commits of this run; a mistake
  gets a new commit and a record node that names it.
- Do not edit `.ouroboros/`. Do not edit `.hypergraph/graph/state/`.

## Question policy

How to decide when nobody is here:

- Prefer the reversible option: disable before delete, a CMake option before a
  deletion, a test before a refactor, a doc convention before a new tool.
- When code and doc disagree, the code wins; fix the doc in the same commit.
- When unsure whether something is in scope, pick the smallest open unit in the
  highest-ranked mission item that still has open work.
- When the lifecycle walk needs a decision about a project's structure, choose
  what a careful engineer keeps for a codebase and write the reason in the
  project's `DECISIONS.md`.
- When a gate has pre-existing failures, diff against the recorded baseline and
  say so; do not chase failures that predate the run.
- Never wait for a human. Write the assumption in the record node's `## Why`.

## Exhaustion policy

maintain

## Quality bar

- The gate for the touched zone passes, or the difference from the pre-existing
  baseline is explained with output.
- One logical change per commit. The message states the user-visible outcome,
  the risk, and the test evidence.
- The record node declares real `## State Impact` targets taken from STATE.md.
- Removals carry a `docs/DECISIONS.md` entry. Landed work items tick their
  `docs/ROADMAP.md` checkbox.
- A change to the lifecycle walk updates its doc and the project-doc scaffold
  in the same commit.

## Reconcile

Maintainer pass every 5 work iterations, or as soon as 3 record nodes are
unreconciled. The run branch is the single-writer branch for this run.

## Method

Ouroboros iterations on branch `ouroboros/nt1`: orient, one dispatched unit, record, commit; a maintainer pass reconciles on pressure.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: e6732c4f929c63ad50df04372acb463f9f08b56d

## State Impact

none: operator directive; impacts are declared by the work nodes that follow
