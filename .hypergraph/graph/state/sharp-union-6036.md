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

**Immutable training snapshots now survive accepted revisions; the real design-edit/retraining comparison remains open.** ADR-291 retains assembled model placements, checked mesh bytes, parameter specs and project documents before training, preserves the original documents/specs on subsequent status writes and refuses a changed accepted identity before dispatch. Browser regression changes accepted design and decisions, deletes old staging and confirms the old run still shows its own model, values and documents [rec: quiet-arbor-0259].

Probe3 adds a real immutable eight-component training snapshot and preserves earlier run records byte-for-byte across policy-playback revisions, with historical model identity, curves and playable videos browser-verified. It exercises the retention helper directly rather than the `cadex walk` orchestration. Complete project copies must include the entire run directory and ignored policies, traces and videos; Git alone is insufficient [rec: light-brook-2640].

Keep `open`: accepting checkpoint/final playback is not a physical design edit followed by retraining. The original probe1 null-identity record and probe2 missing historical inputs remain unreconstructed [rec: quiet-arbor-0259] [rec: light-brook-2640].

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
