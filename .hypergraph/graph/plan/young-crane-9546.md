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

1. **Preserve the headless metatype contract (mission 3; civic-sand-2641, round-glacier-2865).** Move the QtCore/Base/App metatype declarations from Gui/MetaTypes.h to the smallest retained App-level header, preserving attribution and a forwarding Gui header until deletion. Migrate the 12 Material and six retained test includes identified in docs/PHASE8-AUDIT.md; do not remove QtCore, QtConcurrent or LinguistTools. This is one conservative prerequisite commit, with precise manifest/notices, ADR and narrow ROADMAP/doc updates. Verify debug configure, one release build, retained Material tests, the engine suite, both cadex ctests and inherited failure-name comparison using the audit's commands; run fresh packaged gates if installation/payload changes. Record what actually ran and any new blocker. No directory deletion in this unit. [rec: wise-isle-1725] [rec: silver-sage-7486]
2. **Complete Phase 8 GUI disable (mission 3; civic-sand-2641, round-glacier-2865).** After unit 1 succeeds, make ordinary debug configuration headless and prevent explicit GUI-on requests from reaching targets scheduled for deletion, using the smallest consistent configuration rule. Keep GUI source present for this separate disable commit; preserve release/package behavior and retained Qt components. Cite historical d2c8bcc5 plus the new disable evidence, update the affected docs/ADR/ROADMAP and honest inherited manifest/notices, and verify ordinary debug plus the explicit GUI-on case, one release build, engine suite, both cadex ctests and inherited baseline comparison. Follow the audit's fresh packaging sequence if payload/install behavior changes. This is completion of the existing removal protocol, not a new engine design. [rec: wise-isle-1725] [rec: silver-sage-7486]
3. **Delete the verified Phase 8 directory boundary (mission 3; civic-sand-2641, round-glacier-2865, green-sea-3991).** Only after both prerequisite records demonstrate success, remove the 13 audited GUI directory trees and their residual build/test/doc registrations in one coherent delete commit, including the orphan InventorBuilder test and audited retired Main GUI-only targets/sources. Preserve headless App trees, command-line launchers and mixed Assembly publisher modules. Replace obsolete identity-test source-presence checks with absence checks while retaining engine preference coverage. Update ADR, narrow ROADMAP facts, ledger, manifest and notices together. Run the audit's debug configure, one release build, full engine suite, both cadex ctests and failure-name baseline comparison; install and finish staging before packaged lifecycle/licensing gates, checking for stale deleted files and live Ninja dependencies. Report both removed volume and the manifest-scoped delta against nt2 start 7dd3d045; do not claim all GUI-lineage source gone or the fork-delta gap closed from volume alone. If a prerequisite fails, this dispatch remains conditional and the next planner sizes the fix from evidence. [rec: wise-isle-1725] [rec: silver-sage-7486]

## Negative knowledge

- [scope: Phase 8 deletion | confidence: high | evidence: wise-isle-1725] BUILD_GUI=OFF in release does not cover debug, and Material actively consumes Gui/MetaTypes.h. Preserve the App/QtCore contract before deletion; retain mixed Assembly publisher modules. Existing-payload tests and ctests preferring .pixi binaries do not prove a newly deleted source boundary works.

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
