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

**F1's evidence is complete pending the owner's checkbox (ADR-346), and it now has field evidence from a real design turn [rec: stormy-snow-5452].** Every successful CLI bridge `write_script`, `edit_script`, `set_params` and `rebuild` reply carries fit verdict, thresholds, check counts and every failing pair's names, distance and common volume, read from published `inspect scope=clearance` measurements under the bridge lock, never inferred from stdout. Unknown pairs fail; unreadable measurements are unavailable and never refuse the build. `clearance` is on the agent's inspect surface and its instructions treat printouts as claims and measurements as evidence [rec: happy-dawn-1960] [rec: steady-quartz-9854].

**The measured fit the agent sees now includes the swept half (ADR-366) [rec: mellow-sky-2112].** `fit.sweep` rides beside `fit` in the same build reply, computed by `cadex_cli.clearance.sweep_summary` from the `clearance_sweep` the same `inspect scope=clearance` value already carries, so it costs no second engine call and no second measurement: coverage, one compact row per limited joint with its minimum distance, maximum common volume and first-contact value with the pair that reached it, and every pair that interpenetrates anywhere in a range, by name, with the joint it is through. It keeps its own verdict, so `fit["verdict"]` still means the solved pose and F1's claim is unchanged; `pass` requires every limited joint swept to completion with no overlap, and missing coverage is never a pass. Like the static half it is advisory — a failing swept fit is reported, never refused. The bridge progress line and the prose report carry both halves, and the system prompt now says motion fit is measured and that an unswept joint has been checked at one pose only. `cli/tests` 783 passed, 1 skipped; six new tests red on the previous code, two of them live against the real engine [rec: mellow-sky-2112].

**In the field, on `ot7-heron-repair-d`, the agent read the clearance summary and pairs first and after every accepted edit, and drove six accepted revisions from the published failing rows, 15 → 2 → 1 → 2 → 1 → 0 → 0, with 35 of its 46 tool calls being inspects [rec: stormy-snow-5452].** A pair the report never flags is not acted on: the undeclared horn-to-link attachment at 0.2 mm clears the 0.1 mm default, was declared clearance by the agent, and passed. That is a limit of what F1 shows, not a defect in it: F1 shows the measurements, and F2's intent mechanism cannot flag an attachment nobody declared [rec: stormy-snow-5452].

**Paged build replies are regression-pinned through the real inspection pager.** A sixty-pair fixture puts an unknown pair, a 248.2 mm³ intersection and a missed contact at 0.2 mm on the later page, with a world finding alongside them; the reply includes all four named failures and numbers. An unreadable later page yields unavailable fit with its actual read error, while acceptance and revision remain successful. Bridge history and last-fit state agree. Both cases pass, both fail under a dropped-continuation negative control, and the full CLI suite passes 686/1 skipped. `docs/CLI.md` documents this existing behavior [rec: tidy-journey-9462].

The original forty-pair limit is removed at `f2bf2c83`; two fixtures with sixty failing pairs pin complete summary and bridge replies, with no truncation field. The real-engine misleading-stdout transaction fixture receives the measured 100 mm³ intersection despite the script printing “no overlap.” The tool-surface test, `docs/CLI.md` and ADR-346 are updated. Full CLI verification on unchanged `f2bf2c83`: 636 passed, 1 skipped, exit 0 [rec: happy-dawn-1960] [rec: steady-quartz-9854].

The `fit` verdict itself covers the initial solved pose only; intent remains F2, and since ADR-366 the reply carries the swept measurements beside it as their own block (F3, `curious-quill-9036`) [rec: mellow-sky-2112]. No assembly components yields unavailable, meaning nothing was checked. Reconcile judgement: stay `working` on the complete-list evidence plus one real turn's use of it; the checkbox is the owner's, and this does not close F9 or claim an unassisted design result beyond what `polished-forest-0215` records [rec: happy-dawn-1960] [rec: steady-quartz-9854] [rec: stormy-snow-5452].

Charter criterion: **F1. The agent sees measured fit.** After every design turn that builds, the tool reply carries a fit summary computed from the published clearance measurements, never from stdout: the check counts and every failing pair by name with its distance and common volume. `clearance` is an inspect scope on the agent's tool surface. The system prompt no longer tells the agent to verify fit by printing. Evidence: `test_project_tool_surface.py` updated with an ADR; a transaction test in which a script prints "no overlap" while its solids overlap receives the overlap in its reply; `docs/CLI.md` updated. Declared target `gap-f1-agent-sees-measured-fit`; a record may say "ticks F1" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

## Negative knowledge

- [scope: happy-dawn-1960's initial F1 completion claim | confidence: high | evidence: steady-quartz-9854] The original forty-pair slice omitted failing pairs and did not meet F1. The complete-list correction and its full CLI verification supersede that claim.
- [scope: the fit reply as a detector of undeclared attachments | confidence: high | evidence: stormy-snow-5452] A gap that clears the default threshold with no declared intent is never a failing row, so the agent does not act on it. Seeing the measurements is not the same as knowing which pairs should touch.

## Provenance

- kind-dusk-1609 — ADR-341 declared F1 and its evidence bar
- happy-dawn-1960 — ADR-346 measured fit replies, inspect scope, prompt and transaction evidence
- steady-quartz-9854 — removes the forty-pair defect and verifies all 636 CLI tests with one skip
- tidy-journey-9462 — known-answer late-page failures and unavailable fit on later read failure; negative control detects both cases
- stormy-snow-5452 — field evidence: in a real repair turn the agent read clearance first and after every edit and drove six accepted revisions from the failing rows; an undeclared 0.2 mm attachment was not acted on
- mellow-sky-2112 — ADR-366: the build reply carries `fit.sweep` beside `fit`, so the measurements the agent sees include motion fit; advisory, its own verdict, no second engine call
