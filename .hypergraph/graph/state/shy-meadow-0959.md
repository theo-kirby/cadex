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

**Recording, fixture-browser coverage and the borrowed-model rule exist; the fresh biped's real-model orbit/zoom check is still open.** Walk records preserve the rollout's accepted revision/digest, parameter values/specs and bounded document snapshots; the read-only reader labels runs current/historical/unknown against the accepted revision now [rec: wild-cove-4437]. Dashboard tests compare accepted/historical identities and component names, exercise real mouse orbit/zoom, and verify the repaired narrow-browser overflow [rec: rapid-crest-8826].

Borrowed-model rule (ADR-289, commit `7a63fa63`): a run that retained no rollout is drawn from the accepted attempt's tessellation only when its recorded revision AND digest both equal the accepted ones now, labelled as borrowed; a historical run, a blank identity or a moved digest shows nothing, with the reason. An HTTP test borrows the model for exactly one of four identities (current, historical, moved digest, blank). Judgement recorded there: a matching revision alone is not taken as the same geometry [rec: lively-gate-6535].

The `ot5-biped` project was first opened through the private-address dashboard with zero runs, no accepted identity, missing geometry and unavailable specs, plus readable documents and the next CLI action [rec: zesty-star-7710]. It now has an accepted revision (`23c6fe93f47a…`), 14 declared parameters, design-specs and decision notes (D9, `silent-river-6649`), so the fresh-biped evidence this criterion names is no longer blocked on creation; no orbit/zoom test against that real model has been run yet [rec: lucid-journey-6875].

Charter criterion: **D2. The browser shows the right model and specs** Interactive 3D orbit/zoom, component identity, declared parameters, design specs and project decisions come from the selected accepted revision; selecting an earlier run shows its model and specs, visibly identified as historical. Evidence: browser tests comparing displayed revision/run identities with recorded inputs and exercising model interaction on the fresh biped. Declared target `gap-d2-browser-shows-right-model` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330]. Retain `open` until the browser test runs against the fresh biped's accepted model.

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
