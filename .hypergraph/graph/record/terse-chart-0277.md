---
node_id: b8e57ee7-360c-55c7-8752-77873ff89d06
slug: terse-chart-0277
title: A fixed joint holds a pose; it does not require touching (ADR-380, withdrawing ADR-379)
created_at: '2026-09-16T23:50:24+00:00'
parents:
- glad-wing-9845
summary: ''
---
## What

ADR-380, withdrawing ADR-379 the same day it landed.

ADR-379 ruled that a pair an unsuppressed `fixed` joint welds **and** a
`clearances=` declaration gives a running minimum is a self-contradiction,
and made the contradiction itself the failing check `clearance under weld` —
at any measured gap, with `minimum_mm` never consulted. Its argument was "no
measured gap makes 'one rigid body' and 'a running gap' both true".

The argument does not hold. **A fixed joint fixes the relative pose of two
components; it does not assert that their solids meet** — which is exactly
why ADR-370 made "does this weld's gap close?" a separate advisory fact
rather than a check, in its own words "because a standoff or a captive
fastener between them is a legitimate design and only the design knows which
it is". And **a declared minimum clearance is a floor on a distance, not a
claim that the pair is in relative motion.** A board rigidly held 2 mm over
its standoffs, a shroud around a pulley, a magnet over its sensor: each is
one rigid body *and* meant to stay apart, and the `clearances=` declaration
is the only place the design can say by how much. ADR-379 would have failed
every one of them at every gap and told the author to repair a design with
nothing wrong with it.

Landed in this unit, on top of `f37e8a08`:

- `_check_fit` no longer emits `clearance under weld`; a `clearances=`
  declaration on a welded pair is judged by the minimum it declares, exactly
  as an unwelded pair's is (ADR-372's rule, restored).
- The status is gone from `pair_status`, from `fit_summary`'s note, from
  `cadex clearance`'s report and from the walk review's offending set.
- The agent's system prompt no longer says "NEVER DECLARE A `clearances=`
  GAP ON A PAIR YOU WELD". It says instead that such a declaration is
  legitimate and checked as written, and — the part that matters for the
  defect ADR-379 was reaching for — that `fit.attachments` must be read: a
  weld reported `not touching` is a connection the geometry does not make
  unless a standoff or fastener spans the gap.
- Kept, because it is a fact rather than a verdict: the welding joints still
  ride on such a declaration (`{"kind": "clearance", "minimum_mm": …,
  "joints": [...]}`), and `cadex clearance` still writes `declared minimum
  <n> mm, and welded by <joint names>` as the row's detail. That join is
  what lets a reader tell a standoff from a floating horn.
- ADR-379 is marked superseded in `docs/DECISIONS.md` and kept in full;
  `docs/XSCRIPT.md`, `docs/CLI.md`, `docs/INTEGRATION.md` and
  `docs/probes/ot7/REPORT.md` are corrected forward rather than reverted,
  each naming what was tried and why it was withdrawn.

## Why

The critic rejected the previous iteration and asked for exactly this, in two
parts: fix forward the ADR-379 rule in `cadex_assembly_worker.py` and
`cli/cadex_cli/clearance.py` ("a fixed joint preserves relative pose; it does
not require touching, and minimum clearance does not imply motion"), with a
regression where rigidly separated components satisfy their declared minimum
without failing; and supersede `glad-wing-9845`'s success claims through a
corrective record targeting its four impact nodes, preserving it as history.
Both are done here, and nothing was done instead of them. The criterion this
serves is **F2, fit intent is declared and checked** (`winter-key-1482`):
a check that fails correct designs is not a check F5–F7 can be held to.

## Method

Removed the rule at both ends and restored the ADR-372 path, then wrote the
tests that would have caught it. The regression the critic asked for exists
at both levels: in the engine, `('clearance', False, 2.0, 0.0, [])` — welded,
rigidly separated by 2.0 mm, declared 0.5 mm, failing nothing — with its
paired negative at 0.02 mm still failing `below clearance`, so the minimum is
provably consulted; in the CLI,
`test_a_welded_pair_that_meets_its_declared_minimum_reaches_the_reply_clear`
takes a board 2.0 mm over its welded standoff through `fit_summary` and
`write_clearance` and asserts no failing check, no note, and both facts on
the row. Every one of those was red under ADR-379, which failed them alike.
The real-OCCT Heron fixture reads `fit_failures == []` on the horn pair
again, with its published intent carrying both the declared 0.05 mm and
`weld_horn`. `test_the_weld_rule_moves_no_retained_number` holds what it
held: no retained receipt carries an `intent` key at all, so no number in
`docs/probes/ot7/REPORT.md` moves under either decision.

One slip, caught and repaired inside the unit: the scripted rewrite of the
tail of `cli/tests/test_clearance.py` truncated six pre-existing tests
(ADR-378's swept-check suite among them). They were restored verbatim from
`HEAD` and the file now reads 65 added / 61 removed against it.

Gates: `pixi run test-engine` 2,161 passed / 53 skipped; `cli/tests` 828
passed / 1 skipped, re-run in full after the restoration; `build-engine` and
`stage-engine` clean; the packaged lifecycle gate 21 passed against the
freshly staged payload (`build/engine/cadex-engine-0.0.0-linux-x64`).

## Result

The four fit checks are the four fit checks again — overlap, missed contact,
below clearance, unknown — plus world geometry, and a welded pair that
declares a gap is held to the gap it declared. No protocol op, no
`OP_ARG_SPECS` change, no payload contract change and no `shell/` diff.

**What is now true about F4's defect, plainly.** The floating horn on
`ot7-heron-repair-d` is real and unrepaired: `weld_horn_shoulder` holds
`comp_horn_shoulder` 0.2 mm off `comp_upper_arm` and nothing spans it. It is
**not** a failing fit check and a rebuild reports zero, exactly as F4
measured. What names it is `fit.attachments`, `not touching`, with its joint —
advisory by ADR-370's deliberate choice. `glad-wing-9845`'s claim that a
rebuild "would now report two failing pairs where it reported none" is
withdrawn, and so is its claim that F6's and F7's bars were made harder to
meet falsely; what those two gained is the opposite, a check that no longer
fails a legitimately welded-and-spaced design. Its reading of F4's numbers
stands.

**Open, and deliberately not decided here:** whether an unspanned weld gap
should become a check of its own. It needs a way for a design to declare the
spanner — a standoff, a captive fastener — which is why ADR-370 left it
advisory, and inventing one inside a correction would be the same mistake
ADR-379 made. The agent's instructions now point at the block, which is the
reversible half.

F6 and F7 remain blocked on provider capacity with every slot unspent. No
`ot7-*` design was edited, no frozen prompt was spent, no capacity probe was
taken and no run-lifecycle command was issued.

Dispatch closed: 1 unit — ADR-380 withdraws ADR-379's `clearance under weld`, restores the declared minimum on welded pairs, and pins the rigidly-separated regression at both levels.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: c41191f554e11f8957338a3a0cedc9d2154a7e82

## State Impact

- target: winter-key-1482 — F2's checker is back to its four checks plus world geometry: ADR-380 withdraws ADR-379's fifth finding, 'clearance under weld'. A clearances= declaration on a pair an unsuppressed fixed joint welds is judged by the minimum it declares, exactly as an unwelded pair's is, because a fixed joint fixes a relative pose without requiring the solids to touch and a declared minimum is a floor on a distance rather than a claim of motion. Two components rigidly separated by 2.0 mm with a declared 0.5 mm minimum now fail nothing, pinned at both levels; the same shape at 0.02 mm still fails below clearance. Kept: the welding joints still ride on such a declaration and cadex clearance still writes 'declared minimum <n> mm, and welded by <joints>' as the detail — a fact to join, not a verdict. The status is gone from the engine, pair_status, the walk's offending set and the agent's prompt, which now says instead to read fit.attachments and treat a 'not touching' weld as a connection the geometry does not make unless a standoff or fastener spans it.
- target: polished-forest-0215 — F4's measured result is unchanged and so is what a rebuild would report: zero failing checks. glad-wing-9845's claim that a rebuild of ot7-heron-repair-d 'would now report two failing pairs where it reported none' is withdrawn with ADR-379. The floating horn is real and unrepaired — weld_horn_shoulder holds comp_horn_shoulder 0.2 mm off comp_upper_arm with nothing spanning it — and what names it is fit.attachments, 'not touching', advisory by ADR-370's deliberate choice. Whether an unspanned weld gap should become a check of its own is open and undecided; it needs a way for a design to declare the spanner.
- target: narrow-dune-9454 — F6's bar is the four fit checks again. glad-wing-9845's claim that ADR-379 made the bar harder to meet falsely is withdrawn: what F6 gains from ADR-380 is the opposite, a checker that no longer fails a legitimately welded-and-spaced design (a board on standoffs, a shroud around a pulley). F6 itself remains blocked on provider capacity with all four slots unspent; no probe was taken this iteration and no frozen prompt was sent.
- target: rapid-grove-9687 — F7's bar is corrected the same way and F7 remains blocked behind F6 with all four slots unspent.
