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

1. **Delete Help at the audited boundary (mission 3; windy-pebble-4630, round-glacier-2865, green-sea-3991).** The disable is landed and gate-verified, so land the separate delete commit exactly as `docs/HELP-AUDIT.md` §"Separate disable, then delete" specifies: remove `src/Mod/Help/`, its parent gate in `src/Mod/CMakeLists.txt`, the forced-OFF option and report line, the Help row in `src/Tools/updatecrowdin.py`, and the two developer-configuration path entries. Reaudit consumers first with the audit's search basis; do not widen to Start, Test, Measure App, required Assembly publishers or retained Qt. Regenerate both configurations, quarantine stale outputs, run at most one release build, install and finish staging, then the full engine suite, both Cadex ctests, serial inherited CTest diffed by failure name against the baseline, the installed import probe, and the packaged lifecycle/licensing gate. Recompute the manifest-scoped metrics and update notices for each surviving changed inherited file; whole deleted files are not M entries. Add the ADR line, ledger and ROADMAP tick, and land the record node with real impacts in the same unit. This counts as one whole-tree removal, not two. [rec: silver-beacon-0723] [rec: zesty-otter-9342] [rec: warm-anchor-2441]
2. **Audit Start as the second whole-tree candidate (mission 3; windy-pebble-4630, round-glacier-2865).** Same shape as the Help audit and documentation-only: exact tracked importers of Start, its App target and what depends on it, `BUILD_START` defaults and explicit overrides, copy/install/resource consumers, generated consumers, CTest registrations and payload obligations. Start builds an App target and installs Init.py while the payload prunes it; payload absence proves nothing. Identify the smallest durable disable that normalizes existing ON caches, the later delete boundary and the required verification. Record whether Start qualifies and why; if it does not, name the concrete blocker and leave item 3 undispatched. Do not assume Test is removable: MainCmd depends on TestSources and Test installs App tests. Label any existing-payload check as existing-payload evidence. [rec: humble-shore-1680] [rec: silver-beacon-0723] [rec: warm-anchor-2441]
3. **Disable Start only after the audit qualifies it (mission 3; windy-pebble-4630, round-glacier-2865).** One small disable commit at the audited boundary, retaining source for a separate deletion, with ADR, ledger, narrow ROADMAP facts and manifest/notices. Run the gates in the same unit before any doc claims them: both configurations including explicit ON over the existing caches, at most one release build, install and stage, full engine suite, both Cadex ctests, serial inherited CTest with failure-name and registration comparison, installed probe of the retained modules, and the fresh packaged gate. Record node in the same unit. If the audit or disable fails, record the boundary and re-plan; no deletion in this unit. [rec: quiet-canyon-3950] [rec: zesty-otter-9342] [rec: warm-anchor-2441]

## Negative knowledge

- [scope: Help disable and its record | confidence: high | evidence: zesty-otter-9342] The disable commits `a04ca822` and `504b46bc` are unchanged and their gates ran and are recorded; the stale Help copies, install and bytecode were already absent. Do not re-disable, re-run the disable gates or rewrite ADR-217. Iterations 28 to 30 were lost because code and an ADR landed without a record node, the ADR cited a HELP-AUDIT section that did not exist, and the actor then stalled; every unit ends with its record node and cites only doc sections that exist.

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
