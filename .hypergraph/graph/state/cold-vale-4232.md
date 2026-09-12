---
node_id: 9220fe11-e411-5d55-a2a3-53e57c5dd269
slug: cold-vale-4232
title: D7. Save-As/copy produces an independent project
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

Charter criterion: **D7. Save-As/copy produces an independent project** A documented headless operation copies the project and its retained review artifacts, and another server can inspect the copy; changing/retraining the copy leaves the original unchanged, and the copy remains usable with the original unavailable. Evidence: isolation, artifact resolution and browser reopen tests on the copy. Declared target `gap-d7-save-as-copy-produces` [rec: lucky-comet-0031]. No evidence exists yet: the owner's redirect claims no implementation and no criterion completion [rec: dusty-peak-9330]. Flips to working only when the evidence the criterion names is recorded.

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d7-save-as-copy-produces`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
