# Goal: cadex

<!-- The charter. The human owns this file; no agent role edits it. The agents
     write the plan (short / medium / long) and their bets in PLAN.md. Overrule
     them by editing this file: the loop mints a new directive and re-plans.
     No clocks in here. Agents have no sense of time; rungs are sizes. -->

## Mission

**The north star.** cadex is the best early-stage prototyping tool for robots.
A person writes one prompt: "a 3D-printable walking robot with four MG90S, two
larger servos, these bearings, M3 hardware; it must walk and jump." They come
back later, hours or weeks, and find a printable export, a trained policy, a
video of the policy working, and a report with graphs that says what was tried
and why the winner won. A hardware team runs many cadex machines in parallel,
each testing one idea, and reads the reports. Ouroboros, hypergraph, and cadex
each carry part of that. Everything below serves it.

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
4. **The parts library, broad and real.** Many servos, many actuators, bearing
   families, metric nuts and bolts, and compound mechanisms built from those
   parts: rack and pinion, planetary gearbox, linkages. Every part has
   provenance and a real-kernel test. A robot prompt should never fail because
   a common part is missing.
5. **RL loop follow-ups** that are not already covered by item 2.
6. **The harness's own eyes, headless.** The agent must review what it built
   without a screen: render a model from named angles, produce section views,
   identify the parts of an assembly, run clearance and intersection checks,
   and land the outputs in the project directory. The loop is only as good as
   its review step.
7. **Knowledge from outside.** Web search, papers, and real mechanisms are
   sources. The agent reads them, implements the idea, cites the source in
   the project's `DECISIONS.md`, and tests it against what the repo already had.
8. **Experiments and reports.** Make several variants of one thing (five ankle
   joints), test them all the same way, rank them, pick one, and use it in the
   walk. Every study ends in a report with numbers and graphs a person can read.
9. **The fleet.** A fresh machine becomes a working headless cadex from one
   documented script, so a team can run one experiment per machine. Documented
   and scripted; never provisioned by the loop.

Every unit lands as one small commit plus one record node, verified by the gate
AGENTS.md names for the zone touched. The philosophy holds at every grain:
remove more than we add.

## Done criteria

Claims about the world. Each open box here becomes one gap node on the frontier
at run start, so this section is deliberately short: it is *this run's* frontier,
not the whole backlog. The backlog lives under `## Later criteria` below, where
nothing is seeded. Promote a criterion by moving it up when the frontier lands
or blocks; that is a human edit, and it mints a new directive.

**This run's frontier is the lifecycle walk and the eyes it reviews itself
with.** Inherited-tree reduction is done enough — nt2 removed 2.79M lines — so
it is standing work on the long rung now, not a target.

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
- [x] **Phase 8 `src/Gui` delete commit landed** under the two-commit protocol,
      with the DECISIONS entry and the gate green after it (ADR-214/215, nt2:
      thirteen Gui directories and three retired sources, 3,734 files; release
      build, install and stage fresh, 2,021 engine tests passed / 52 skipped,
      inherited CTest baseline unchanged).
- [x] **Two Phase 13b engine-side removals landed** under the two-commit
      protocol, DECISIONS entries included (nt2 landed six: Help ADR-216/217/218,
      Start ADR-219/220/221 with the GSL submodule, Material ADR-225, the Main
      resource template ADR-226, the Test Tk runner ADR-230/231, and the
      translation updater ADR-232).

**Headless review:**

- [ ] **The agent can see its work without a screen.** One CLI call each, with
      outputs landing in the project directory: render from named angles,
      section view through a named plane, list the parts of an assembly with
      catalog ids, and a clearance and intersection check that names the
      offending pairs. The lifecycle walk's review step uses them.

Every unit (a rule, not a gap; the critic grades it):

- The zone's gate ran and the output is reported honestly; a record node with
  real `## State Impact` targets; ROADMAP checkbox and ADR line where AGENTS.md
  asks for them.

## Later criteria

Real criteria, not seeded as gaps. The planner may not target these; the human
promotes one into `## Done criteria` above when the frontier lands or blocks.
They are here so that a short frontier does not mean a forgotten backlog.

**Inherited-tree reduction:**

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
- [ ] **The catalog is broad enough for a robot prompt**: at least five servos,
      ten actuators, a bearings family, and M2 to M5 nuts and bolts, each with
      provenance and a real-kernel test.
- [ ] **Compound mechanisms exist as parametric library values** built from
      catalog parts: a rack and pinion and a planetary gearbox at least, each
      with a mesh and clearance test.

**Outside knowledge:**

- [ ] **One mechanism in the repo came from a paper or a real product**: the
      source is cited in the project's `DECISIONS.md`, the implementation is
      tested, and the walk built it.

**Experiments and reports:**

- [ ] **A variant study exists**: several variants of one joint generated by
      one script, tested the same way, ranked in a report with a graph, and the
      winner used by the walk.
- [ ] **A research report renders headlessly** from a project's `PROGRESS.md`
      numbers into a document with graphs a person can read.

**Fleet:**

- [ ] **A fresh machine runs the walk** after one documented install script,
      headlessly, with no step that needs a person.

**North star:**

- [ ] **The robot prompt works unattended**: from a prompt naming the servos,
      bearings, and hardware, the loop produces a printable mesh export, a
      trained policy, and a rollout video, with no human step.

**Shell:**

- [ ] **The `hide_render` shell bug from `docs/IDEAS.md` is fixed** with a test
      that fails on the old behaviour.

**RL follow-ups:**

- [ ] **mg-legs tips at the declared shove band, backward first**, with the
      numbers in the project's `PROGRESS.md`.

## Horizon ladder

Sizes, not times. What to do when the rung above is exhausted. The planner
re-plans from this after every maintainer pass and reads the run budget from the
loop, not from this file.

**One thing leads this run: the lifecycle walk, run end to end on this machine.**
nt2 never ran it. It spent 40+ iterations on inherited-tree reduction instead,
ticked 58 ROADMAP boxes, and closed no criterion. Reduction is finished as a
target; it is standing work on the long rung and nothing more.

- **short-term:** (units, one iteration each) **Run the documented headless
  lifecycle entry point end to end, on this machine, and record exactly which
  leg still needs a person or a guess.** That run is the unit. A clean run is
  the evidence that closes the walk gap; a failed run names the next unit. Do
  this before anything else, every time the short rung is empty. Then close the
  named legs one unit each: the remote-training handoff script and doc, the
  GUI-attached mode doc, the domain-doc convention the walk exercises
  (`docs/gear-ratios.md`, `docs/sensors.md`).
- **medium-term:** (gaps, several units each) The headless review calls, one CLI
  call at a time — render from named angles, section through a named plane,
  assembly inventory, clearance and intersection — then wire each into the
  walk's review step as it lands. Then the walk's third mode: the remote
  handoff, scripted and documented, not executed. nt2 left the second-mechanism
  walk close to done (`sage-peak-2689`: the linear carriage ran through the same
  entry point with no dispatch change, and both projects carry comparable
  baseline numbers); finish and evidence it rather than restarting it.
- **long-term:** (directions, and the standing work that never ends) Toward the
  north star, in this order, one rung opened at a time:
  **(1)** the four criteria above — this run's whole frontier;
  **(2)** a fresh Linux machine runs the walk after one documented install
  script, headlessly, with no step that needs a person;
  **(3)** a biped the loop designed from a prompt, trained end to end on that
  machine's GPU.
  Then print-ready export, G-code, the rollout video, each as one more leg of the
  same walk. **Rungs 2 and 3 are parked in `## Later criteria` and are not on the
  frontier.** The planner may not target a parked criterion, and may not treat
  this list as permission to start one: the human promotes a rung by editing this
  file between runs, and the loop picks the new gaps up at the next run start.
  Standing work, always open: keep every gate green, every doc true to the code,
  the delta manifest honest, the project docs current, and the frontier short.
  Inherited-tree reduction lives here now: take a removal only when a change
  makes it obvious and cheap, never as the unit of an iteration. Maintenance is
  real work.

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
- **Never provision cloud machines or spend money.** The fleet is a script and
  a doc until the human runs it.
- **Outside sources are for reading.** Cite every paper, product, or page used
  in the project's `DECISIONS.md`. Never copy code whose license crosses the
  LGPL/GPL boundary AGENTS.md draws; reimplement the idea.
- Never commit `shell/lib/<platform>` contents. Never commit secrets or machine
  paths. Never commit training checkpoints or rollouts; `PROGRESS.md` carries
  the numbers. **The same goes for generated review and probe output** -- a
  record cites the numbers that matter and where the run wrote them, and does
  not carry the dump. nt3 committed 9,321 lines of probe JSON across 129 files,
  42% of its whole diff, which no one will ever read. Never hand-edit `STATE.md`. Never write state nodes; the
  maintainer pass reconciles.
- Builds are long. One unit includes at most one full build. If a gate cannot
  finish inside the iteration, record exactly what was verified and what was
  not, and leave the tree building at every commit.
- Fix forward. Never rewrite or revert earlier commits of this run; a mistake
  gets a new commit and a record node that names it. **A critic rejection is a
  must-fix for the next iteration, not a lost iteration:** the loop no longer
  reverts on reject, so read the must-fix, close it in a new commit, and say in
  the record which rejection it answers. Every one of nt2's six rejections was
  closed this way.
- **Never gate a unit on the wall clock.** No plan item, record, or handoff may
  say "not before 06:30 UTC", "after the quota resets", or "wait for" anything a
  clock decides. The loop has no way to sleep on a clock: it re-reads the time,
  finds it too early, stops, and does it again a minute later. nt3 spent 113
  iterations and two hours doing exactly this. If a unit genuinely cannot start
  yet, it is not the unit -- pick a different one from the frontier and say in
  one line why the first was skipped.
- **Writing about the work is not the work.** A record describes a change; it is
  not one. Neither is an audit, a qualification, a plan, or a handoff addressed
  to a maintainer or planner -- those roles are the same loop and run on their
  own schedule, so an iteration that only asks for them has done nothing. If a
  unit produces no diff outside `.hypergraph/` and `.ouroboros/`, it was not a
  unit.
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
- When a paper and the repo disagree, build the smallest experiment that
  decides, and put the numbers in the report.
- When a review tool would help and does not exist, build the tool as its own
  unit first; do not guess at what the model looks like.
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
- **The record node names the charter criterion the unit advances, and says what
  is still missing before that criterion can be ticked.** A unit that advances
  no criterion on the frontier is not a unit of work: ticking a ROADMAP box is
  not progress by itself. nt2 ticked 58 of them and closed no criterion.
- **The unit changes code, a test, or a document, not only a record.** Naming a
  criterion in prose is not advancing it. The critic rejects a unit whose whole
  diff is under `.hypergraph/` or `.ouroboros/`, unless the unit is a maintainer
  or planner pass, which are the only two that are allowed to be bookkeeping.
  nt3 wrote 22,437 lines over 201 iterations and moved one node on the frontier.

## Reconcile

Maintainer pass every 5 work iterations, or as soon as 3 record nodes are
unreconciled. The run branch is the single-writer branch for this run. The
planner runs after each maintainer pass and owns the `plan` view (PLAN.md);
the maintainer never touches it. The human may merge the run branch into main
with a merge commit at any time; the run continues on its branch.
