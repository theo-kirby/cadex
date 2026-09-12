---
node_id: 17878bbb-7dd9-5fc4-bdcd-f7d802e0c0a6
slug: sharp-union-6036
title: D5. Review history survives a design change
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**Run retention and fixture history checks exist; the real design-change lifecycle remains open.** Each walk retains revision/digest, parameter specs, task/training configuration, receipt figures, policy identity and review references in `runs/<name>/run.json`, with bounded project-document snapshots. Artifact resolution rejects escaping references and reports missing files; videos remain an empty slot [rec: wild-cove-4437]. Fixture browser tests preserve historical model/spec identities. Retain `open`: no fresh-project design edit and retraining history with retained curves, models and playable videos has been verified [rec: rapid-crest-8826].

Charter criterion: **D5. Review history survives a design change** Each run retains the model/script revision, specs, task/training configuration, metrics, policy identity and review/video references needed to interpret it; after a design edit and retraining, both runs remain selectable with their own curves, models and videos. Evidence: before/after identity and artifact checks, and browser assertions that old results have not silently switched to the new design. Declared target `gap-d5-review-history-survives-design` [rec: lucky-comet-0031].

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d5-review-history-survives-design`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- wild-cove-4437 — per-run retention contract and containment-checked references
- rapid-crest-8826 — fixture browser historical identity checks, with real retraining/video evidence outstanding
