---
node_id: 67e36206-82b2-5afd-89ed-1201a5a5d249
slug: shy-meadow-0959
title: D2. The browser shows the right model and specs
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**Real fresh-biped orbit/zoom now passes for retained training parts and assembled checkpoint playback; complete historical model/spec retention remains open.** Probe2 initially displayed the correct revision but no model, causing its interaction check to time out [rec: merry-star-6951]. ADR-290 exposes run-local STL parts beside recorded `model_xml` when no rollout trace was recorded, with revision/digest and explicit labels that parts are at identity without recorded assembly placements. Missing/refused exports remain unavailable; symlinked STLs are refused, and a missing recorded rollout does not fall through to another model [rec: misty-trail-1655].

The real private-address browser check selected historical probe2 and compared revision/digest with its original export, exercised orbit/zoom on eight retained parts and checked served bytes and unchanged input hashes. It then independently exercised the assembled biped at checkpoint20's own revision using its retained meshes, mapping and first frame. Both checks passed without rebuilding geometry or writing telemetry; fixture browser regression and full CLI/engine suites passed. This was same-machine private-address testing, not a second-device test [rec: misty-trail-1655].

Walk records retain rollout identity, parameter specs and bounded document snapshots; current/historical/unknown labels compare recorded identity with the accepted revision [rec: wild-cove-4437]. The borrowed-current-model path requires both revision and digest to match and labels its source [rec: lively-gate-6535]. Fixture tests cover identities, component names and interaction [rec: rapid-crest-8826].

Keep `open`: probe2's assembled training placement map and overwritten document snapshot were not recovered. Retained assembled training poses and complete spec/history evidence remain absent. Checkpoint20's pose is not evidence of probe2's training pose [rec: misty-trail-1655].

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
