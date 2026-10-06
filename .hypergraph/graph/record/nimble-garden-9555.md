---
node_id: 2c093764-0097-5e61-893b-8823f4328461
slug: nimble-garden-9555
title: 'G2 style revised: foot bounded by standing height, level thigh for sprawled legs, roll limit from measured first contact (ADR-566)'
created_at: '2026-10-06T14:40:41+00:00'
parents:
- ancient-trail-9417
summary: ''
---
## What

Revised the `printed-legged-robot` style (ADR-566) on the three gaps the G2 fresh-session check found: (1) **COMPACT HAS A NUMBER**: each sole is at most a quarter of the robot's standing height long and an eighth of it wide, with the ratios recorded, and stability is credited to the strip and its place under the COM, never to the foot's area; (2) the level-thigh pose is asked of a **sprawled leg** only, and an upright leg stands with the thigh down to a slightly bent knee; (3) **MEASURE WHERE THE FEET MEET**: sweep hip roll with the inward limit opened wide, read the joint row's `first_contact` from `inspect scope=clearance path=/clearance_sweep/joints`, set the limit at least two sweep steps short of it, and record both angles. The look checklist names a sole past the bound. `docs/DESIGN-LANGUAGE.md` §5 and the LESSONS.md rows L4 and L7 carry the same rules.

## Why

This is the critic's named unit: G2 is not met, because the fresh session's first accepted design missed the foot rule (a 72 × 40 mm slab under a 210 mm robot, about 0.34 and 0.19 of its height). The critic asked for exactly these three edits, pinned in both test_agent_guidance files, with an ADR. It also asked for the two unreconciled records to be folded "now if cheap". I did not: a work iteration forbids reconcile. The tail is now three records (northern-stream-2677, ancient-trail-9417 and this one), so the next reconcile pass should fold them.

## Method

- Bounds from evidence: the reference robot's passing feet, 64 × 32 mm on about a 31 cm robot, are about 0.21 and 0.10 of its height. The fresh-session slab was 0.34 and 0.19. A quarter and an eighth admit the first with margin and reject the second. They are ratios, not the reference numbers, so the existing check that no reference number appears still holds.
- Checked against source that the sweep publishes `first_contact` (value, unit, pair) on each joint row (`CadexFitReport.py:440`).
- Tests: `src/Mod/cadex/cadex_tests/test_agent_guidance.py::test_the_style_bounds_the_foot_scopes_the_level_thigh_and_derives_the_roll_limit` checks each phrase in the style and not in the base, and that the level thigh sits inside the sprawled-leg clause. `cli/tests/test_agent_guidance.py::test_the_style_s_foot_thigh_and_roll_rules_reach_a_project_that_chose_it` checks that the rules reach `cadex guidance --project` for a project that chose the style and never reach the base. Both fail on the ADR-565 style (verified: 2 failed, 21 passed) and pass with the change (23 passed).

## Result

What is true now: the style bounds the foot by the robot's standing height, asks the level thigh of sprawled legs only, and derives the inward roll limit from the measured `first_contact`. The base is unchanged and the tool surface is unchanged.

Gates, all in the foreground:
- `pixi run build-engine` ran.
- `pixi run test-engine`: 2600 passed, 58 skipped (340 s).
- CLI suite with the GPU hidden, in thirds: 400 passed (165 s); 353 passed, 1 skipped (331 s); 443 passed (129 s).
- One concern: the whole CLI suite as one command ran past the shell's 600 s limit (about 625 s summed), so it was stopped and re-run in thirds. ADR-564's 614 s figure is still over the limit; the charter's 8-minute target is not met.

- Assumption: the quarter and eighth bounds are *owner to confirm*. They are an upper bound the passing robot met with margin, not a measured optimum. This is recorded in ADR-566 and the ledger.
- G2 is still open. The next unit re-runs the fresh session on a new `orun4-*` project under the revised style, then moves to H1.
- The tail is three unreconciled records; a reconcile is due.

Dispatch closed: 1 unit — printed-legged-robot style revised: foot bounded by standing height, level thigh for sprawled legs only, roll limit from measured first contact (ADR-566)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 10020100c007beceadbf221a702b7fd083c99b34

## State Impact

- target: narrow-beacon-6703 — the printed-legged-robot style now bounds each sole (≤1/4 standing height long, ≤1/8 wide), scopes the level thigh to sprawled legs, and derives the inward roll limit from the sweep's measured first_contact (ADR-566, commit 10020100); a second fresh session is still owed
