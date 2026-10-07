---
node_id: 4457e1d5-4024-5020-9279-2a3d7229f4e9
slug: smooth-pond-6955
title: 'ADR-583: smoke allows a threaded bolt its thread at every pose'
created_at: '2026-10-07T01:48:41+00:00'
parents:
- warm-otter-8152
summary: ''
---
## What

ADR-583, commit `2eeb3ead`. `cadex smoke`'s per-frame geometry check now uses the engine's thread allowance for a bolt threaded into a printed part (ADR-492):
- `cli/cadex_cli/smoke.py`, `thread_allowances(items, static, maximum_volume)`:
  - builds each component's catalog row from the retained outputs, the way the clearance scope builds them (`CadexInspection.py`);
  - calls `CadexFitReport.thread_allowances`;
  - keeps an allowance only for a pair whose published solved-pose overlap is above the volume limit and within the allowance. That is the swept check's gate (`sweep_summary`).
  - The result is passed to the child as `plan["thread_allowances"]`.
- `cli/cadex_cli/smoke_geometry.py`:
  - a pair fails only when its worst volume exceeds both the limit and its allowance;
  - the row carries `thread_allowance_mm3`;
  - the result counts `threaded`.

Smoke blocker (b) is fixed.

## Why

The critic named blocker (b): apply the static row's fit intent per frame, take the rule from the engine's static clearance, and invent no tolerance. I did that.
- **Where the rule actually lives.** The worker's `fit_intent` (contact / clearance / attached) grants no overlap: `pair_status` checks volume before intent. Threaded engagement is granted by ADR-492's `thread_allowances` in `CadexFitReport`, which the static block uses (`threaded` status) and the sweep keeps through motion. Smoke now reuses that exact function and gate.
- **No new tolerance.** The allowance comes from catalog part numbers and ISO minor diameters, with the engine's own 1e-3 margin.

## Method

1. Confirmed on `/tmp/o4s-smoke1` (the ADR-582 receipt) that all 33 failures are bolt pairs at `time_s` 0.0.
2. Confirmed the retained outputs carry `catalog {family: bolt, part_number: m2x8-socket}`.
3. Wrote two failing-first tests:
   - `test_smoke_geometry_bound.py::test_a_threaded_bolt_holds_its_allowance_while_a_real_collision_fails`:
     - setup: a cylinder half-sunk in a block (2π mm³, allowance 7), and a ball driven into the block;
     - only the ball fails. On the old child the bolt fails too, which was verified by stashing the change.
     - The bolt driven 2 mm deeper (4π mm³) fails.
   - `test_smoke.py::test_a_thread_allowance_holds_only_for_a_bolt_threaded_at_the_solved_pose`:
     - only a bolt-into-printed pair with 0 < static volume ≤ allowance holds one;
     - zero overlap, past the thread, and bolt-into-catalog-servo hold none;
     - the value equals π/4(2²−1.567²)·8·1.001.
4. Re-ran the full `cadex smoke --project /tmp/o4s --out /tmp/o4s-smoke2`.

## Result

What is true now:
- Smoke on the 66-component fresh-session biped copy: **186.49 s, verdict `pass`**, exit 0.
  - finite, penetration, support, termination and components are all true;
  - 33 threaded pairs, worst at 83.5% of their allowance over 101 frames;
  - no other pair overlaps;
  - booleans 4,845 run and 9,797 reused, unchanged.
- Docs updated:
  - `docs/CLI.md`, the smoke section;
  - `docs/DECISIONS.md`, ADR-583;
  - `docs/probes/orun4/REPORT.md`: §7 defect 2 now reads fixed, and the ADR table gains a row.
- Gates at `2eeb3ead`, in the foreground:
  - CLI suite as one command with the GPU hidden: 1214 passed, 1 skipped, 473.64 s (under 480 s);
  - `pixi run test-engine`: 2611 passed, 59 skipped, 345.34 s.
- Nothing under `src/` changed, so no engine rebuild, stage or packaged gate was needed.

Assumption: as in the fit block, only catalog bolts into printed parts carry an allowance. Press fits get none, and any other overlap still fails.

The reconcile tail is now three records (solemn-moon-8508, warm-otter-8152, this one). The critic asked for a reconcile next, then a re-claim of done.

Dispatch closed: 1 unit — smoke applies the engine's thread allowance per frame; the fresh-session biped smokes pass (ADR-583)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 2eeb3eade23caad8a077829da6a5f502af4ea95b

## State Impact

- target: salty-isle-4063 — cadex smoke applies the engine's ADR-492 thread allowance per frame, gated as the sweep gates it (ADR-583): the 66-component fresh-session biped smokes pass in 186.49 s with 33 threaded pairs at most 83.5% of their allowance; smoke's three fresh-session blockers are closed
