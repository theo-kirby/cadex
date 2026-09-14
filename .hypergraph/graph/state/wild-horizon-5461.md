---
node_id: 0c71b7d0-970a-5028-a6c9-cd3894e6a386
slug: wild-horizon-5461
title: F1. The agent sees measured fit
created_at: '2026-09-14T17:28:04+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: working

## Current

**F1's evidence is complete pending the owner's checkbox (ADR-346).** Every successful CLI bridge `write_script`, `edit_script`, `set_params` and `rebuild` reply carries fit verdict, thresholds, check counts and every failing pair's names, distance and common volume, read from published `inspect scope=clearance` measurements under the bridge lock, never inferred from stdout. Unknown pairs fail; unreadable measurements are unavailable and never refuse the build. `clearance` is on the agent's inspect surface and its instructions treat printouts as claims and measurements as evidence [rec: happy-dawn-1960] [rec: steady-quartz-9854].

The original forty-pair limit is removed at `f2bf2c83`; two fixtures with sixty failing pairs pin complete summary and bridge replies, with no truncation field. The real-engine misleading-stdout transaction fixture receives the measured 100 mm³ intersection despite the script printing “no overlap.” The tool-surface test, `docs/CLI.md` and ADR-346 are updated. Full CLI verification on unchanged `f2bf2c83`: 636 passed, 1 skipped, exit 0 [rec: happy-dawn-1960] [rec: steady-quartz-9854].

Fit covers the initial solved pose only; intent and swept checks remain F2 and F3. No assembly components yields unavailable, meaning nothing was checked. Reconcile judgement: mark `working` on the corrected complete-list evidence, not the premature parent claim; this does not close F9 or claim an unassisted design result [rec: happy-dawn-1960] [rec: steady-quartz-9854].

Charter criterion: **F1. The agent sees measured fit.** After every design turn that builds, the tool reply carries a fit summary computed from the published clearance measurements, never from stdout: the check counts and every failing pair by name with its distance and common volume. `clearance` is an inspect scope on the agent's tool surface. The system prompt no longer tells the agent to verify fit by printing. Evidence: `test_project_tool_surface.py` updated with an ADR; a transaction test in which a script prints "no overlap" while its solids overlap receives the overlap in its reply; `docs/CLI.md` updated. Declared target `gap-f1-agent-sees-measured-fit`; a record may say "ticks F1" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

## Negative knowledge

- [scope: happy-dawn-1960's initial F1 completion claim | confidence: high | evidence: steady-quartz-9854] The original forty-pair slice omitted failing pairs and did not meet F1. The complete-list correction and its full CLI verification supersede that claim.

## Provenance

- kind-dusk-1609 — ADR-341 declared F1 and its evidence bar
- happy-dawn-1960 — ADR-346 measured fit replies, inspect scope, prompt and transaction evidence
- steady-quartz-9854 — removes the forty-pair defect and verifies all 636 CLI tests with one skip
