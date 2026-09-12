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

**Run retention now includes identity from the first record; the real design-change lifecycle remains open.** Each walk retains revision/digest, parameter specs, task/training configuration, receipt figures, policy identity and review references in `runs/<name>/run.json`, with bounded project-document snapshots; artifact resolution rejects escaping references and reports missing files; videos remain an empty slot [rec: wild-cove-4437]. Fixture browser tests preserve historical model/spec identities [rec: rapid-crest-8826].

The real biped's first walk showed the retention gap: `runs/probe1/run.json` kept `identity_source: "not reached"` and null revision/digest after the train leg had reported both, so a failed run could not be tied to its revision on the dashboard [rec: lucid-journey-6875]. ADR-289 (commit `7a63fa63`) closes it in the CLI: a run is the run of a revision from its first record. `cadex walk` starts `run.json` from the manifest's accepted revision, digest and specs; every leg that reports an identity (design, sweep, train, collect, declare, rollout) replaces it with `<leg> leg envelope`; a design turn or sweep re-reads the manifest's specs and re-lands `running` before the train leg; a failed or pending record keeps the last identity learned; every write snapshots the project documents; `not reached` now means only that there was no manifest and no leg spoke. A historical run with no rollout shows no model, with the reason. Tests tell the manifest's and the train leg's identities apart by construction and show a design turn moving the identity before training; CLI suite 358 passed, 1 skipped. `probe1`'s pre-fix record is deliberately left as written, so on the real project it still reads `not reached` until the next walk lands [rec: lively-gate-6535].

Charter criterion: **D5. Review history survives a design change** Each run retains the model/script revision, specs, task/training configuration, metrics, policy identity and review/video references needed to interpret it; after a design edit and retraining, both runs remain selectable with their own curves, models and videos. Evidence: before/after identity and artifact checks, and browser assertions that old results have not silently switched to the new design. Declared target `gap-d5-review-history-survives-design` [rec: lucky-comet-0031]. Retain `open`: no fresh-project design edit and retraining with retained curves, models and playable videos has been verified; the one real run so far has no rollout or video.

## Negative knowledge

- [scope: `cadex walk` run records written before ADR-289 (commit 7a63fa63), including the real `runs/probe1` | confidence: high | evidence: lucid-journey-6875, lively-gate-6535] A run that failed before its rollout carries no revision or digest, and records are not rewritten after the fact.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d5-review-history-survives-design`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- wild-cove-4437 — per-run retention contract and containment-checked references
- rapid-crest-8826 — fixture browser historical identity checks, with real retraining/video evidence outstanding
- lucid-journey-6875 — the null-identity defect demonstrated on the real biped's failed first walk
- lively-gate-6535 — ADR-289: identity from the manifest at walk start, kept through failure, moved by design turns
