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

1. **Disable the audited Measure GUI shim install (mission 3; round-glacier-2865).** Remove only MassPropertiesGui.py from Measure_Scripts, whose shared list feeds target/copy/install; keep the source for a later delete commit. Follow docs/PHASE8-AUDIT.md and ADR-215. Preserve the other four Measure scripts, Measure App class and view-provider identity string, required Assembly publication modules and retained Qt. Update ADR, ledger, narrow ROADMAP facts and inherited manifest/notices together. Verify debug/release configurations, at most one release build, full engine suite, both cadex ctests and inherited baseline names/inventory/skips/disabled cases. Quarantine stale copied/installed shim files, install and finish staging before fresh packaged lifecycle/licensing gates; assert the shim absent from generated consumers and payload while retained Measure/Assembly consumers remain available. Serial CTest discovery avoids the prior generated-metadata race. Report precommit HEAD-manifest limits and rerun the committed comparison; no old-payload proof or broader no-GUI-source claim. [rec: humble-shore-1680] [rec: terse-ridge-1619] [rec: solar-cove-9793]
2. **Delete the disabled Measure GUI shim (mission 3; round-glacier-2865).** Only after the preceding disable commit has the required passing evidence, delete MassPropertiesGui.py in a separate small commit. Preserve MassPropertiesObject.h and its view-provider identity, Measure App behavior and all mixed Assembly publishers; no whole Measure-tree deletion. Confirm the audited consumer closure still holds, update ADR/ledger/ROADMAP and manifest/notices as applicable, and follow the audit's verification recipe: both configurations, at most one release build, full engine suite and inherited gates with baseline comparison, fresh install then completed stage and packaged lifecycle/licensing checks, including stale-file and live-dependency inspection. Report deleted volume separately from import-relative manifest metrics against nt2 start 7dd3d045. This sequence does not close the two engine-tree-removals or broad fork-delta gaps. If disable exposes a blocker, leave this unit undispatched for the next planner to size the repair. [rec: humble-shore-1680] [rec: terse-ridge-1619] [rec: solar-cove-9793]

## Negative knowledge

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
