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
criteria shipped in earlier runs; they declare no gap. The agents
re-plan from the ladder after every reconcile and record their bets.

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
not the whole backlog. The backlog lives under the later-criteria section below,
where nothing is seeded. Promote a criterion by moving it up when the frontier
lands or blocks; that is a human edit, and it mints a new directive.

**Why this section changed for ot5.** Four runs ticked nothing, and ot4's digest
named the cause: each criterion was a compound claim no single unit could finish,
so nobody would declare one true. Every open box below is now **one claim with
one piece of evidence** -- a file the run writes, or a command that exits 0 --
and the record node that produces that evidence is allowed to say "this ticks
criterion N". The ticks above the line are the human's, made on the evidence the
state graph holds from ot4 (`crisp-reef-5607`, `swift-dusk-2951`,
`witty-spark-2613`, `damp-moon-9297`).

**This run's frontier is three things: the eyes that see motion, a real gait
on the GPU, and the first variant study with a report a person can read.**

**File lifecycle (shipped):**

- [x] Opening a `.blend` beside its `.cadex` hydrates the model (`load_post`
      queues a rebuild; a test asserts `model_objects_on_open > 0`).
- [x] A project locked out by a digest-moving change shows the re-accept box in
      the chat panel (failure code cached on the per-root state) and
      `write_script` recovers it from the UI.
- [x] Save-As carries `.cxpolicy` forward (the shell suffix list).

**Robot lifecycle loop (shipped in ot4; ticked by the human on 2026-09-12):**

- [x] **The walk exists and is tested headlessly.** `cadex walk` takes a
      mechanism from design through training, verify, rollout and review with no
      human step; four mechanisms have run it from nothing on this machine
      (`chilly-basin-7378`, `dry-falcon-5463`).
- [x] **Iterate works.** Change a part or a policy parameter, retrain, compare
      against the previous run, and the comparison lands in the project's
      `PROGRESS.md` with the numbers.
- [x] **Project as codebase.** Creating or first visiting a project scaffolds
      `ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md`; the agent tool surface
      reads and updates them; a convention for domain docs is documented and
      used by the walk. Everything is committed in the project directory.
- [x] **Three modes, one shape.** Headless exercised; GUI-attached documented
      leg by leg (ADR-269); remote scripted as `--remote --detach` and
      `--complete` (ADR-282), not executed against a live box.
- [x] **The walk holds on a second mechanism.** The same entry point, no
      mechanism-specific code, four rigs including one with a passive joint;
      every project's `PROGRESS.md` carries the same columns.

**Inherited-tree reduction (shipped):**

- [x] At least two Phase 13b shell-side removals landed under the two-commit
      protocol (disable commit, delete commit, DECISIONS entry).
- [x] The exploded-view import in `cadex_assembly_worker.py` is resolved, or a
      record node says why not.
- [x] **Phase 8 `src/Gui` delete commit landed** under the two-commit protocol,
      with the DECISIONS entry and the gate green after it (ADR-214/215).
- [x] **Two Phase 13b engine-side removals landed** under the two-commit
      protocol, DECISIONS entries included (nt2 landed six: ADR-216..232).

**Headless review (shipped in ot4; ticked by the human on 2026-09-12):**

- [x] **The agent can see its work without a screen.** `cadex render`,
      `cadex section`, `cadex inventory` and `cadex clearance` each land their
      output in the project directory, and the walk's review step runs all four
      (`idle-pond-4961`).

**Motion-aware eyes (this run):** the two eyes that ot4 found measuring a still
mechanism. The engine half of the first landed as ADR-283; the walk does not use
it yet.

- [ ] **C1. The walk's clearance is swept, not posed.** A `cadex walk` run on a
      project that declares clearance pairs writes `review.json` whose clearance
      block carries `scope: "rollout trace"` (or equivalent wording chosen in
      the unit), the number of frames measured, and a `closest_approach` naming
      the pair, the millimetres and the frame index. Evidence: that file from
      one walk on this machine, and a `cli/tests` test that fails if the scope
      falls back to the initial pose.
- [ ] **C2. A walk names an interference that exists only in motion.** One
      project in `~/cadex-projects/` whose initial pose is clear but whose
      rollout brings two named parts within the declared clearance; the walk's
      `review.json` reports it with the frame index, and the project's
      `PROGRESS.md` row says so. Evidence: the two files.
- [ ] **C3. The derived section cuts the part that moves.** On every ot4 walk
      project that recorded a `moved: true` entry under `section.missed_objects`
      (`ot4-cart` is one), re-running `cadex section` with no `--offset-mm`
      produces a cut whose `missed_objects` has no `moved: true` entry.
      Evidence: the section JSON for each such project, and a `cli/tests` test
      pinning the ranking term that made it so.

**Gait on the GPU (this run):** the loop runs on the machine with the 5090 and
the training bound is lifted to what a gait needs (see Constraints). The
standing benchmark is `mg-legs`; its project lives outside this repo at
`~/cdx-rl/projects/mg-legs.cadex` and is copied, never edited in place, into
`~/cadex-projects/mg-legs/` as the first unit.

- [ ] **G1. mg-legs walks through the unchanged entry point on this machine.**
      `cadex walk` on the copied project, training on the GPU inside the bound,
      exits 0 with every leg run and all four eyes in `review.json`. Evidence:
      that `review.json` and the project's `PROGRESS.md` row.
- [ ] **G2. A GPU-trained policy steps and survives.** A checkpoint from a run
      under this charter's bound scores at least half on the conjunction
      "stepped at least 10 mm *and* survived" over at least twelve rollout
      episodes -- the criterion `~/cdx-rl/README.md` measures B6 (6/12) and
      experiment 003 (17/24) against -- selected by that table and not by
      reward, with the table in the project's `PROGRESS.md`. Evidence: the
      `PROGRESS.md` row and the `.cxpolicy` digest it names.
- [ ] **G3. mg-legs survives the declared shove band, backward first.** Over
      the declared `assembly.disturbance` band, fewer than half of the episodes
      end `tipped`, and the backward direction is measured separately with its
      own number. Evidence: the numbers in `PROGRESS.md`, produced by a table
      the record node cites by path.

**Variant study and report (this run):**

- [ ] **V1. Five variants of one joint from one script.** One xscript project
      whose parameters generate at least five variants of one joint (a hip, an
      ankle, a knee -- the unit chooses and writes why in the project's
      `DECISIONS.md`), each built by `cadex params --set`, each passing the same
      review. Evidence: the project, and its `PROGRESS.md` with one row per
      variant.
- [ ] **V2. The variants are ranked and the winner is used.** All five go
      through the same walk with the same task; a ranking by the stepping table
      or the task's own objective lands in `PROGRESS.md`; the winning variant's
      parameters are the project's committed defaults. Evidence: the ranking
      table and the commit that set the defaults.
- [ ] **V3. A report renders headlessly from `PROGRESS.md`.** One CLI call
      turns a project's `PROGRESS.md` into a document with at least one graph
      (reward curve, ranking bar chart) under the project's `report/` directory,
      with no display and no tokens. Evidence: the rendered file from the V2
      project and a `cli/tests` test that renders a fixture.

Every unit (a rule, not a gap; the critic grades it):

- The zone's gate ran and the output is reported honestly; a record node with
  real `## State Impact` targets; ROADMAP checkbox and ADR line where AGENTS.md
  asks for them.
- **The record node names the criterion code (C1..V3) it advances and states
  whether the evidence that criterion asks for now exists.** If it does, say
  "ticks C1" in the record; the human confirms by editing this file.

## Later criteria

Real criteria, not seeded as gaps. The planner may not target these; the human
promotes one into the done-criteria section above when the frontier lands or
blocks. They are here so that a short frontier does not mean a forgotten
backlog.

**Inherited-tree reduction:**

- [ ] **The fork's delta against upstream is smaller than at the start of this
      run**, measured by the delta manifest AGENTS.md names, and the manifest is
      honest about every inherited file touched.

**Parts library:**

- [ ] **A planetary gearbox exists as a parametric library value** with a mesh
      test that passes; ADR-235's planet-ring overlap is resolved or the
      composition is replaced.
- [ ] **25T horns and servo pigtails come from manufacturer STEP sources**, with
      the provenance recorded the way `docs/PROVENANCE.md` asks.
- [ ] **The catalog is broad enough for a robot prompt**: at least five servos,
      ten actuators, a bearings family, and M2 to M5 nuts and bolts, each with
      provenance and a real-kernel test.

**Outside knowledge:**

- [ ] **One mechanism in the repo came from a paper or a real product**: the
      source is cited in the project's `DECISIONS.md`, the implementation is
      tested, and the walk built it.

**Fleet:**

- [ ] **A fresh machine runs the walk** after one documented install script,
      headlessly, with no step that needs a person.

**North star:**

- [ ] **The robot prompt works unattended**: from a prompt naming the servos,
      bearings, and hardware, the loop produces a printable mesh export, a
      trained policy, and a rollout video, with no human step.
- [ ] **A biped the loop designed from a prompt trains end to end on this
      machine's GPU** and its policy steps and survives on the same table as G2.

**Shell:**

- [ ] **The `hide_render` shell bug from `docs/IDEAS.md` is fixed** with a test
      that fails on the old behaviour.

## Horizon ladder

Sizes, not times. What to do when the rung above is exhausted. The critic
re-plans from this after every reconcile and names the next unit in its reply;
the ladder is the first plan, not the last.

**One thing leads this run: a mechanism the eyes can see moving, trained for
real on the GPU, and a study that ends in a report.** ot4 proved the walk on
four toy rigs; ot5 makes the walk say something true about a mechanism that
matters.

- **short-term:** (units, one iteration each)
  1. Wire ADR-283's swept clearance into the walk's review step so
     `review.json` reports the trace scope and the worst frame (C1).
  2. Copy `~/cdx-rl/projects/mg-legs.cadex` into `~/cadex-projects/mg-legs/`,
     scaffold its project docs, and run `cadex walk` on it with training on the
     GPU inside the bound; record exactly which leg fails and why (G1). A clean
     run is the evidence; a failed run names the next unit.
  3. Fix the section ranking so a plane that cuts the moving part beats one
     that cuts more still parts, and re-cut `ot4-cart` (C3).
  4. Pick the joint for the variant study, write it as one parametric xscript
     with five named parameter sets, and build all five with `cadex params`
     (V1).
  5. The smallest `cadex report` that draws one graph from a `PROGRESS.md`
     fixture (V3, first half).
  Whenever the short rung is empty: run `cadex walk` on the mg-legs project
  again and record what changed. That run is always a unit.
- **medium-term:** (gaps, several units each)
  1. A rig whose interference exists only in motion, walked and reported (C2).
  2. The GPU gait: iterations and envs raised until a checkpoint steps and
     survives on the table (G2), then the shove band with backward measured on
     its own (G3). One training run per unit; `--detach` and `--complete` split
     a long run across iterations if it needs it.
  3. The five variants through the same walk and ranked, the winner as the
     project's defaults (V2), then the report rendered from that project (V3).
  4. Every project under `~/cadex-projects/` keeps `PROGRESS.md` rows that are
     comparable across projects; a doc in `docs/CLI.md` says which columns are.
- **long-term:** (directions, and the standing work that never ends)
  Toward the north star, in this order, one rung opened at a time:
  **(1)** the nine criteria above -- this run's whole frontier;
  **(2)** a biped the loop designed from a prompt, trained end to end on this
  machine's GPU, on the same stepping table;
  **(3)** a fresh Linux machine runs the walk after one documented install
  script, headlessly, with no step that needs a person.
  Then print-ready export, G-code, the rollout video, each as one more leg of the
  same walk. **Rungs 2 and 3 are parked in the later-criteria section and are
  not on the frontier.** The human promotes a rung by editing this file between
  runs.
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
- **This run's machine is the GPU box** (`sb1x`: Ubuntu 24.04, RTX 5090, 32
  cores, 60 GB). The loop runs on it and owns the checkout at `~/cadex`. The old
  "never dispatch to the GPU box" rule described a machine the loop could not
  reach; it can, it is running on it, and B7 is no longer blocked by that rule.
  Do not touch any other machine, and do not dispatch work off this one.
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
- **Training is bounded, and the bound is now a gait's size: at most 2 hours
  of wall clock and 20 GB of memory per training run.** The 5090 is this run's
  trainer; `jax` with the CUDA plugin and `mujoco-mjx` are installed in
  `~/cadex-train-venv`. One training run per unit, launched inside the
  iteration; a run that needs more than the iteration has left is started with
  `--detach` and collected with `--complete` in the next one. Never two
  training runs at once. Never a run without `--timeout`.
- **mg-legs is read from `~/cdx-rl` and never written there.** Copy the
  project into `~/cadex-projects/mg-legs/` once and work only on the copy. The
  `cdx-rl` repository is another project's tree; do not commit to it.
- **Projects live under `~/cadex-projects/`**, each its own git repository as
  the walk scaffolds it. They are not in this repo and are not committed here;
  the record node cites the project path and the numbers.

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

Housekeeping every 5 work iterations, or as soon as 3 record nodes are
unreconciled: the actor's next iteration is the reconcile pass (fold impacts,
advance the high-water mark, regenerate `STATE.md`, check, commit). The
maintainer and planner roles are off for this run; the critic's reply names the
next unit. The run branch is the single-writer branch for this run. The human
may merge the run branch into main with a merge commit at any time; the run
continues on its branch.
