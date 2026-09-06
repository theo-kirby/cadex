# Goal: cadex

<!-- The charter. The human owns this file; no agent role edits it. The agents
     write the plan (short / medium / long) and their bets in PLAN.md. Overrule
     them by editing this file: the loop mints a new directive and re-plans.
     No clocks in here. Agents have no sense of time; rungs are sizes. -->

## Mission

Autonomous, reviewable progress on cadex, in this priority order. Ticked
criteria shipped in earlier runs (ADR-186..198); they declare no gap. The agents
re-plan from the ladder after every maintainer pass and record their bets.

1. **File lifecycle** — the most fragile part of the product. Keep it working.
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
3. **Inherited-tree reduction.** Shrink both inherited trees in place.
4. **Parts library L2/L3.**
5. **RL loop follow-ups** that are not already covered by item 2.

Every unit lands as one small commit plus one record node, verified by the gate
AGENTS.md names for the zone touched. The philosophy holds at every grain:
remove more than we add.

## Done criteria

Claims about the world. Each open box is a gap on the frontier until work
falsifies it. Two grains: the first group is the current frontier; the second
is what the planner pulls forward when the first group is landed or blocked.

**File lifecycle (shipped):**

- [x] Opening a `.blend` beside its `.cadex` hydrates the model (`load_post`
      queues a rebuild; a test asserts `model_objects_on_open > 0`).
- [x] A project locked out by a digest-moving change shows the re-accept box in
      the chat panel (failure code cached on the per-root state) and
      `write_script` recovers it from the UI.
- [x] Save-As carries `.cxpolicy` forward (the shell suffix list).

**Robot lifecycle loop:**

- [ ] **The walk exists and is tested headlessly.** One documented entry point
      (a CLI prompt or a headless script) takes a mechanism from design →
      assembly → MJCF → task → toy-scale local CPU training → policy verify →
      rollout → review, on this machine, with no human step. The rehearsal in
      `gilded-trail-2519` named the gaps; they are closed or recorded as the
      lifecycle frontier.
- [x] **Iterate works.** Change a part or a policy parameter, retrain, compare
      against the previous run, and the comparison lands in the project's
      `PROGRESS.md` with the numbers.
- [x] **Project as codebase.** Creating or first visiting a project scaffolds
      `ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md`; the agent tool surface
      reads and updates them; a convention for domain docs (e.g.
      `docs/gear-ratios.md`, `docs/sensors.md`) is documented and used by the
      walk. Everything is committed in the project directory.
- [ ] **Three modes, one shape.** The walk runs headless (exercised), with the
      GUI attached (documented, not exercised while the headless-only constraint
      holds), and with training on a remote machine (the handoff is documented
      and scripted, not executed while the local-only constraint holds). The
      loop's steps and artifacts are the same in all three.
- [ ] **The walk holds on a second mechanism.** The same entry point, with no
      code change specific to the mechanism, takes a second mechanism through
      the whole loop, and both projects' `PROGRESS.md` carry comparable numbers.

**Inherited-tree reduction:**

- [x] At least two Phase 13b shell-side removals landed under the two-commit
      protocol (disable commit, delete commit, DECISIONS entry).
- [x] The exploded-view import in `cadex_assembly_worker.py` is resolved, or a
      record node says why not.
- [ ] **Phase 8 `src/Gui` delete commit landed** under the two-commit protocol,
      with the DECISIONS entry and the gate green after it.
- [ ] **Two Phase 13b engine-side removals landed** under the two-commit
      protocol, DECISIONS entries included.
- [ ] **The fork's delta against upstream is smaller than at the start of this
      run**, measured by the delta manifest AGENTS.md names, and the manifest is
      honest about every inherited file touched.

**Parts library:**

- [ ] An L2 boards family exists over `CadexCatalog`, with tests that include a
      real-kernel build, and the packaged lifecycle gate passes.
- [ ] **L3 motors and mechanisms families exist** over `CadexCatalog`, same
      test shape as the boards family, and the packaged lifecycle gate passes.
- [ ] **25T horns and servo pigtails come from manufacturer STEP sources**, with
      the provenance recorded the way `docs/PROVENANCE.md` asks.

**Shell:**

- [ ] **The `hide_render` shell bug from `docs/IDEAS.md` is fixed** with a test
      that fails on the old behaviour.

**RL follow-ups:**

- [ ] **mg-legs tips at the declared shove band, backward first**, with the
      numbers in the project's `PROGRESS.md`.

Every unit (a rule, not a gap; the critic grades it):

- The zone's gate ran and the output is reported honestly; a record node with
  real `## State Impact` targets; ROADMAP checkbox and ADR line where AGENTS.md
  asks for them.

## Horizon ladder

Sizes, not times. What to do when the rung above is exhausted. The planner
re-plans from this after every maintainer pass and reads the run budget from the
loop, not from this file.

- **short-term:** (units, one iteration each) Orient on STATE.md and PLAN.md.
  Run the documented headless lifecycle entry point end to end on this machine
  and record exactly which leg still needs a person or a guess; a clean run is
  the evidence that closes the walk gap. Then close the remaining legs one unit
  each: the remote-training handoff script and doc, the GUI-attached mode doc,
  the domain-doc convention exercised by the walk (`docs/gear-ratios.md`,
  `docs/sensors.md`). Then the L2 boards family over `CadexCatalog` with a
  real-kernel test and the packaged lifecycle gate.
- **medium-term:** (gaps, several units each) The lifecycle walk on a second
  mechanism. L3 motors and mechanisms families. The Phase 8 delete commit for
  `src/Gui`. Phase 13b engine side, two-commit protocol. The `hide_render` shell
  bug. Each of these is a done criterion above; pull it forward when the
  short-term rung is landed or blocked.
- **long-term:** (directions, and the standing work that never ends) mg-legs
  tipping at the declared shove band, backward first. 25T horns and servo
  pigtails from manufacturer STEP sources. Reduce the fork's delta against
  upstream wherever a change makes it smaller. Propose new directions only
  inside the mission list, and only ones that remove more than they add.
  Standing work, always open: keep every gate green, every doc true to the
  code, the delta manifest honest, the project docs current, and the frontier
  short. Maintenance is real work.

## Constraints

**Standing (true for every run):**

- **AGENTS.md is the contract. Obey all of it.** Change-policy zones, the
  two-commit removal protocol, the manifest-and-notice discipline for inherited
  files, the LGPL/GPL one-way boundary, no UI in the engine, protocol changes
  update `docs/INTEGRATION.md` and the shell client in the same commit.
- **Training is offboard by design and stays so.** `training/` never enters
  CMake, a payload, or `pixi.toml`. The engine verifies policies; it never
  produces them.
- **Never dispatch to the GPU box** (B7 stays blocked) and never touch its
  checkout.
- **Do not start a replacement engine or shell** (Phases 11 and 12 are
  unscheduled by decision).
- Never commit `shell/lib/<platform>` contents. Never commit secrets or machine
  paths. Never commit training checkpoints or rollouts; `PROGRESS.md` carries
  the numbers. Never hand-edit `STATE.md`. Never write state nodes; the
  maintainer pass reconciles.
- Builds are long. One unit includes at most one full build. If a gate cannot
  finish inside the iteration, record exactly what was verified and what was
  not, and leave the tree building at every commit.
- Fix forward. Never rewrite or revert earlier commits of this run; a mistake
  gets a new commit and a record node that names it.
- Do not edit `.ouroboros/`. Do not edit `.hypergraph/graph/state/`.

**This run (the human lifts these by editing this file):**

- **Headless only.** Never run `pixi run app` or `pixi run install-app`; never
  launch the GUI. Use `pixi run build-shell`, `pixi run gate`, `pixi run
  build-release`, and the pytest suites. The GUI-attached mode is documented,
  not exercised.
- **Training is local CPU, toy scale, bounded**: at most 15 minutes of wall
  clock and 3 GB of memory per training run, in the `training/` venv per
  `training/SETUP.md`. Remote training is documented and scripted, not run.

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

creative, bounded: a new direction must serve a numbered mission item, must
remove more than it adds, and is written down as a bet before any code. When
no such direction exists, the long-term rung's standing work is the work.

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
unreconciled. The run branch is the single-writer branch for this run. The
planner runs after each maintainer pass and owns the `plan` view (PLAN.md);
the maintainer never touches it. The human may merge the run branch into main
with a merge commit at any time; the run continues on its branch.
