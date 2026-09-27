---
node_id: 9eadc90e-e6a8-5d70-9e21-2c3dd487812d
slug: true-tower-9405
title: A1. Cadex has a written design language and a frozen way to judge it
created_at: '2026-09-27T15:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **A1. Cadex has a written design language and a frozen way to judge it.** - `docs/DESIGN-LANGUAGE.md` states Cadex's own language for small printed servo robots: form, materials and palette, joints, face, proportion, printability and presentation. Each rule names the core references it comes from by filename only. - `docs/probes/ot10/README.md` freezes a scoring rubric of 5–8 traits, each scored 0–3 with written anchors. - It also freezes the measurable proxies from A3 and a numeric bar for A5, which must be set before any A5 probe runs. - It freezes the judging procedure: a fresh model call that sees the rubric, the reference images and the candidate renders, and nothing else. - hex3's accepted design is scored on it as the baseline. [rec: damp-dusk-8045]

Declared target: `gap-a1-cadex-has-written-design`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: damp-dusk-8045].

## Negative knowledge

None yet.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
