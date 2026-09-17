# Goal: the agent designs it right

Verified against source: 2026-09-17. Owner-directed charter revision (ADR-341),
replacing the ot6 charter (ADR-328), whose D1, D2 and D4–D10 the owner ticked on
2026-09-14 (record `nimble-wing-3050`). D3, the rendered look, went to the
owner's own manual work and does not carry. Amended 2026-09-15 for the ot7
restart (ADR-355): usage-limit failures are void, design turns wait for the
product agent, and no role stops or starts the run.
The human owns this file; unattended roles do not edit it.

## Owner directive: finish the correction, then wait (2026-09-17)

The owner approved this correction after the iteration-116 check-in. This
section takes precedence over instructions below to find more tooling work
while the product agent is unavailable.

1. Finish the unit already in flight at iteration 116, including only fixes
   directly required by its critic review and its required verification.
2. Reconcile the outstanding corrective impacts, especially ADR-380's removal
   of ADR-379's false claim that fixed components must touch. The state and
   generated views must reflect the corrected code. Record this owner directive
   once, causally parented, with its State Impact; include the charter change
   in that handoff. Run hypergraph export and check.
3. Then wait for product-agent access. Do not start more tooling, checker,
   test, documentation or bookkeeping units to fill the wait. Do not write
   repeated waiting records or repeatedly probe the same organisation-level
   refusal. An unchanged refusal is not new evidence. Return a no-change stuck
   result and let the runner back off.
4. Resume the existing frozen F6 and F7 experiments only after concrete evidence
   of restored access to the required product-agent model, such as an owner
   account refresh with a successful availability check or a provider reset
   followed by a successful check. Actor availability alone does not establish
   product-agent availability. Preserve all unspent slots and the measured F4
   and F5 outcomes. Do not claim done while F6 and F7 remain unattempted.

No restart or configuration change is requested. The current actor and critic
finish under their existing charter; this directive applies at the next
iteration boundary. The configured stop rules still apply.

## Restart

ot7 stopped itself on 2026-09-14 at 23:24 UTC, after 40 iterations. The
tooling half landed with evidence (F1–F3, F8, F9). The agent half, F4–F7, was
never tried. Claude's five-hour window was spent, the actor had fallen back to
Codex, and all six product-agent calls it dispatched, three F4 repairs and one
each for F5, F6 and F7, failed in two to four seconds with "You've hit your
session limit". The critic counted those as spent attempts, ruled the run
exhausted, and told the actor to stop it, which it did.

**Those six calls are void.** No model saw a prompt. They consumed no create,
continuation or repair slot and are not design results. The "exhausted" and
"terminal incomplete" handoffs in `docs/probes/ot7/REPORT.md` and its records
are superseded by this amendment. Fix them forward, and do not delete them.
Every F4–F7 design still has its create or repair prompt and all three
continuations unspent. This restart continues run ot7 on the same branch.

## Mission

Make the product agent design mechanisms that fit, on its own. ot6 produced
three buildable designs, but the product agent did not make them fit by itself.
Finch, the biped, was written by the actor with no model turn. Robin and Heron
came from the agent, and the actor edited Robin's script twice. Heron's three
defects were found by a hand-run probe script and fed back as hand-written
turns: a floor plane in the design, 248.2 mm³ of servo tab buried in its cheek,
and a horn left 0.2 mm from its link. Each time the agent's printed output said
the parts fit.

The cause is in the product, not in the model. The engine already measures
every part pair's gap and overlap at the solved pose
(`_measure_clearance` in `src/Mod/cadex/cadex_assembly_worker.py`), but the
agent's tools cannot reach those measurements, its reply carries the script's
stdout, and its system prompt (`cli/cadex_cli/agent.py`) tells it to verify by
printing. Nothing checks fit across a joint's range.

In priority order, this run:

1. **Puts measured fit in front of the agent.** After every design turn that
   builds, the agent's reply and tools carry measured clearances and overlaps
   from the published result. Its instructions say that a script's printout is
   a claim and the measurements are the evidence.
2. **Lets a design say what should touch.** A script declares intended
   contacts and clearances between named parts, and the checker reports what
   the geometry does against that intent. A failing fit is reported, never
   refused: the design still builds and accepts, and existing projects keep
   opening.
3. **Checks fit through the motion.** Every joint with declared limits is swept
   through its range, and first contact is reported at the angle or position
   where it happens.
4. **Proves the agent uses it, unassisted.** The arm, balancer and biped
   prompts, in fresh projects, reach designs with no failing fit, no actor edit
   and no human design feedback, and each passes a short smoke rollout. A
   design that does not get there is a valid measured result and is reported
   as such.

The dashboard and the rendered look belong to the owner for now and are out of
this run entirely. There is no policy training this run.

## Done criteria

Only these unchecked claims form this run's frontier. Each record names the
criterion it advances, the evidence now present, and what remains. A record may
say "ticks F1" when its evidence exists; the human owns the checkbox edit.

- [ ] **F1. The agent sees measured fit.** After every design turn that builds,
  the tool reply carries a fit summary computed from the published clearance
  measurements, never from stdout: the check counts and every failing pair by
  name with its distance and common volume. `clearance` is an inspect scope on
  the agent's tool surface. The system prompt no longer tells the agent to
  verify fit by printing. Evidence: `test_project_tool_surface.py` updated with
  an ADR; a transaction test in which a script prints "no overlap" while its
  solids overlap receives the overlap in its reply; `docs/CLI.md` updated.
- [ ] **F2. Fit intent is declared and checked.** The script API declares
  intended contact and intended clearance, with a minimum, between named
  components. The checker reports four things: any overlap on any pair, a
  declared contact that is not touching within tolerance, a declared clearance
  below its minimum, and an undeclared pair closer than the default minimum.
  World geometry in a design, a floor or bench plane, is reported as its own
  failure. Nothing is refused at acceptance. Evidence: engine tests on
  fixtures that reproduce Heron's three ot6 defects, each reported with the
  right pair and number; `docs/XSCRIPT.md` documents the declarations.
- [ ] **F3. Fit is checked across each joint's range.** For every joint with
  declared limits, the checker places the real solids at poses across that
  range at a declared step, holding the other joints at the solved pose, and
  reports per pair the minimum distance, the maximum common volume and the
  joint value of first contact. The agent can reach the result, and so can
  `cadex clearance --sweep`. Evidence: an engine test on a two-link fixture
  whose contact begins at a known angle, reported within one step; on a copy
  of `ot6-finch`, the knee-to-thigh contact reported with its angle; measured
  runtime per joint recorded, and a bound on it enforced.
- [ ] **F4. The agent repairs from measurements alone.** A fresh product-agent
  session is given Heron's first accepted ot6 revision (`7e9eff5c…`, from a
  copy of the retained project) and one frozen continuation prompt that
  contains no part name, number or defect. Using only its tools, it resolves
  all three defects and accepts with zero failing fit checks. Evidence: turn
  count and timings, transcript digests, and the fit report before and after.
- [ ] **F5. The arm is designed unassisted.** Heron's ot6 create prompt, in a
  fresh project, reaches an accepted design with zero failing static and swept
  fit checks, zero actor edits, at most three frozen continuation prompts,
  catalog hardware for every purchased part, and a passing smoke rollout.
  Evidence: prompts and continuation count, per-turn fit failure counts,
  final fit report, inventory, smoke result, and the comparison with ot6.
- [ ] **F6. The balancer is designed unassisted.** The same bar as F5 on
  Robin's ot6 create prompt (`docs/probes/ot6/robin/create.prompt.txt`).
- [ ] **F7. The biped is designed unassisted.** The same bar as F5 on a biped
  prompt written and committed in this run's first unit, before any design
  turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog
  horns, bearings and fasteners, modelled printable mounts, no world geometry.
  ot6 has no biped baseline, because Finch had no model turn.
- [ ] **F8. A smoke rollout is one command.** A short bounded simulation of an
  accepted design, zero-action or holding its initial pose for a declared
  duration, passes when state stays finite, no component pair interpenetrates
  beyond tolerance over the trace, and the design rests on the environment
  floor or holds its grounded base. Evidence: CLI tests with a passing and a
  failing fixture, and the receipts F5–F7 cite.
- [ ] **F9. Nothing regressed.** Both suites green; the packaged gate green
  for any engine protocol or payload change. The retained ot6 designs (copies
  of Finch, Robin and Heron) still open, and the product checker's failing set
  on each matches what the ot6 probe checkers found, with every difference
  explained.
- [ ] **F10. A closing report exists and the critic accepted done.**
  `docs/probes/ot7/REPORT.md` has one row per design: prompts, turns,
  continuation prompts used, fit failures per turn, final static and swept
  checks, smoke result, and the ot6 comparison. It links the evidence for
  F1–F9 and names what remains open, claiming nothing a record does not carry.
  This is the run's last unit.

## Horizon ladder

Granularity, not elapsed time. The critic selects the next unit after each actor
turn; this ladder is the starting plan, not a fixed implementation sequence.

- **short-term:**
  R1. Teach `docs/probes/ot7/runner/run.py` to recognise a usage-limit exit,
      mark the receipt void, and stop without spending another slot. A
      fixture pins it. Rewrite the runner README and REPORT.md forward: the
      six calls are void and nothing is exhausted.
  R2. With Claude available, dispatch the F4 repair on a fresh seed copy, then
      F5, F6 and F7 in fresh suffixed projects, each through its continuations
      as its fit report requires. Items 0–4 below have landed, and so has the
      regression half of item 7.
  0. Freeze the prompts: commit the arm, balancer and new biped create prompts
     and the continuation prompts under `docs/probes/ot7/prompts/`, before any
     design turn (F5–F7).
  1. Add the `clearance` inspect scope to the agent's tools and a fit summary
     to the design-turn reply, computed from the published measurements;
     update the tool-surface test and the system prompt (F1).
  2. Add fit-intent declarations to the script API and the four-way check,
     with fixtures reproducing Heron's three ot6 defects (F2).
  3. Build the swept check on a two-link fixture with a known contact angle,
     then run it on a copy of `ot6-finch` (F3).
  4. Make the smoke rollout one command with a passing and a failing fixture
     (F8).
  5. Seed Heron's first ot6 revision in a copy and run the measurements-only
     repair (F4).
  6. Run the arm prompt unassisted (F5), then the balancer (F6), then the
     biped (F7).
  7. Run the checker on the ot6 copies, both suites and the packaged gate,
     then write the closing report (F9, F10).
- **medium-term:**
  1. Measured fit reaches the agent: summary in the reply, clearance scope,
     declared intent, and swept ranges (F1–F3).
  2. The agent demonstrably uses it: the seeded repair, then three unassisted
     designs, each with a smoke rollout (F4–F8).
  3. The regression floor and the closing report (F9, F10).
- **long-term:**
  1. Printability rules as checks: minimum wall, screw engagement, bearing
     seats, horn attachment, one connected assembly.
  2. A prompt benchmark: a fixed mechanism set scored on first-try pass rate,
     turns to acceptance and failing checks, re-run to show improvement.
  3. Behaviour worth watching: the rewards ot6 left open, so the biped walks,
     the balancer stands still and the arm settles on its target.
  4. Print-ready export: per-part STL or 3MF, orientation and a bill of
     materials from a design that passes every check.
  5. Keep every gate green, every doc true, and every project record usable.

## Constraints

**Standing:**

- Obey AGENTS.md: licensing boundaries, sandboxed geometry, unchanged process
  separation, zone gates, ADRs and record nodes. No UI in the engine, no copying
  GPL shell code into the CLI, no replacement engine or shell work.
- Training remains offboard. No trainer, JAX or MJX in engine payloads and no
  new training dependencies in pixi.toml.
- Preserve accepted-state checks. Reading a project cannot re-accept changed
  geometry, and a historical view never rebuilds an old run with today's script.
- The protocol is a contract. Prefer extending an existing inspect scope or
  assembly output over a new op; a new or changed op follows AGENTS.md's rule 6
  (INTEGRATION.md and the shell client in the same change). A change to the
  agent's tool surface updates `test_project_tool_surface.py` and earns an ADR.
- Keep records and artifacts project-local and portable. A committed receipt
  under `docs/probes` is at most 16 KB and an image at most 200 KB; transcripts,
  traces and logs stay in the project directory, cited by path and digest.
- Never commit secrets, machine-specific absolute paths, private-network
  addresses or hostnames, or build outputs. Never hand-edit STATE.md, PLAN.md
  or state nodes.
- One logical change per commit, fix forward after critic rejection. At most
  one full build per unit; report incomplete verification honestly.

**This run:**

- **The actor never edits a design.** In any `ot7-*` test project, every change
  to the script, its parameters or its accepted state comes from a product-agent
  turn. When the agent cannot run, the actor records the refusal and works on
  tools, checks or tests instead. It never substitutes its own edit.
- **Prompts are frozen.** Create prompts and at most three continuation prompts
  per design are committed before the first design turn. A continuation prompt
  names no part, number or defect ("Read the measured fit report and resolve
  every failing check." is the shape). A changed prompt starts a new attempt,
  and every attempt is reported.
- **A usage limit is not an attempt.** A product-agent call that ends on a
  provider usage, session or credit limit is void. This includes a call cut
  off partway through a turn. A void call consumes no slot and is not a design
  result. Only a turn that reached the model and ended on its own counts. The
  void call's project or evidence directory stays as a receipt. The retry
  sends the same frozen prompt in a fresh project, or to a fresh copy of the
  seed, with a letter suffix (`ot7-heron-b`, `ot7-heron-repair-b`). The report
  lists every void call apart from the design's attempts.
- **Design turns wait for the product agent.** The product agent runs on the
  same Claude account as the actor, so a spent Claude window stops both.
  Dispatch a design turn only while that harness is available, and never from
  a fallback harness while Claude is limited. If a call is void anyway, record
  it and move to tooling, tests or reconcile. Do not dispatch again until the
  window has reset.
- **No role stops, starts or restarts the run.** This covers the actor, the
  critic and any process either of them launches. No `ouroboros stop`,
  `ouroboros run` or signal to the loop, whether detached or not. The run ends
  only through its configured stop rules or the owner. A role that believes the
  run is finished says so in its verdict or record, then works the
  highest-ranked open criterion or makes no change.
- **Failing fit is reported, never refused.** Acceptance behaviour for existing
  scripts does not change; old projects keep opening and accepting.
- **The dashboard and the look are the owner's.** No edits to
  `cli/cadex_cli/review_static/`, `docs/REVIEW-DESIGN.md`, `docs/review-design/`,
  or the video rendering style. Leave the operator dashboard service alone. If
  an unavoidable change elsewhere breaks a test in that area, stop that line of
  work and record it rather than editing the page.
- **No policy training.** Smoke rollouts only, each bounded to five minutes.
- New test projects live outside this checkout under the operator's
  cadex-projects directory, named `ot7-*`. The ot6 projects are read-only; work
  on copies.
- Out of this frontier: printability rules beyond F2, a prompt benchmark beyond
  the three designs, reward design, print-ready export, catalog expansion
  beyond what a design needs, and inherited-tree removals.

## Question policy

The owner has chosen declared fit intent, reporting without refusing, ot6's
prompts plus a new biped prompt, no actor edits to designs, and no training.
Resolve routine choices autonomously: choose the smallest reversible change
advancing the highest-ranked open F criterion, use code as truth and update its
docs, and record assumptions. Never guess a measurement or report a design as
passing without its fit report. Report pre-existing gate failures against the
baseline. When the product agent's harness is limited, choose an unblocked
tooling, test or reconcile unit. When none is left, make no change and let the
loop wait for the reset. Never spend a frozen prompt while the harness is
limited. Scope expansion requires an owner charter revision, not an actor
interpretation.

## Exhaustion policy

`report_done`. When F1–F9 each have evidence, the next unit is F10: write the
closing report and claim done. The critic accepts done only when every
criterion's evidence is present in a record; the run stops after the runner's
`stop.on_done_accepted` count. A design that failed after its allowed
continuation prompts is evidence, not a reason to keep prompting. Do not add a
fourth design, start a long-term rung or repeat an attempt to fill the run.
Void calls never exhaust a design. A design is exhausted only after its create
or repair prompt and all three continuations have reached the model. "No
authorized experiment remaining" is not true while any design has an unspent
slot, and a verdict or record may not rest on it.

## Quality bar

- Engine changes run `pixi run test-engine`; CLI changes run
  `pixi run python -m pytest cli/tests`; protocol or payload changes also run
  the packaged gate (`CADEX_ENGINE_ROOT=<payload> pytest
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`).
- Every check ships with a fixture whose right answer is known in advance and a
  test that fails on the old code.
- An unassisted-design claim carries the prompts' digests, the turn count, the
  transcript digests, the fit report per turn and the smoke result. A claim
  without its fit report is not evidence.
- A unit changes product code, a meaningful test or a user-facing document and
  advances an F criterion. Bookkeeping alone is reserved for reconcile passes.
- Record causally with real State Impact targets. Removals and direction
  changes earn an ADR, behaviour changes update their docs, and landed roadmap
  items are marked.

## Reconcile

Every five work iterations or three unreconciled records, the actor's next unit
is the reconcile pass: fold impacts, advance the high-water mark, regenerate the
views, export, check and commit. Separate maintainer and planner remain off; the
critic names the next unit. Unattended roles never edit this charter. The
runner ingests operator charter edits at the next iteration boundary and
records a versioned directive; confirm adoption in its charter-reload log. The
current actor and critic finish under their original charter. Do not launch or
restart a run as part of charter authoring.
