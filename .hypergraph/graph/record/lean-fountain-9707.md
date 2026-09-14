---
node_id: 27ca1083-59bf-527d-99e2-3ddae5c4887e
slug: lean-fountain-9707
title: 'F8: bounded accepted-artifact smoke with exact posed BREP checks (ADR-352)'
created_at: '2026-09-14T20:44:50+00:00'
parents:
- kind-flint-2780
summary: ''
artifacts:
- docs/probes/ot7/f8-smoke.json
---
## What

Implemented `cadex smoke --out DIR` (ADR-352) for F8: retained accepted artifacts,
zero action or held position actuators, finite-state checks, exact BREP
component-pair overlap across the sampled dynamics trace, and floor support or
a held grounded base. The command reports failing measurements without changing
acceptance. Docs/CLI.md documents it; docs/ROADMAP.md marks the implementation.
The evidence index is `docs/probes/ot7/f8-smoke.json`.

## Why

The critic selected F8 after the scheduled reconcile. This unit follows
`kind-flint-2780`, making the bounded smoke available before seeded repair and
unassisted design experiments. I followed that selection, not the stale plan's
section-view work. An uncommitted smoke draft was present on arrival; it was
completed within this unit. Its rebuild would accept, and its MuJoCo contact
check could not see component pairs without collision geoms. Those were replaced
before claiming evidence. There was no product-agent design turn or actor edit
to an ot7 design, no dashboard change and no policy training.

## Method

Read retained script.json and the pinned result.json under the project lock,
check accepted revision/digest and available model/task hashes, copy artifacts,
and hold the lock through measurement. Neither restore nor rebuild executes.
The dynamics child records absolute component poses. A trusted FreeCAD child,
following the existing CLI export process seam, composes each source BREP's
local placement with those poses. It measures every component pair, including
physics-excluded pairs and parts with no collision proxy. First-frame distances
and common volumes must agree with published static clearance. Missing solids
or disagreement is an error, not a pass. No protocol op or payload changed.

Both children share a wall-time deadline capped at 300 seconds. Samples include
initial and final poses, actual solver times are retained, and requested trace
intervals are capped at 15,000. The complete smoke.json is written only after
both children finish; intermediate dynamics evidence has a distinct schema.
Finite state is checked per solver step, warning counters survive resets, and
optional task termination conditions are evaluated without training or policy
execution.

Final verification:
- `pixi run test-engine`: 2,127 passed, 53 skipped, 314.19 s.
- `pixi run python -m pytest cli/tests`: 666 passed, 1 skipped, 532.81 s.
- Staged-engine lifecycle plus the complete smoke suite: 43 passed, 22.42 s,
  using `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64` and pytest
  targets `src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py cli/tests/test_smoke.py`.
- Focused smoke suite: 25 passed, 10.98 s.

An initial full CLI run also passed (664 passed, 1 skipped); the final full run
above was repeated after the remaining error-handling and lock-lifetime changes.
No full build was needed: engine source and the payload contract are unchanged.
Raw final logs and fixture receipts are retained in the operator's project
`cadex-projects/ot7-f8-checks/evidence/`; the committed evidence index lists
portable relative artifact paths, SHA-256 digests, counts and source hashes.

## Result

F8 has implementation and known-answer fixture evidence (ticks F8, subject to
owner/critic review). A grounded fixture passes with zero exact overlap across
101 poses. The falling-arm fixture has no collision geoms, so its proxy check
passes, but exact geometry reports 1,463.7845106574737 mm³ between base and swing
at 1.64 s and fails. Two overlapping boxes yield the analytic 400 mm³, fail at
1e-6 mm³ tolerance and pass at 401 mm³. The remaining fixtures cover floor rest,
2 mm initial floor burial, no floor, unstable dynamics, hold versus zero action,
termination, non-integral sampling, timeouts, stale-receipt prevention, no
accepted attempt, tampered model rejection and byte-preserved accepted state
when the working script is deliberately broken.

The limits are explicit: component checks are sampled rather than continuous;
floor penetration and support use the model's collision proxies; unsupported
non-BREP components or mismatched initial measurements cannot pass. Existing
NumPy/MuJoCo and FreeCAD are used; no dependency was added. No whole-goal completion
is claimed. F9 gains fresh suite and packaged evidence, but the retained ot6
comparison and the unassisted design/repair experiments remain outside this unit.
Dispatch closed: 1 unit — bounded accepted-design smoke with exact sampled component fit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 20b2060d78de137a1829514a7209028a77b7c2cf

## State Impact

- target: honest-ivy-8824 — F8 implemented and fixture-verified: cadex smoke reads retained artifacts without accepting, checks finite state, exact sampled component overlaps and support, with a shared 300-second bound; 25 smoke tests and staged verification pass. Sampled checks and proxy floor support are explicit limitations.
- target: chilly-union-8972 — cadex smoke is a documented no-token command with accepted identity, complete measured verdicts and project-local trace/geometry receipts; no restore, rebuild, protocol change or new dependency.
- target: eager-summit-3153 — Latest F8 verification: engine 2127 passed/53 skipped, final CLI 666 passed/1 skipped, staged lifecycle plus smoke 43 passed. No engine source or payload change and no full build; ot6 comparison remains open.
