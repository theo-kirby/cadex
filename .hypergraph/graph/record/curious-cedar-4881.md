---
node_id: 105fa35a-7ff0-5163-a3c0-2e8b6d3936e8
slug: curious-cedar-4881
title: 'F3: backfilled record for ADR-351 slider sweeps (commit 7fb47e51, iteration 12)'
created_at: '2026-09-14T19:53:23+00:00'
parents:
- green-river-3790
summary: ''
---
## What

Backfilled record for commit `7fb47e51` ("ouroboros #12: no record"), which
landed ADR-351: `assembly.assembly(..., sweep_step_mm=...)` extends the ADR-349
exact-solid sweep producer to limited, unsuppressed slider joints in rigid
trees. Each swept joint now names its `kind`, `unit` and `step` and reports
`range_<unit>`, `initial_<unit>` and `first_contact_<unit>`, so degrees and
millimetres never share a key; the assembly report carries `step_degrees` and
`step_mm`, null when undeclared. A limited joint whose kind's step is
undeclared, an open-ended limit, or any other limited kind (cylindrical
included) is reported `incomplete` with its reason rather than skipped. The
inspect scope, `cadex clearance --sweep`, the agent instructions, `docs/CLI.md`,
`docs/INTEGRATION.md` and `docs/XSCRIPT.md` pass the new fields through.

## Why

The critic's iteration-13 message asked first for the missing causal record of
`7fb47e51`, with State Impacts on `curious-quill-9036` (F3) and
`eager-summit-3153` (F9), actual gate results and the remaining gaps. Iteration
12 committed through the runner's no-record fallback, so its evidence was
invisible to the graph. This record is that backfill, written from the commit
and from gates re-run in iteration 13 against the committed source; the
iteration-12 transcript's CLI run was killed when its turn ended, so no
iteration-12 CLI total is claimed.

## Method

Read the commit's diff (13 files, +324/−92). Engine: `_SWEEP_KINDS` maps
revolute → (`angle_limits_degrees`, `sweep_step_degrees`, degrees) and slider →
(`length_limits_mm`, `sweep_step_mm`, mm); the child translates the subtree along
the solved connector +Z axis between the length limits with the same baseline
agreement, endpoint-inclusive sampling and per-joint/total/pose/pair budgets as
hinges. Tests: `test_slider_known_position_solved_agreement_and_incomplete_coverage`
uses two spheres whose contact begins 2 mm before coincidence and asserts first
contact within one 0.75 mm step of −2 mm, the analytic lens volume
π(4r+d)(2r−d)²/12 at the nearest sample, the 6 mm solved distance, elapsed time
under the per-joint bound, and the same result with connector order reversed;
the hinge fixture pins the undeclared-step, open-ended and cylindrical reasons;
`test_joint_sweep_is_published_and_restore_does_not_recompute` is parametrised
over revolute and slider and now checks `kind`, `unit`, `range_<unit>` and the
`first_contact_<unit>` key across a cadexd restart.

Iteration 13 found the installed engine one comment line behind the committed
worker (iteration 12 edited after its last build), so it ran one
`pixi run build-engine` and `pixi run stage-engine` (both exit 0; installed and
payload copies now byte-identical to source) before the gates.

## Result

Gates, all run in iteration 13 against `7fb47e51`'s tree:
- packaged gate `CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py`:
  18 passed in 16.59 s (17 before ADR-351; the slider parametrisation is the
  eighteenth).
- `pixi run test-engine`: 2,127 passed, 53 skipped in 346.72 s (iteration 12 added three tests over green-river-3790's 2,124).
- `pixi run python -m pytest cli/tests`: 641 passed, 1 skipped in 566.76 s, run to completion this time (iteration 12's run was killed at turn end).

Remaining gaps for F3: the product producer has not yet been run on a copy of
`ot6-finch` (that is iteration 13's own unit); limited cylindrical and other
non-hinge, non-slider joints stay `incomplete` by design; sampling is discrete
and is not a continuous collision proof. Remaining gaps for F9: the retained
Finch, Robin and Heron reopen-and-failing-set comparison against the ot6 probe
checkers is still not done. No dependency was added; no design was edited;
acceptance behaviour is unchanged.

Dispatch closed: 1 unit — backfilled record for ADR-351 slider sweeps with iteration-13 gate results.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 7fb47e51ff94bfe7247c0f201fabcab6cecd1d75

## State Impact

- target: curious-quill-9036 — Limited sliders sweep in millimetres beside hinges (ADR-351): per-joint kind, unit and step; range_/initial_/first_contact_<unit>; undeclared-step, open-ended and other limited kinds reported incomplete, never skipped. Gates re-run green in iteration 13; product Finch measurement was still outstanding at this commit.
- target: eager-summit-3153 — Iteration-13 gates against 7fb47e51: engine 2,127 passed/53 skipped, CLI 641 passed/1 skipped run to completion, packaged lifecycle 18 passed after one build and stage; retained-design failing-set comparison still open.
