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

**Real 70/90 mm Reed designs pass browser model/spec identity and orbit/zoom checks, and ordinary parameter sweeps now retain geometry before training.** ADR-291 freezes assembled placements, checked run-local mesh bytes, parameter specs and project documents; later status writes preserve them and changed accepted identity before dispatch is refused [rec: quiet-arbor-0259].

The foot90 experiment checks exact retained identities and design-spec content, downloads both physical foot meshes, exercises orbit/zoom, and visibly identifies the baseline as historical. It also exposed missing accepted tessellation in ordinary `walk --set`: foot90's training snapshot truthfully remains unavailable, while its final rollout model works [rec: candid-forest-9800].

ADR-293 fixes new sweeps by requesting standard tessellation without edges in the existing parameter acceptance transaction. A real-engine browser regression checks assembled geometry, revision/digest, parameter values/defaults, rendered pixels and orbit/zoom at trainer dispatch, then verifies historical identity and retained bytes after a later physical parameter change. Status is `working` from the combined real-biped review and product-path regression; the latter intercepts trainer dispatch and is not a new real-biped GPU run. No historical snapshot is backfilled [rec: forest-ledge-2219].

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
