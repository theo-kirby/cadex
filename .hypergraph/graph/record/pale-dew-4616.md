---
node_id: 2d798bf9-301b-50da-9a72-6017852c33a9
slug: pale-dew-4616
title: F7's smoke, taken without spending a slot, catches 24 misplaced MJCF bodies (ADR-392)
created_at: '2026-09-20T00:15:45+00:00'
parents:
- happy-ocean-5297
summary: ''
---
## What

F7's last missing requirement — a smoke rollout — was **measured without
spending a design slot**, and the collector gap that made that impossible was
closed first (ADR-392).

**The gap.** The ot7 collector runs its one bounded holding smoke only when an
attempt *closes*. `ot7-plover-e` is `paused` at zero failing static and zero
failing swept fit checks with `continue-2` and `continue-3` unspent, so the
only route to a smoke was to spend a frozen continuation on a turn whose own
fit report names nothing to fix — buying a measurement with a design slot.
`run.py smoke PROJECT` takes it instead: the same bounded
`cadex smoke --seconds 1`, no prompt, no model, no slot, no status change. Its
evidence goes to `evidence/smoke-interim/` (then `smoke-interim-retry-N`) so
the canonical `evidence/smoke/` stays free for whatever closes the attempt
later, and the result is appended to `interim_smokes` beside the design
identity it measured. The closing-smoke block became `run_smoke`, shared by
both paths, so ADR-391's first-free-name rule is not copied.

**What it measured on `ot7-plover-e`** (accepted revision `0491ead7…`, digest
`a00d1aea…`, exit 1 in 0.4 s, receipt still `paused` with two continuations
unspent):

- **The dynamics half passed every check**, verdict `pass`. State finite
  throughout; penetration **0 breaches** with the two feet touching the floor
  at 0.337 mm against a 0.5 mm tolerance; support resting on the floor after a
  0.281 mm drop at 0.186° of tilt, base `c_pelvis`, `kind: free`; the single
  termination rule unfired. 51 samples over 1.0 s at 50 Hz, MuJoCo 3.10.0.
  **The biped stands.** It does not topple the way Robin's did.
- **The exact-BREP half never produced a verdict.** Its frame-0 agreement gate
  raised on `('c_bearing_hip_l', 'c_bearing_hip_r')`: the published clearance
  puts them 33.8 mm apart with zero common volume, and the MJCF puts both at
  the same point 16.9 mm below the pelvis.

**The gate was right, and what it caught is ours.** Composing the MJCF body
tree to world poses against the solved component placements: **all 24
components whose solved placement carries a rotation are at a different world
pose in the model than in the assembly** — worst `c_tabscrew_knee_l_0` at
**121.9 mm**, with a wholly different orientation every time — and the five
with an identity rotation are exact to 1e-6. Four of the misplaced bodies
carry a collision geom (the servos) and all 24 carry mass, so the dynamics
pass is a pass on a model that does not match the design. Sharper still: of
the 28 non-root bodies, **4 carry the parent-relative transform the solved
assembly implies and 24 carry its exact inverse, none anything else** — the
four are precisely the bodies with a revolute joint, the 24 are the fixed
attachments. `CadexDynamics.py:3350` derives a non-root body's frame as
`parent_local_matrix × inverse(child_local_matrix)` from the joint connector
frames, while only the root body uses the solved placement. Robin and Heron
write no rotated body at all, which is why neither exercised this.

**Inventory, measured for F7's catalog-hardware requirement.** 29 components:
**24 catalogued** (4 `servo/mg90s`, 4 `servo_horn/mg90s-single_arm`, 4
`bearing/mr128`, 8 `bolt/m2x6-socket`, 4 `bolt/m2x12-socket`) and **five
uncatalogued sources, every one a printed part** (pelvis, both thighs, both
shins). `derived_catalog_sources` empty, no world geometry. Every purchased
part is a catalog part, so the requirement is met — with the M2 × 16 the
create prompt named still absent, replaced by the M2 × 12 the continuation
fitted.

Committed: the collector change, its two fixtures, ADR-392 with its measured
addendum, the runner README section, the REPORT.md iteration-167 section and
its updated F7 row, and the compact receipt
`docs/probes/ot7/retained/plover-smoke-e.json` (12.4 KB).

## Why

Exactly the critic's message: measure F7's missing evidence on
`ot7-plover-e` without spending a slot, run the smoke directly rather than
burning `continue-2`, record the inventory count, and — if the collector can
only smoke on an exhausting invocation — fix that with a fixture first. It
could only smoke on an exhausting invocation, so the fixture and the fix came
first and the measurement second.

**One deviation, and it is the critic's own condition.** The message said to
dispatch `continue-2` only if the smoke or the inventory actually fails. The
inventory passes. The smoke exits 1 — but its failure is a repository defect
in the MJCF the engine exports, not a design defect: the design is unchanged,
its fit report names no failing check, the dynamics half passes, and nothing
in the agent's tool surface shows it a body pose. Spending a frozen
continuation on it would ask the agent to fix our bug and then report the
outcome as the agent's, which is the exact failure ot7 exists to end. So
`continue-2` stays unspent and F7's smoke is recorded as **unproven rather
than failing**.

Frontier: `rapid-grove-9687` (F7), with `chilly-union-8972` (the CLI and its
collector) carrying the new subcommand and `salty-isle-4063` (dynamics on
MuJoCo) carrying the defect.

## Method

`run.py smoke $PROJECTS/ot7-plover-e` — one measurement, no prompt, no window
probe, no model call. No actor edit of any kind: nothing under the project,
`src/` or `cli/cadex_cli/` was touched, and the receipt's own design-identity
guard would have refused had the script moved.

The MJCF comparison was computed from the smoke's own retained artifacts:
`plover_model-model.xml` composed down the body tree, against the solved
placements in `evidence/turn-1/inventory.json`, with each non-root body's
written parent-relative transform tested against both the implied transform
and its inverse.

Fixtures: `test_a_paused_attempt_is_smoked_without_spending_a_slot` walks a
paused attempt through an interim smoke, a second interim smoke beside it, and
a later resume to exhaustion that still writes its closing smoke into the
canonical `evidence/smoke`; `test_smoke_refuses_what_it_cannot_honestly_measure`
covers no attempt, a repair attempt, a closed attempt and an actor-edited
design. Both fail on the old code. `pixi run python -m pytest cli/tests`:
**845 passed, 1 skipped** in 552.7 s. No engine, protocol or payload change, so no engine suite or
packaged gate is implicated.

## Result

**F7's smoke exists and is not the agent's problem.** Of F7's six
requirements, five are evidenced and unchanged — accepted design, zero failing
static checks, zero failing swept checks with complete coverage, zero actor
edits, one of three continuations used, and now catalog hardware measured at
24 catalogued components against five printed sources. The sixth, a passing
smoke rollout, is **measured and unproven**: the dynamics half passes every
check on a standing biped, and the exact-BREP half cannot return a verdict
while the model misplaces every rotated component.

**The next unit is the engine one**, and it is well-pinned: a fixture that
holds a fixed-attachment body's MJCF frame to the parent-relative transform
the solved assembly implies (it is currently the inverse), then the fix at
`CadexDynamics.py:3350`. It is engine zone, so it needs `pixi run test-engine`
and, if any published shape moves, the packaged gate.

Concerns for the next iteration. (1) **This defect predates ot7 and reaches
past it**: every MuJoCo model of a design with rotated fixed attachments has
carried its hardware mass, and any hardware collision geoms, in the wrong
place. No previously closed criterion is retracted by this record, but F9's
regression pass should say what it covers. (2) The unreconciled tail is now
four records deep and the reconcile is due at five. (3) F7 still holds
`continue-2` and `continue-3`, and its fit report names no failing check, so
the case for spending either is now weaker, not stronger. (4) No window probe
was taken this iteration, because no design turn was dispatched.

Dispatch closed: 1 unit — F7's smoke measured on `ot7-plover-e` without
spending a slot, behind a new `run.py smoke` and two fixtures (ADR-392): the
dynamics half passes and the biped stands, while the exact-BREP half's
agreement gate catches all 24 rotated components written into the MJCF at the
inverse of their solved parent-relative transform.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: eae5a5d5f22b8732aebd580fe60f7c325588e467

## State Impact

- target: rapid-grove-9687 — F7's sixth requirement is now measured rather than unrun, and no slot was spent to get it: run.py smoke on ot7-plover-e (accepted revision 0491ead7, digest a00d1aea, receipt still paused with continue-2 and continue-3 unspent) exited 1 in 0.4 s. The dynamics half passed every check with verdict pass -- state finite, penetration 0 breaches with both feet touching the floor at 0.337 mm against a 0.5 mm tolerance, support resting on the floor after a 0.281 mm drop at 0.186 deg of tilt with base c_pelvis and kind free, the one termination rule unfired, 51 samples over 1.0 s at 50 Hz on MuJoCo 3.10.0 -- so the biped stands and does not topple the way Robin's did. The exact-BREP half returned no verdict: its frame-0 agreement gate raised on (c_bearing_hip_l, c_bearing_hip_r), published 33.8 mm apart and placed at the same point in the model. That is a repository defect, not a design defect, so F7's smoke is unproven rather than failing and continue-2 stays unspent. Inventory measured for the catalog bar: 29 components, 24 catalogued (4 servo/mg90s, 4 servo_horn/mg90s-single_arm, 4 bearing/mr128, 8 bolt/m2x6-socket, 4 bolt/m2x12-socket), five uncatalogued sources all printed parts, derived_catalog_sources empty, no world geometry -- every purchased part catalogued, with the M2x16 the create prompt named still replaced by an M2x12. Receipt docs/probes/ot7/retained/plover-smoke-e.json, commit eae5a5d5.
- target: chilly-union-8972 — The ot7 collector gained run.py smoke PROJECT (ADR-392): a bounded cadex smoke --seconds 1 on an open attempt that sends no prompt, reaches no model, spends no slot and changes no status, recorded under the receipt's interim_smokes beside the design identity, the status it was taken at and the remaining block it left untouched. Its evidence goes to evidence/smoke-interim then smoke-interim-retry-N, leaving the canonical evidence/smoke free for whatever closes the attempt later. It refuses a project with no attempt, a repair attempt, an attempt closed by a void, interrupted or failed call, an attempt with no completed turn, and a design that changed since its last turn. The closing-smoke block became the shared run_smoke, so ADR-391's first-free-name rule is not duplicated. Two fixtures fail on the old code; cli/tests: 845 passed, 1 skipped.
- target: salty-isle-4063 — A measured MJCF export defect, first reached by a design with rotated components: composing plover_model-model.xml's body tree to world poses against the solved component placements, all 24 of ot7-plover-e's 29 components whose placement carries a non-identity rotation are at a different world pose in the model than in the assembly (worst c_tabscrew_knee_l_0 at 121.9 mm, with a wholly different orientation in every case), while the five with an identity rotation are exact to 1e-6. Sharper: of the 28 non-root bodies, 4 carry the parent-relative transform the solved assembly implies and 24 carry its exact inverse, none anything else -- the four are precisely the bodies with a revolute joint, the 24 are the fixed attachments. CadexDynamics.py:3350 derives a non-root body's frame as parent_local_matrix x inverse(child_local_matrix) from the joint connector frames, while only the root body uses the solved placement. Four misplaced bodies carry a collision geom (the servos, 55.2 mm and 114.2 mm out) and all 24 carry mass, so a dynamics pass on such a model is a pass on geometry that does not match the design. Robin and Heron write no rotated body at all, so neither exercised this; the defect predates ot7. Not yet fixed: the next unit is a fixture holding a fixed-attachment body's frame to the implied transform, then the fix.
- target: first-snow-5587 — The closing report carries F7's smoke and inventory: docs/probes/ot7/REPORT.md gains an iteration-167 section with the ADR-392 collector change, the dynamics half's passing checks, the exact-BREP half's agreement-gate finding and its 4-of-28 versus 24-of-28 inverse-transform measurement, and the measured inventory; the F7 row of the F1-F9 evidence table now records catalog hardware met at 24 catalogued components against five printed sources and the smoke as unproven rather than failing, linking the receipt and its assessment. F10 still has no critic acceptance of done.
