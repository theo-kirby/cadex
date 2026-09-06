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

1. **Prove nominal L12 mounting geometry (mission 4; rising-banner-4325, brave-stone-9609).** Construct and measure the proposed L12-50-210-12-S geometry headlessly with the existing OCCT engine before exposing the family. Follow ADR-207: datasheet nominal mounting centres are 102 mm retracted and 152 mm extended; the older STEP is 0.5 mm longer, not a tolerance or a blanket surface correction. Exercise the supplied clevis, mounting-bore voids/material, extension endpoints and a nontrivial placement. Explicitly identify approximated housing transitions and omitted installation details. Record a reproducible construction/probe and its numbers; do not repeat the completed eight-file source audit or invent missing fit dimensions. This is a one-iteration geometry experiment, with no public API required; run the gates for any zone edited, at most one full build. If a required interface cannot be supported, name that precise remaining leg without declaring all L3 blocked. [rec: southern-moss-9142] [rec: western-water-1442]
2. **Ship the proven L12 catalog variant (mission 4; rising-banner-4325, brave-stone-9609).** After unit 1 resolves the geometry contract, expose the same L12-50-210-12-S through CadexCatalog and the existing LibraryPart contract. Reject extension outside [0, 50] and unsupported variants; distinguish geometric extension from S-switch reachability and retain force/speed/voltage/duty qualifications at their stated operating points. Add real-kernel canonical and placed interface tests, discovery/API goldens, provenance, docs, ADR and the narrow ROADMAP implementation checkbox. Run the full engine suite, at most one full build, completed staging and packaged lifecycle/library gates. Never overlap staging with either suite. Record incomplete gates precisely; geometry establishes no physical inertia, load or collision guarantee. If unit 1 already ships this implementation with all evidence, replan rather than duplicate it. Keep the whole L3 criterion open; no solenoid or joints promotion yet. [rec: southern-moss-9142] [rec: floral-stone-2866] [rec: western-water-1442]

## Negative knowledge

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
