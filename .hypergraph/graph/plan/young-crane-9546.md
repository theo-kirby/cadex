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

1. **Qualify one sourced mechanical joint (mission 4; rising-banner-4325, brave-stone-9609).** Choose one identifiable, common robot-relevant joint hardware variant from manufacturer drawings or traceable original documentation. State the variant, source revision/URLs/download hashes, mounting and mating datums, supported motion geometry and qualified ratings; distinguish nominal geometry from tolerance, load and fit guarantees. Prove a bounded exterior with the existing headless OCCT engine, checking actual mating interfaces, material/void, canonical and nontrivial placed geometry, and any supported articulation limits. Use existing catalog/recipe precedents; this is hardware geometry, not a new assembly solver or automatic dynamics. Deliver one reproducible source/geometry audit, no public API required. If essential interfaces cannot be sourced, record exactly what is missing and replan rather than guessing or repeating the solenoid search. At most one full build and the gates for any edited zone. [rec: open-pine-9349] [rec: clever-falcon-0085]
2. **Ship the proven joint catalog variant (mission 4; rising-banner-4325, brave-stone-9609).** Conditional on unit 1 proving a supportable contract, expose that same bounded hardware value over CadexCatalog and LibraryPart with existing recipe primitives. Preserve sourced datums, qualifications and approximation metadata; refuse unsupported variants and invalid geometric parameters. Pin canonical/placed real-worker interfaces, discovery/API goldens and cadexd publication; update provenance, docs, ADR and a narrow ROADMAP implementation checkbox. Run the full engine suite, at most one full build, completed staging, then packaged lifecycle/library gates sequentially so installed workers see the API. Report skips and incomplete gates exactly. If qualification already delivered and verified the API, replan instead of duplicating it. Solenoid delivery and full L3 remain open; no automatic dynamics, physical inertia or installation-fit guarantee follows from an exterior model. [rec: frosty-snow-9642] [rec: open-pine-9349] [rec: clever-falcon-0085]

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
