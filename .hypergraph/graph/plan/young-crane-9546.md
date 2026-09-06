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

1. **L3 BLDC family (mission 4; rising-banner-4325, brave-stone-9609).** Next dispatch: add one manufacturer-specific BLDC motor family over CadexCatalog using the existing LibraryPart shape. Read and cite manufacturer drawings/specifications for mounting, shaft, envelope and kV; attach torque/current/voltage ratings only with their stated operating conditions. Distinguish derived estimates from measured ratings; do not infer continuous torque or physical inertia from an envelope. Select a product with adequate primary-source evidence, record missing data honestly, and avoid an actuator helper or new simulation abstraction. Include provenance, real-kernel placement/interface tests, applicable API goldens/docs, ADR and a narrow ROADMAP subitem. Run the engine suite, at most one full build, complete staging before packaged lifecycle/library tests. Leave the whole L3 criterion open and record any unfinished gate precisely. [rec: idle-dawn-5426] [rec: strong-grotto-8980]
2. **L3 linear-actuator family (mission 4; rising-banner-4325, brave-stone-9609).** After unit 1 lands or is evidenced blocked, add one manufacturer-specific linear-actuator family through the same catalog/lib-value contract. Source body, rod, mounting centres, stroke and rated force/speed/voltage with operating conditions; explicitly constrain supported variants and geometric extension range. Pin retracted/extended mounting geometry and placement with real-kernel tests; geometry alone makes no load, collision or dynamics guarantee. Include provenance, relevant docs/goldens, ADR and a narrow ROADMAP subitem. Run the engine suite, at most one full build, then staging followed by packaged lifecycle/library gates. No remote execution or new training layer. Retain unsourced interfaces or incomplete gates as named remaining legs, and keep solenoid, joints and compound gearing separate. [rec: idle-dawn-5426] [rec: strong-grotto-8980]

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
