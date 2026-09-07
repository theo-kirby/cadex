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

1. **Audit Material's GUI registration cluster (mission 3; round-glacier-2865).** MeshPart's separate disable/delete landed; do not repeat them. Bound one documentation audit to Material/InitGui.py, MaterialEditor.py and TestMaterialsGui.py: trace headless/product imports, startup and test discovery, CMake copy/install paths and active build/install/stage copies. Determine the exact safe disable set and retained dependencies, including materialtests/TestMaterialDocument.py; GUI-looking names alone are insufficient. Preserve Material App, Init.py, importFCMat.py, App tests, materialtools, cards/model resources, retained Qt and required Assembly proxies. Record the dependency evidence, candidate boundary, stale-copy handling and gate commands in the audit/ADR/ROADMAP. No implementation or deletion in this unit; existing-payload tests are only a baseline. If no safe subset qualifies, record the blocker and replan rather than expanding into mixed helpers or Main. [rec: humble-shore-1680] [rec: light-peak-0510] [rec: shady-ivy-2659]
2. **Conditionally disable only the audited Material GUI registrations (mission 3; round-glacier-2865).** Proceed only on the preceding record's explicit safe subset and retained-consumer proof. Remove its active copy/install registrations in one separate disable commit, retain all source for later deletion and preserve the audit's App/resources/test boundary. Quarantine stale copies and inspect generated rules plus active debug/release/install/stage paths. Run at most one full release build, complete install and staging, then run the full engine suite, inherited CTest with failure-name comparison to its recorded baseline, fresh packaged lifecycle/licensing gates and retained Material App tests/probes. Never overlap staging with payload-reading tests. Record exact failures, skips and validation limits; keep manifest equality/notices and required ADR/ROADMAP updates honest, including committed-HEAD evidence. Incomplete or regressed gates block deletion. Replan after this pair: source deletion is a later separate unit, not authorized by an audit alone; BLDC searches remain stopped. [rec: fierce-journey-4610] [rec: light-peak-0510] [rec: mild-harvest-8460] [rec: shady-ivy-2659]

## Negative knowledge

- [scope: AT2814 qualification stop | confidence: high | evidence: mild-harvest-8460] The one alternative audit is complete and blocked on current definition, thermal conditions and rating/drawing revision linkage. No winding qualified; no geometry or delivery dispatch. Stop the motor-search sequence, retain set A and require new qualifying evidence plus an explicit replan before resuming; do not repeat RI50 or AT2814 searches. This does not prove qualifying evidence cannot exist.

- [scope: completed MeshPart and staging order | confidence: high | evidence: light-peak-0510] Separate install-disable and source-delete landed with 2023 engine passes, 26 fresh packaged passes and 162 inherited failures with no new baseline failures. Preserve App, Init.py, meshFromShape, library and export macros; do not repeat the removed initializer work. Whole-file deletion of 73 lines is not M-line savings or broad GUI closure. Staging concurrently exposed ccx before pruning; finish install/stage before payload-reading suites. The old audit's active initializer copies are historical, not current. [rec: fierce-journey-4610]

- [scope: RI50 and BLDC set A | confidence: high | evidence: shy-hill-8139] RI50 is parked: inspected BOM cells and STEP headers do not close thermal operating-point or rating/drawing revision gaps. DWG annotations and the installation video were not inspected; this is no proof that qualifying evidence cannot exist. No repeated identical searches, frameless-to-shafted recipe substitution, kV-derived usable torque or automatic proof/delivery. Set A requires qualified shafted 28xx, hollow frameless 50 and 80 windings; existing Skywalker lacks torque qualification and no alternative is prequalified. [rec: slender-harbor-9625]

- [scope: completed GSL and N20 units | confidence: high | evidence: late-pond-3758] Start's committed-HEAD manifest check passed, completing Help/Start's two-removal evidence; GSL checkout cleanup also landed. No repeat deletion, GSL audit or reserved check. Surviving-file modification sets are unchanged by GSL. N20 independent surfaces and 160 probes now pass; full engine 2023 passed/52 skipped, staged lifecycle/library 91 passed. Assumed bore depth and flat transition remain unqualified for fit. The local payload has 144 relocation violations and is not shippable; complete staging before suites. [rec: windy-lily-2895]

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

- frosty-dawn-2061 — fold completed GSL/N20; dispatch BLDC audit and evidence-gated proof/delivery

- vast-oak-7458 — fold set A and parked RI50; bound shafted qualification and preserve every charter gap

- sharp-oak-9030 — fold blocked AT2814 and audited MeshPart; promote separate disable/delete, retaining all charter gaps

- shady-ivy-2659 — fold completed MeshPart pair; bound Material audit/disable, correct metrics and preserve all gaps
