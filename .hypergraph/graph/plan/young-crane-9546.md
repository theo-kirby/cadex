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

1. **Audit remaining L3 coverage (mission 4; rising-banner-4325, brave-stone-9609).** Produce one reviewable coverage/evidence matrix against ROADMAP's L3 promise: common BLDC sizes and kV/torque data, N20, linear actuator, solenoid and joints. Identify delivered variants, sourced ratings and coupling limits, actual worker and packaged evidence, and exact missing contracts. SKF GE 6 C qualification/delivery is already verified; do not repeat it. Preserve solenoid delivery as an open deferred leg with the existing mounting/travel restart conditions; no repeated source search or weakened promise. Record the smallest remaining implementation candidates and their prerequisites for a later planner, distinguishing geometry from powered reachability, inertia and fit. Update narrow docs/ADR/ROADMAP facts where needed, never tick the whole L3 gap without evidence. This unit audits existing evidence; it does not ship another API or expand catalog scope. Run gates for any edited zone; at most one full build. [rec: morning-field-8202] [rec: open-pine-9349] [rec: clever-falcon-0085] [rec: true-fox-1464]
2. **Audit the Phase 8 deletion boundary (mission 3; civic-sand-2641, round-glacier-2865, green-sea-3991).** After unit 1 lands or records a concrete blocker, produce one reproducible dependency and deletion-readiness audit covering src/Gui, src/Mod/*/Gui, tests/src/Gui, setup_qt_test and their build/install references. Cite the actual disable commit and distinguish still-used headless modules from removable GUI trees; verify the exploded-view publisher dependency described by ROADMAP rather than deleting by filename. Identify the smallest coherent deletion boundary, remaining disable prerequisites and exact validation commands, including debug configure, release build, both cadex ctests and baseline comparison, and packaged gates if payload/protocol changes follow. Capture the run-start revision and inherited-manifest counts/diff metric now, with an honest current comparison; deletion volume alone is not measured fork-delta reduction. Deliver an audit record and necessary docs, no source deletion in this unit. The next planner sizes delete or prerequisite-disable work from the evidence; at most one full build and the edited zone's gates. [rec: empty-wolf-3962] [rec: lone-wood-3732] [rec: true-fox-1464]

## Negative knowledge

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
