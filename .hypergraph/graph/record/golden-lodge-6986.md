---
node_id: 04df37bc-ada6-523c-b874-bcabaa4a0ee0
slug: golden-lodge-6986
title: A suppressed joint is not missing coverage (ADR-371)
created_at: '2026-09-16T18:29:57+00:00'
parents:
- honest-sky-8719
summary: ''
---
## What

The fifth F6/F7 capacity probe of 2026-09-16, and then the defect it left room
for: **a suppressed joint is no longer counted as missing swept coverage**
(ADR-371, commit `45a2fe2c`).

The probe first. `run.py window --model claude-fable-5` was refused again,
exit 1 in 2.07 s, `room: false`: `seven_day_overage_included` 100 % with
`overageDisabledReason: org_level_disabled`, `seven_day` 54 %, `five_hour`
25 %, the result frame carrying "You've reached your Fable limit". The
rejecting frame's `resets_at` is the same `1789740000` →
2026-09-18T14:00:00Z, which dates that usage window and nothing about the
organisation setting that refused. No slot was spent; no prompt was
dispatched; F6's four slots and F7's four stay unspent and no `ot7-robin-b` or
`ot7-plover-b` exists.

Then the unit. `_measure_joint_sweeps` handed **every** limited joint to the
sweep child, suppressed ones included. The child serialised every component's
BREP, launched a `FreeCADCmd` subprocess, and refused the joint from inside it
with `only unsuppressed limited tree hinges and sliders are supported`. The
row came back `incomplete`, and one `incomplete` row makes the whole
assembly's coverage `incomplete` — permanently, because nothing the author can
declare will change it. The CLI's block then told the agent to declare the
`sweep_step_degrees` it had already declared, and `fit.sweep` could never read
`pass` again.

Now: the engine checks `suppressed` first and returns
`{"status": "skipped", "reason": "the assembly suppresses this <kind> joint,
so the solver ignores it and it holds no range to sweep"}`, before any child
process or geometry call; only a status that is neither `complete` nor
`skipped` degrades coverage. `sweep_summary` counts those rows as
`joints_skipped`, apart from `joints_complete`, and judges its verdict over
the joints that are left. An assembly whose limited joints are *all*
suppressed has rows and judges none: a third fact wearing `unavailable` after
ADR-368's two, with its own reason, never a pass.

## Why

The critic's message: probe capacity with the runner's no-slot probe, dispatch
F6 if it permits, and if refused "preserve all slots and make no change unless
a concrete unblocked defect advances an F criterion". The probe refused, so
this is the second clause, and it is the same shape as last iteration's unit —
a defect in what the agent is shown, found by reading the product rather than
by manufacturing work.

It advances **F3** (fit checked across each joint's range) and **F1** (the
agent sees measured fit) directly: a permanently `incomplete` swept verdict is
the agent being told its coverage is broken when it is not, and the one
remedy the block offers — declare a step — is already done. It is also the
defect class the run keeps finding: the product knowing less about the design
than the checker beside it.

The defect contradicted two contracts that were already written down.
`docs/XSCRIPT.md` said the producer sweeps "each limited, **unsuppressed**
revolute or slider joint"; the CLI's own no-joints wording listed "suppressed"
among the joints a sweep does not cover; and ADR-370, one iteration earlier,
had filtered the attachment report to unsuppressed fixed joints. The engine
was the outlier, as `CadexDynamics` is not — it treats a suppressed joint as
no edge at all.

The one judgement call: **complete coverage of joints that were all suppressed
is not a pass.** Counting skipped rows as covered would have made a mechanism
that declares motion and then holds it still read `sweep pass`. That case gets
`unavailable` with its own reason and its own progress phrase instead.

## Method

1. `pixi run python docs/probes/ot7/runner/run.py window --model
   claude-fable-5` — refused, `room: false`, no slot spent, recorded above.
2. Reproduced the defect on the real kernel before touching anything: a
   suppressed limited hinge through `_measure_joint_sweeps` under
   `build/release/bin/FreeCADCmd` returned `status: incomplete`, reason `only
   unsuppressed limited tree hinges and sliders are supported`, with
   `elapsed_seconds: 0.114` — proof a child process ran for a joint there was
   nothing to measure on.
3. Engine: the `suppressed` branch in `_measure_joint_sweeps`, and
   `not in ("complete", "skipped")` as the condition that degrades coverage.
4. CLI: `joints_skipped` in `sweep_summary`, the verdict judged over
   `len(joints) - skipped`, `SWEEP_ALL_SUPPRESSED`, the two new `_sweep_line`
   phrases, and the `cadex clearance --sweep` coverage line.
5. Tests, each red on the old code and checked so: the real-kernel driver in
   `cadex_tests/test_joint_fit_sweep.py` gains a suppressed-only sweep
   (coverage `complete`, row `skipped`, **no** `elapsed_seconds` and no
   `pairs`, which is how the test proves no child ran) and a suppressed joint
   beside a swept one; `cli/tests/test_clearance.py` gains the mixed case
   (`pass`, counts `(2, 1, 1)`, `sweep pass: 1 joint(s) swept; 1 suppressed`),
   the all-suppressed parametrisation, and the writer's coverage sentence.
   Verified red by stashing each side's source and re-running.
6. `docs/XSCRIPT.md`, `docs/CLI.md`, `docs/INTEGRATION.md`, ADR-371.
7. Green: `pixi run test-engine` **2145 passed, 53 skipped** (316.9 s);
   `pixi run python -m pytest cli/tests` **793 passed, 1 skipped** (531.3 s);
   `pixi run build-engine` + `pixi run stage-engine`, then the packaged gate
   `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
   test_cadexd_lifecycle.py` **20 passed**.

## Result

**What is true now.** A design that suppresses a limited joint gets a swept
verdict that can reach `pass`, and a design that suppresses every one of them
is told that in words rather than being handed a coverage complaint it cannot
answer. Commit `45a2fe2c`; ADR-371; three docs updated with it.

For the next iteration:

- **The F6/F7 gate is still shut, measured this iteration.** Fifth probe,
  2026-09-16: exit 1 in 2.07 s, `org_level_disabled`, seven-day-with-overage
  100 %, five-hour 25 %, `room: false`. Only an **unrefused** probe is evidence
  it lifted; a clock reading is not. Re-probe before any dispatch.
- **The reconcile debt is four nodes**: `soft-journey-2954`,
  `mellow-marsh-0749`, `honest-sky-8719` and this one. A work dispatch cannot
  fold any of them.
- **One deliberate non-change.** A revision accepted before ADR-371 keeps its
  `incomplete` row and its unsupported-kind reason until it is rebuilt.
  Rewriting retained measurements would change receipts that F9's regression
  floor is held against; no ot6 or ot7 design suppresses a limited joint, so
  no retained failing set moves either way.
- **The judgement call to know about.** `joints_checked` still counts every
  row, including skipped ones, so an older reader that computed unswept
  coverage as `checked - complete` now over-counts by the number of suppressed
  joints. Both readers in this tree were updated in the same commit, and the
  arithmetic is stated in the summary's own comment and in `docs/CLI.md`.
- No new dependency, no TODO, no stub, nothing left red. `build/engine/` was
  re-staged for the gate; it is a build output and is not committed.

Dispatch closed: 1 unit — the gate re-probed and still refused, so the unit
became a defect in what the agent is shown: a suppressed joint is no longer
counted as missing swept coverage (ADR-371).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 45a2fe2c0b9e4c531938d3e8e651e25bf87f399d

## State Impact

- target: wild-horizon-5461 — The swept half of the build reply stops reporting a suppressed joint as missing coverage (ADR-371): its row is skipped with its reason, counted as joints_skipped apart from joints_complete, and the verdict is judged over the joints that are left, so one suppressed joint beside a swept one is a pass rather than a permanent incomplete. All limited joints suppressed is a third unavailable fact with its own reason and its own progress phrase, never a pass. Engine 2145 passed/53 skipped, cli/tests 793 passed/1 skipped, packaged gate 20 passed on a freshly staged payload.
- target: forest-wind-0342 — _measure_joint_sweeps in cadex_assembly_worker.py checks suppressed first and returns status skipped without launching the sweep child or touching geometry; only a status that is neither complete nor skipped degrades the report's coverage. Before this every limited joint, suppressed included, cost a BREP serialisation and a FreeCADCmd launch that refused it as an unsupported kind. No protocol op, argument or response shape changed, and no verdict or acceptance behaviour changes for a design without a suppressed limited joint.
- target: chilly-union-8972 — cli/cadex_cli/clearance.py gains joints_skipped and SWEEP_ALL_SUPPRESSED, judges the swept verdict over the unskipped joints, and writes the suppressed coverage sentence in cadex clearance --sweep; bridge.py's _sweep_line gains the '; N suppressed' suffix and the 'every limited joint suppressed (N)' phrase. docs/CLI.md, docs/XSCRIPT.md and docs/INTEGRATION.md carry the contract.
- target: narrow-dune-9454 — F6 remains blocked: a fifth capacity probe on 2026-09-16 refused claude-fable-5 at the organisation level (org_level_disabled, seven_day_overage_included 100 %, seven_day 54 %, five_hour 25 %) in 2.07 s with room false. It spent no slot; all four F6 slots stay unspent and no ot7-robin-b exists. No prompt was dispatched.
- target: rapid-grove-9687 — F7 remains blocked behind F6 on the same measured refusal, all four slots unspent; the fifth probe is the current evidence.
