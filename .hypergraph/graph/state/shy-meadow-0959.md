---
node_id: 67e36206-82b2-5afd-89ed-1201a5a5d249
slug: shy-meadow-0959
title: D2. The browser shows the right model and specs
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Two live-review defects found on the persistent Wren dashboard are fixed with browser regressions that failed on the old source.** ADR-306: an open spec/decision document was hidden by every live poll; loaded text now persists across polls, explicit link-click refresh is labelled, automatic current-following is suspended while reading, text clears on view/revision change, and a request sequence rejects superseded responses. Regressions cover accepted/historical reading, arrival of a newer current run during reading, and a delayed old response after switching documents [rec: calm-grove-2647]. ADR-307: the accepted view updated revision/parameter labels while retaining old geometry; polling now compares selected view, revision and digest and reloads the model on change, including first acceptance into an already-open empty view. Regressions check a new 40 mm cube's 45 mm world-X bound after placement, camera preservation on an unchanged poll, and the historical run's own revision. Acceptance-transition evidence is fixture-based; persistent Wren checks are read-only [rec: violet-wave-6524].

**Wren's repaired accepted display passes private-address browser review:** eight solids, twelve declared parameter defaults, accepted identity, pointer orbit, wheel zoom and empty-run polling, following a public rebuild that restored tessellation at unchanged accepted identity; preservation through in-place engine restore is tracked as the D6 gap [rec: mild-river-8224].

**Real 70/90/100/55 mm Reed designs pass browser model/spec identity and orbit/zoom checks, sweeps retain geometry before training, and byte-identical parts each keep their mesh.** ADR-291 freezes assembled placements, run-local mesh bytes, parameter specs and project documents, and refuses dispatch on changed accepted identity [rec: quiet-arbor-0259]. ADR-293 fixes ordinary `walk --set` sweeps, which had lost accepted tessellation for foot90's training snapshot, by requesting standard tessellation inside the parameter acceptance transaction, with a real-engine browser regression [rec: candid-forest-9800] [rec: forest-ledge-2219]. ADR-302 fixes byte-identical BREP outputs (a mirrored limb pair) keeping only one side's mesh; each output now retains its own accepted tessellation, verified after a service restart. Frozen training views of shin55, copy100 and probe3 keep their partial meshes as recorded, by the no-rebuild constraint, and say so [rec: fair-crow-5108].

Status stays `working`: real-biped review and product-path regressions pass, but historical snapshots are not backfilled and remain labelled [rec: forest-ledge-2219] [rec: fair-crow-5108].

Charter criterion: **D2. The browser shows the right model and specs** Interactive 3D orbit/zoom, component identity, declared parameters, design specs and project decisions come from the selected accepted revision; selecting an earlier run shows its model and specs, visibly identified as historical. Evidence: browser tests comparing displayed revision/run identities with recorded inputs and exercising model interaction on the fresh biped. Declared target `gap-d2-browser-shows-right-model` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d2-browser-shows-right-model`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- wild-cove-4437 — run recording and identity-aware read-only reader
- rapid-crest-8826 — fixture identity and model-interaction browser verification; narrow-browser repair
- zesty-star-7710 — actual unaccepted-project browser verification after creation refusal
- lucid-journey-6875 — the fresh biped now has an accepted revision, parameters and notes
- lively-gate-6535 — ADR-289 borrowed-model rule and its four-identity HTTP test
- merry-star-6951 — real probe2 missing-model observation
- misty-trail-1655 — ADR-290 retained training parts and real historical parts/assembled-checkpoint interaction, with pose/history limits
- quiet-arbor-0259 — ADR-291 immutable assembled training views and browser design-change regression
- light-brook-2640 — real probe3 live/historical assembled-model interaction and identity checks
- candid-forest-9800 — real physical-design browser comparison and discovery of missing swept training tessellation
- forest-ledge-2219 — ADR-293 closes parameter-sweep retention defect with real-engine browser regression; historical gap remains labelled
- fair-crow-5108 — ADR-302: byte-identical outputs each keep their accepted tessellation; earlier frozen views stay as recorded
- mild-river-8224 — Wren accepted-view identity, defaults and browser interaction receipt; restore limitation disclosed
- calm-grove-2647 — ADR-306: documents stay open across polls; regressions for view change, newer attempt and superseded response
- violet-wave-6524 — ADR-307: geometry reloads on revision/digest change, including first acceptance; bounds and camera regressions
