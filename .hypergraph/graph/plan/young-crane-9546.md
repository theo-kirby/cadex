---
node_id: c1e64944-a027-59bb-80ed-a530f6fc6dad
slug: young-crane-9546
title: short
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **Finish the GSL tail and resolve Start's remaining evidence condition (mission 3; windy-pebble-4630, round-glacier-2865, green-sea-3991).** Start disable/delete landed; do not repeat them. First locate durable output for the reserved post-commit HEAD manifest test, or run that focused check on the committed tree and record its result. Help plus Start qualify as two whole-tree removals only with that check passing; declare the resulting state impact rather than editing the projection. Then re-audit tracked GSL consumers on the post-delete tree. If none remain, remove only the GSL gitlink, its .gitmodules entry, setup-engine checkout reference and dead CMake references; update current setup instructions that still name GSL, the ADR, ledger, ROADMAP fact and inherited notices/manifest where applicable. Never vendor submodule contents. Run setup-engine and release configure; CMake changes require the zone's release build, at most one full build, and removals require relevant tests/licensing checks. If payload rules change, finish install/staging before the packaged lifecycle gate. If a consumer or gate blocks removal, record the exact boundary and stop this unit. Preserve Test, Assembly, retained Qt and shell/lib. [rec: rustic-spire-7084] [rec: southern-wood-6367] [rec: still-quill-0059] [rec: fair-snow-3443]
2. **N20 independent interface verification, only after item 1 lands or records its blocker (mission 4; rising-banner-4325, brave-stone-9609).** Follow docs/L3-COVERAGE.md and the existing N20 contract: one actual-worker test unit measuring the D-shaft and mounting bores independently, including a placed instance. Use sourced existing dimensions; keep assumed bore depth and transition limits explicit. No new SKU, API or invented installation-fit claim. Run the full engine suite, actual-worker interface/library coverage and packaged lifecycle checks, with staging complete before inspection; if implementation changes are necessary, include the required single build and fresh staging. Record numerical probe evidence, ADR/doc/ROADMAP facts as applicable and real impacts. This improves verification and cannot close full L3. [rec: steady-rain-3009] [rec: fair-snow-3443]
3. **Qualify one additional common BLDC candidate, only after item 2 lands or is blocked (mission 4; rising-banner-4325, brave-stone-9609).** One bounded source-audit unit: define the named common-size acceptance set required by docs/L3-COVERAGE.md, then qualify one additional SKU/winding using manufacturer mounting geometry, kV and a torque operating point with voltage/current/duration/cooling qualifications. Cite inspected sources and revision-specific dimensions; separate geometry proof from delivery. If evidence is incomplete, record the exact missing fields and a bounded next decision; do not ship another envelope as full delivery or repeat identical searches. No solenoid restart without new mounting/travel evidence, no new API in this audit and no claim that two motors close plural coverage. [rec: steady-rain-3009] [rec: open-pine-9349] [rec: fair-snow-3443]

## Negative knowledge

- [scope: Start completion and metrics | confidence: high | evidence: rustic-spire-7084] Disable and delete have recorded runtime gates; the reserved committed-HEAD manifest check remains conditional in the work record. Do not redispatch deletion or count its two commits twice. Current FreeCAD M metric is 56/1637/1815, inherited remaining 3440 versus run-start 47/1804/1907 and 7277; older remaining counts included added files. Serialize staging before suites; use the installed script-file probe with an explicit pass marker and floating-point volume tolerance. [rec: southern-wood-6367]

- [scope: Start audit findings | confidence: high | evidence: sleepy-stone-2956] The audit is documentation only: no build, configure, install, stage, CTest or packaged gate ran; every disable gate is future. The staged payload prunes `Mod/Start` but still carries `lib/Start.so` (266,296 bytes), so payload absence proves nothing and the disable must confirm the library is gone. `MainCmd` depends on Test (`TestSources`), not Start; Test is not audited and not assumed removable. The 11 `FileUtilitiesTest` registrations leaving is the expected delta, not a regression.

- [scope: Help disable and delete | confidence: high | evidence: steady-dew-8037] Both Help commits landed with gates and records; do not re-run them or rewrite ADR-216 to ADR-218. The `-c` string form of the installed probe crashed; use the script-file form. Iterations 28 to 30 were lost because code and an ADR landed without a record node, the ADR cited a HELP-AUDIT section that did not exist, and the actor then stalled; every unit ends with its record node and cites only doc sections that exist. [rec: zesty-otter-9342]

- [scope: completed Measure sequence | confidence: high | evidence: small-tide-8341] Both disable and source deletion landed; do not redispatch. One shim file (22 lines, 1477 bytes) is not a whole-tree removal. Fresh packaged gates pass; inherited failures match baseline. Broader GUI-source and delta criteria remain open.

- [scope: post-deletion residual GUI | confidence: high | evidence: humble-shore-1680] Directory deletion and its residual audit are landed; all 26 postcommit packaged lifecycle/licensing tests passed. Required Assembly proxies and the Measure App view-provider identity must remain. Active Python install rules survived binary GUI deletion; source names and payload exclusion alone do not prove a tree removable. The existing-payload audit is not fresh proof of a future shim disable/delete.

- [scope: Phase 8 deletion | confidence: high | evidence: fair-cabin-5280] The earlier active Material/Gui metatype dependency and debug GUI-on path are resolved by sharp-pond-0087 and fair-cabin-5280; do not redispatch them. Retained Qt components and mixed Assembly publisher modules remain required. Existing-payload tests and ctests preferring .pixi binaries do not prove a newly deleted source boundary works; deletion needs fresh install/staging gates. The final rpm preset correction had focused coverage only, not a foreign-platform build.

- [scope: deferred solenoid delivery | confidence: high | evidence: open-pine-9349] The 412 proof is partial; older TAU mounting separation conflicts (20 versus 18.2 mm), and Ledex B7 lacks sourced engagement depth and maximum mechanical travel. Do not transplant slots or use the force-plot endpoint as a travel stop. No solenoid API shipped; these bounded searches do not disprove other variants. Resume only on new source evidence or a separately justified contract, not another identical partial model.

- [scope: GUI-attached walk and foreign revisions | confidence: high | evidence: still-badger-2386] The old real-engine overwrite claim was not reproduced: current stale failures omit the model_state needed by dormant replay. Replay and guard adoption are now removed; synthetic regression and real two-engine refusal/refresh recovery passed the full headless gate. This does not serialize simultaneous acceptance or rebuilds; sequential use remains required. Do not redispatch the completed defensive fix or claim general concurrent-write safety.

- [scope: any unit that changes the lifecycle walk | confidence: high | evidence: wild-marsh-9611] The critic rejected iteration 3 because `cli/cadex_cli/project_docs.py` did not change with the walk; the fix-forward pinned the scaffold's Training section to `docs/CLI.md` by a test. A walk change carries the doc and the scaffold in one commit, and a documentation unit names the scaffold sentence it relies on.
- [scope: a warm start under `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg; the dispatcher copies two files out and the `--init-from` policy is not one of them. Local second-mechanism qualification did not exercise this remote restriction.

- [scope: L2 and second-mechanism qualification | confidence: high | evidence: sage-peak-2689] Both former short dispatches landed. Slider training verified the pipeline, not height holding; do not treat unlike effort units as a design ranking.

- [scope: payload verification sequencing | confidence: high | evidence: stormy-quill-5350] Finish stage-engine before suites inspect the payload; concurrent staging exposed ccx before its normal prune and produced a transient failure.

## Provenance

- lone-wood-3732 — qualify current implementation and sequence lifecycle legs
- empty-wolf-3962 — fold pending short seed under charter constraints
- golden-mist-0498 — two units landed; GUI doc first, L2 boards and the second mechanism promoted from medium
- humble-bell-9017 — GUI documentation dispatch landed; retain L2 and second mechanism with corrected runtime limits

- nimble-glade-6200 — promote safety and one L3 family after verified L2 and second-mechanism work

- strong-grotto-8980 — both short units landed; promote two bounded L3 families and correct overwritten-risk evidence

- western-water-1442 — retain L12 delivery after sourced BLDC; preserve all remaining charter gaps

- sunny-lily-7639 — both L12 units landed; promote bounded solenoid work and preserve all broader gaps

- clever-falcon-0085 — promote joints after solenoid source follow-up; preserve deferred delivery and all charter gaps

- true-fox-1464 — fold verified joint delivery; audit residual L3 and advance reduction while preserving every charter gap

- silver-sage-7486 — fold completed audits; sequence Phase 8 prerequisites and conditional deletion, retaining all gaps

- deep-ash-7027 — fold landed prerequisites; dispatch deletion and conditional residual audit, preserving all charter gaps

- solar-cove-9793 — fold landed directory deletion and residual audit; dispatch the bounded Measure sequence and retain broader gaps

- quiet-canyon-3950 — fold landed Measure sequence; dispatch Help audit and conditional disable

- warm-anchor-2441 — fold landed Help audit and gate-verified disable; dispatch Help delete, Start audit and conditional Start disable

- still-quill-0059 — fold landed Help delete and Start audit; dispatch the Start disable, its conditional delete and the GSL follow-on

- fair-snow-3443 — fold Start disable/delete; finish GSL and conditionally promote two bounded L3 units
