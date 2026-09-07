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

1. **Teach the authoring contract that the policy strings are inline literals (mission 2; crisp-reef-5607).** The first walk run stopped at exit 3 because the design turn declared `weights` and `sha256` as module constants and `walk.py:declare_policy` rewrites inline string literals only; the `describe_api` prompt in `cli/cadex_cli/agent.py` teaches the `policy_on` switch and never mentions the literals [rec: misty-rain-9048]. The unit: one paragraph in that prompt saying `assembly.policy(task, weights="…", sha256="…")` must carry both strings inline, and a test that pins the paragraph and shows `declare_policy` accepting a script written the way the prompt now teaches. `docs/CLI.md`'s walk section already names this refusal count (commit `64b92b29`); if the wording drifts, fix it in the same commit. Zone gate: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`. Not authorized: widening `declare_policy` to resolve module constants (the walk must not guess at a script it did not write), a `walk.py` change, a scaffold change, running the walk again. [rec: glad-snow-3838] [rec: misty-rain-9048]
2. **Carry the design leg's reason into the walk's refusal (mission 2; crisp-reef-5607).** Inside `cadex walk --prompt` the design turn once ended in 3.76 s after one `describe_api` call with "the turn finished without the engine accepting a script" and nothing else; the same argv run directly succeeded in 214 s [rec: misty-rain-9048]. The refusal at `cli/cadex_cli/__main__.py` (the `accepted is None` branch) drops whatever the child agent said and whatever refused the script. The unit: the envelope's `error` carries the child's closing text and the last engine refusal when there is one, so a record or a later retry policy can name the cause; a test with a stubbed turn asserts the reason reaches the envelope. This is a walk-adjacent change: if `docs/CLI.md` describes the design leg's failure, update it and the scaffold's sentence it relies on in the same commit [rec: wild-marsh-9611]. Not authorized: an automatic retry, any change to the leg order, any `OP_ARG_SPECS` change. [rec: glad-snow-3838]
3. **Re-run the walk from `--prompt` on a fresh project and say whether the criterion can be ticked (mission 2; crisp-reef-5607).** Only after ranks 1 and 2 land with their records. Same discipline as the first run: fresh project under `build/lifecycle/`, the guard harness (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs), `--iterations 1 --envs 4 --seed 0`, headless only [rec: misty-rain-9048]. The record carries the command, the exit codes per leg, wall, peak RSS and `total_reward`, and states plainly whether ideation → design → … → review completed with no human step. A clean run is the evidence that closes `crisp-reef-5607`; a failed run names the next unit and that unit is what short takes next. If the design leg fails again, the record must now carry the reason rank 2 exposes. Not authorized: `pixi run app`, any GUI launch, remote training, fixing a leg in the same iteration. [rec: glad-snow-3838]

The two headless-review units that led this rung before nt3's first walk run (assembly inventory with catalog ids; the clearance and intersection check) are not withdrawn: they stand at medium ranks 1 and 2 with their full specifications and return here the moment the walk from a prompt is closed or blocked [rec: glad-snow-3838] [rec: flat-river-8853].

Operator re-plan before nt3 (2026-09-07) [rec: modest-summit-8554]: the planetary gearbox unit that led this rung is withdrawn. Its criterion is parked under `## Later criteria` and the planner may not target it. nt2 ran 68 iterations without running the walk once; the walk leads until it is closed.

## Negative knowledge

- [scope: completed updater writer pair | confidence: high | evidence: autumn-arrow-3125] Disable 95c1286d and delete 25445f70 landed separately with 2034 engine passes, one release build each, 162 baseline-only CTest failures and the retained App/Base translation probe. Surviving FreeCAD M totals are 56/1635/1881 versus the nt2 start 47/1804/1907; zero whole-file saving; Blender unchanged 44/1046/129. Do not redispatch; the updater's remaining commands, App/Base resources and Qt consumers stay. Direct external helper imports ceased to work. [rec: green-stone-3882] [rec: autumn-arrow-3125]

- [scope: stopped accessory delivery | confidence: high | evidence: steady-reef-0162] Neither category qualified. Horn geometry is measured, but exact mating and redistribution are unresolved; DS archive is inaccessible; cable lead has no manufacturer STEP. Raw Part.read is not the assumed script-owned route. No new candidate, approximation or importer is dispatched; both charter categories remain open. [rec: steady-reef-0162] [rec: noble-clover-4083]

- [scope: sole qualified updater boundary | confidence: high | evidence: cold-clover-8123] Audit and disposition have landed: only updateTranslatorCpp, its two dispatch sites and exclusive PySide import qualify. App/Base each retain 39 TS files and live Qt consumers; upload discovers sources independently. External use is unknown. Separate disable/delete evidence is required; no whole-updater deletion, resource/Qt removal, location cleanup or live network execution follows. Planning claims no implementation or delta saving. [rec: eager-garden-8009] [rec: cold-clover-8123] [rec: damp-sand-1115]

- [scope: completed Test Tk pair | confidence: high | evidence: silver-lodge-1952] Separate copy/install disable and 399-line source deletion landed, retaining all 37 other Test files. Fresh engine 2023 passed/52 skipped, packaged 26 passed, GUI-denied text 12 passed and Cadex CTests 4/4; inherited failures remain 162 with no new baseline names, full inventory unchanged. No stale runner source/bytecode remains in the four audited roots. Do not redispatch; whole-Test remains unqualified. FreeCAD current M totals 56/1634/1820, inherited remaining 3433. Local stage is not portable-release proof. [rec: simple-oak-4775] [rec: silver-lodge-1952]

- [scope: exhausted fifth-servo qualification | confidence: high | evidence: hidden-ridge-7342] HS-311 and HS-422 both fail unchanged ServoPart mounting-mouth compatibility; output-stack evidence is incomplete and HS-422 dimension labels conflict. No independent proof or delivery occurred. Stop the conditional proof/delivery, third-candidate search and recipe refactor until new evidence and an explicit later bet. Four servos and seven inclusively counted powered identities remain, not full breadth or L3 coverage. [rec: hidden-ridge-7342]

- [scope: qualified Test Tk boundary | confidence: high | evidence: humble-tide-6752] Earlier 'Test unaudited' observations are historical: only standalone unittestgui.py is now qualified, at one Test_SRCS copy/install row. Retain TestSources, MainCmd's dependency, Init.py registrations, data, TestGui/QtUnitGui and all other files. Audit native text tests passed 12 and existing-stage baseline passed 26, without fresh build/removal proof. Test being pruned from the payload alone proves nothing about build/install consumers. [rec: humble-tide-6752]

- [scope: completed render visibility fix | confidence: high | evidence: civic-moss-7263] Actual hydration/EEVEE regression fails on old source and passes after independent source/edge render ownership; camera source/ordinary/posed bands changed from 1024/1024/1024 to 0/1024/1024, and the full headless gate passed. Do not redispatch the audit/fix. Tests explicitly reload changed source; installed startup code was not refreshed. Legacy viewport restoration and manual render hiding during existing ownership remain limited; general headless review/video is still open. [rec: sunny-canyon-1138] [rec: civic-moss-7263]

- [scope: completed surviving-diff audit and reduction | confidence: high | evidence: proud-moon-9023] The finite 56-file audit qualified only the Preferences wrapper, now removed with source/staged probes, 2023 engine passes/52 skips, 26 fresh packaged passes and zero new inherited CTest failures (162 baseline names remain). FreeCAD is 56/1634/1819 surviving M files/inserted/deleted and 3434 inherited remaining; broader reduction remains open. No repeated audit, guard cleanup, formatter exception or Windows launcher work without new qualifying evidence and a later bet. [rec: proud-branch-1079] [rec: proud-moon-9023]

- [scope: completed Material and Main subsets | confidence: high | evidence: chilly-summit-3112] Material's three scripts and Main's freecad.rc.cmake are deleted after separate disables and fresh verification; no repeat audit, deletion or ordering handoff. Both units report engine 2023 passed/52 skipped, packaged 26 passed, Material App 15/C++ 35 passed and 162 inherited baseline failures with no additions. Retired Main debug autogen metadata was quarantined. Preserve shared Windows launcher arms pending behavior validation and a later bet; preserve Material App/tests/resources including TestMaterialDocument, retained Qt and required Assembly proxies. Debug configure and static Windows resource checks do not prove Windows behavior; the local stage is not relocatable-distribution proof. [rec: icy-tree-0009] [rec: chilly-summit-3112]

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

- placid-chart-1292 — fold verified Material audit/disable; dispatch exact deletion and bounded Main audit, preserving every charter gap

- amber-tower-7307 — resolve reconciled dispatch ordering; resume Material deletion and isolate audited Main template deletion, preserving Windows and all broader obligations

- easy-sea-7738 — fold both completed deletions; bound surviving-diff audit and conditional reduction, retaining every charter gap

- tidy-sea-8308 — fold completed audit/reduction, promote existing visibility defect and preserve all charter obligations

- rough-gate-7949 — fold completed visibility work; promote one fifth-servo sequence and preserve every broader obligation

- twilight-wolf-7995 — fold failed servo qualification and qualified Test Tk boundary; preserve all charter gaps

- narrow-pebble-8020 — fold completed Tk pair and current metrics; promote existing manufacturer STEP gap without retiring charter obligations

- noble-clover-4083 — fold pending offline updater audit and stop conditional accessory delivery
- hollow-reef-8734 — reconcile exhausted accessory sequence and audit-only updater direction; preserve all charter gaps

- damp-sand-1115 — fold completed updater audit/disposition; dispatch only separate disable and conditional delete, retaining all charter gaps

- placid-delta-6677 — fold the landed updater pair; dispatch three sequential gear units toward the compound-mechanisms criterion

- flat-river-8853 — fold the landed gear and rack-and-pinion units; dispatch the planetary unconditionally and promote the assembly inventory and the conditional clearance op from medium

- glad-snow-3838 — fold the first walk run: the two named legs and the re-run lead short; inventory and clearance step down to medium
