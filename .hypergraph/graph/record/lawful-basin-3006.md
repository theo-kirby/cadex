---
node_id: 4c8a9b86-151b-5c5f-b2c0-71a08e3ce26e
slug: lawful-basin-3006
title: 'ot10: ADR-428 hexapod-7 build CPU measured (sweep off 212 vs 10° 210 CPU-s in the domain worker); T3/T4 become overlay language'
created_at: '2026-09-28T11:00:51+00:00'
parents:
- first-journey-3938
summary: ''
---
## What

Measured where hexapod attempt 7's build CPU goes, then acted on it (ADR-428).
The sweep is **not** the cost. So the T3/T4 diagnosis became one overlay change,
taught as language: limbs taper in depth as well as width, and a printed cradle
that follows a servo case face for face is covered by `shell` or rounded into
the limb and joint cap. `docs/DESIGN-LANGUAGE.md` §1 and §5 now say the same.
A regression pins the change.

## Why

This is the critic's named unit. It must end in a change, and the rule was:
if the sweep is not the cost, make one overlay change about T3/T4. A5
(`loyal-fountain-8709`) is the highest-ranked open criterion, and attempt 7
missed it on T3 and T4. I did not start the A6 concept sheet. The critic
ordered it *after* this unit, and one dispatch is one unit.

## Method

- **Copies.** Three `/tmp` copies of `ot10-hexapod-7` at `f0a77bfb`, with
  `sweep_step_degrees` at 17.5 (rebuilt with `cadex export`), at 10.0, and
  removed. The 10.0 and removed copies were rebuilt with
  `cadex script --set`, all under `/usr/bin/time -v`. Two fresh copies
  (10°, off) were then rebuilt again while a poller read every FreeCADCmd
  process's utime+stime and thread count from `/proc` every 0.5 s.
- **Wall time.** Read from each accepted `result.json`'s `clearance_sweep`
  block.
- **Overlay change.** The change is in `cli/cadex_cli/agent.py`. The
  regression `test_limbs_taper_in_depth_and_cradles_do_not_show_as_servos`
  fails with the overlay reverted and passes with it.

## Result

- **The sandboxed domain worker's CPU does not depend on the sweep.** It
  spent 209.9 CPU-s at 10° and 212.0 CPU-s with the sweep off, against a
  limit of 300. The geometry alone uses 70% of the budget.
- **The sweep runs one child FreeCADCmd per joint, and each child has its
  own RLIMIT_CPU.**
  - At 10° the 12 children spent 12.7–55.6 CPU-s each, 456 in all.
  - Hips cost about 50–56 CPU-s and knees about 13–33.
- **Wall time decides whether the sweep completes.**
  - At 17.5° it completed 12/12 in 129.2 s.
  - At 10° it was **incomplete**: it hit the 180 s total wall budget at
    `hip_rr`, with 10/12 joints complete.
- **Whole commands:**
  - 17.5° `export`: 1,149 CPU-s, 7:00 wall.
  - 10° `script --set`: 625 CPU-s, 4:38 wall.
  - Off: 227 CPU-s, 1:37 wall.
  - These totals include tessellation and the sweep children.
- **What this means.** The agent's ADR-008 ("10° ran past the 300
  CPU-second limit") misattributes the cause. At 10° the build is refused
  as an incomplete sweep by the wall budget, never by the CPU limit. The
  one `cpu_limit` refusal in the turn came from geometry: the loft-edge
  fillets it then dropped, on top of 210 CPU-s.
- **No budget or sweep change** follows from the measurement.
- **Now true:**
  - The overlay's `TAPER TO A FOOT` requires depth taper ("a plate of one
    thickness cut to a tapering outline is still a flat bar edge-on").
  - `SHELLS HIDE THE HARDWARE` names servo-shaped cradles.
  - The rubric, proxies, bar and procedure are unchanged, and the new text
    uses no rubric anchor wording.
- **Tests.**
  - `cli/tests/test_turn_loop.py`: 44 passed.
  - The full CLI suite: 1014 passed, 1 skipped.
  - The engine is untouched.
- **Concern.** The poller samples every 0.5 s, so each process's CPU may
  be under-read by about 2 CPU-s. That does not change the conclusion.
  The geometry's 210 CPU-s leaves about 90 CPU-s for refinement such as
  fillets. That margin, not the sweep, is the budget that binds. If a
  later attempt hits it again, the next lever is the geometry cost (which
  ops dominate), not the sweep.
- **Not measured.** Whether the new sentences move T3/T4. That needs
  hexapod attempt 8 on a new `ot10-*` project.
- **Next unit.** Per the critic, start the A6 concept sheet on
  quadruped-3.
- **Reconcile.** The unreconciled tail is now 3 records: reconcile is due.

Dispatch closed: 1 unit — measured hexapod-7's build CPU (domain worker 210 CPU-s with the sweep on or off; the sweep is per-joint children and wall-bound), so no sweep/budget change; turned T3/T4 into one overlay change (depth taper, servo-shaped cradles) with a regression (ADR-428).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 711ab677ec287c934701800299320672c3d46963

## State Impact

- target: loyal-fountain-8709 — hexapod-7's build CPU measured on /tmp copies: the domain worker spends ~210 CPU-s of 300 with the sweep on or off; the sweep runs in per-joint children and is bounded by its 180 s wall budget (10° incomplete at hip_rr, 17.5° complete in 129 s), so no sweep/budget change. ADR-428: the overlay and DESIGN-LANGUAGE now teach depth taper and servo-shaped cradles covered or rounded (regression in test_turn_loop.py); unmeasured on a design until hexapod attempt 8.
- target: chilly-union-8972 — overlay TAPER TO A FOOT requires depth taper; SHELLS HIDE THE HARDWARE names servo-shaped printed cradles (ADR-428).
