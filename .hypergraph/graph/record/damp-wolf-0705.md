---
node_id: 4633fc1d-502a-5abe-8de6-da839d43caca
slug: damp-wolf-0705
title: 'Ouroboros run: nt1 — operator directive'
created_at: '2026-09-05T21:51:39+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

## Why

The goal document, verbatim:

# Goal: nt1 — cadex night test one

## Mission

One night of autonomous, reviewable progress on the cadex frontier, in this
priority order: **file lifecycle (broken)**, **inherited-tree reduction**,
**parts library L2/L3**, **RL loop follow-ups**. Every unit lands as one small
commit plus one record node, verified by the gate AGENTS.md names for the zone
touched. The philosophy holds all night: remove more than we add.

## Done criteria

- [ ] File lifecycle: opening a `.blend` beside its `.cadex` hydrates the model
      (`load_post` queues a rebuild; a test asserts `model_objects_on_open > 0`).
- [ ] File lifecycle: a project locked out by a digest-moving change shows the
      re-accept box in the chat panel (failure code cached on the per-root state)
      and `write_script` recovers it from the UI.
- [ ] File lifecycle: Save-As carries `.cxpolicy` forward (the shell suffix list).
- [ ] Inherited-tree reduction: at least two Phase 13b shell-side removals landed
      under the two-commit protocol (disable commit, delete commit, DECISIONS entry).
- [ ] Inherited-tree reduction: the exploded-view import in
      `cadex_assembly_worker.py` is resolved, or a record node says why not.
- [ ] Parts library: an L2 boards family exists over `CadexCatalog`, with tests
      that include a real-kernel build, and the packaged lifecycle gate passes.
- [ ] Every unit: the zone's gate ran, output reported honestly; a record node
      with real `## State Impact` targets; ROADMAP checkbox and ADR line where
      AGENTS.md asks for them.

## Horizon ladder

What to do if this runs for:

- **the next hour:** orient on STATE.md. Take file lifecycle first: hydrate on
  open (`load_post` -> `on_file_changed` -> queue a rebuild), with a test.
- **the next day:** the lockout re-accept box; the `.cxpolicy` Save-As suffix;
  then Phase 13b shell-side disable commits, one candidate per unit, each its
  own two-commit pair: Cycles, the VSE, grease pencil, the compositor,
  `shell/locale/`, most of `shell/tests/files/`.
- **the next week:** resolve the exploded-view import, then the Phase 8 delete
  commit for `src/Gui`; Phase 13b engine side (trees in no shipped payload, the
  2.1 GB of dev environment in the staged payload); parts library L2 boards,
  then L3 motors and mechanisms; the `hide_render` shell bug from
  `docs/IDEAS.md`; the CLI tool-surface gaps (shell access, `put_asset`) as
  ADR-backed units.
- **the next month:** mg-legs tipping at the declared shove band, backward
  first; 25T horns and servo pigtails from manufacturer STEP sources; reduce the
  fork's delta against upstream wherever a change makes it smaller.
- **the next year:** keep every gate green, every doc true to the code, the
  delta manifest honest, and the frontier short. Maintenance is real work.

## Constraints

- **AGENTS.md is the contract. Obey all of it.** Change-policy zones, the
  two-commit removal protocol, the manifest-and-notice discipline for inherited
  files, the LGPL/GPL one-way boundary, no UI in the engine, protocol changes
  update `docs/INTEGRATION.md` and the shell client in the same commit.
- **Do not start a replacement engine or shell** (Phases 11 and 12 are
  unscheduled by decision).
- Never commit `shell/lib/<platform>` contents. Never commit secrets or machine
  paths. Never hand-edit `STATE.md`. Never write state nodes; the maintainer
  pass reconciles.
- **Do not dispatch training runs** (B7 is blocked on the GPU box) and do not
  touch the GPU box.
- **Headless only.** Never run `pixi run app` or `pixi run install-app`; never
  launch the GUI. Use `pixi run build-shell`, `pixi run gate`, `pixi run
  build-release`, and the pytest suites.
- Builds are long. One unit includes at most one full build. If a gate cannot
  finish inside the iteration, record exactly what was verified and what was
  not, and leave the tree building.
- Fix forward. Never rewrite or revert earlier commits of this run; a mistake
  gets a new commit and a record node that names it.
- Do not edit `.ouroboros/`. Do not edit `.hypergraph/graph/state/`.

## Question policy

How to decide when nobody is here:

- Prefer the reversible option: disable before delete, a CMake option before a
  deletion, a test before a refactor.
- When code and doc disagree, the code wins; fix the doc in the same commit.
- When unsure whether something is in scope, pick the smallest open unit in the
  highest-ranked frontier item.
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
- commit: 5b5894bf997f9533870080b8b438f697a6c661a2

## State Impact

none: operator directive; impacts are declared by the work nodes that follow
