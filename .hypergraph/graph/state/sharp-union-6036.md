---
node_id: 17878bbb-7dd9-5fc4-bdcd-f7d802e0c0a6
slug: sharp-union-6036
title: D5. Review history survives a design change
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Review history survives the real 70→90 mm foot edit and GPU retraining.** Both designs remain browser-selectable with distinct model/spec identities, 240-point reward/loss/episode-length curves and playable/downloadable videos. All 250 pre-existing run/asset files remain byte-identical. This supplies the physical design-change comparison previously missing, so status is `working`; actor-authored revision is a separate remaining D9 limitation [rec: candid-forest-9800].

ADR-291 retains assembled placements, checked mesh bytes, parameter specs and project documents before training and preserves them through later status writes [rec: quiet-arbor-0259]. ADR-293's real-engine browser regression additionally preserves the prior swept run's mesh bytes, assembled components, revision/digest and specs after a later physical parameter edit while current geometry changes [rec: forest-ledge-2219].

Historical gaps remain explicit: foot90's original unavailable training snapshot is not rewritten from its later working rollout geometry, and the fix is verified on a real-engine fixture rather than another biped GPU run [rec: candid-forest-9800] [rec: forest-ledge-2219]. Complete project copies must include run directories and ignored policies, traces and videos; Git alone is insufficient [rec: light-brook-2640].

Charter criterion: **D5. Review history survives a design change** Each run retains the model/script revision, specs, task/training configuration, metrics, policy identity and review/video references needed to interpret it; after a design edit and retraining, both runs remain selectable with their own curves, models and videos. Evidence: before/after identity and artifact checks, and browser assertions that old results have not silently switched to the new design. Declared target `gap-d5-review-history-survives-design` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: `cadex walk` run records written before ADR-289 (commit 7a63fa63), including the real `runs/probe1` | confidence: high | evidence: lucid-journey-6875, lively-gate-6535] A run that failed before its rollout carries no revision or digest, and records are not rewritten after the fact.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d5-review-history-survives-design`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- wild-cove-4437 — per-run retention contract and containment-checked references
- rapid-crest-8826 — fixture browser historical identity checks, with real retraining/video evidence outstanding
- lucid-journey-6875 — the null-identity defect demonstrated on the real biped's failed first walk
- lively-gate-6535 — ADR-289: identity from the manifest at walk start, kept through failure, moved by design turns
- quiet-arbor-0259 — training-start specs/documents stay frozen and dispatch identity is guarded
- light-brook-2640 — real retained snapshot, preserved prior records and policy-playback history; redesign still outstanding
- candid-forest-9800 — real physical edit/retraining retains both designs, curves and videos with all old run/assets unchanged
- forest-ledge-2219 — parameter-sweep history regression retains original assembly, meshes and specs without backfill
