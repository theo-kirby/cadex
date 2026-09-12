---
node_id: da342c09-235c-544f-8e48-10263d3a053b
slug: jolly-loom-0622
title: D1. A live project dashboard is reachable
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D1 has its documented command and private-address browser smoke evidence (ADR-286).** The one-project inspection dashboard serves accepted and recorded historical model/spec inputs, document snapshots and permitted artifacts without an engine or project writes. Same-machine headless Chromium opened the synthetic fixture over Tailscale in 0.12 seconds and matched project name, accepted revision and location.host; the final browser/HTTP suite passed all 15 tests. Reconcile judgement: set `working`, because D1 explicitly requires this smoke and does not require a second device or a fresh biped. No second-device visit or persistent running server is claimed; the test stopped its server. The human-owned charter checkbox is unchanged [rec: rapid-crest-8826].

Charter criterion: **D1. A live project dashboard is reachable** One documented command serves one selected project over the machine's Tailscale/private-network address, and a browser can open it without a desktop session on the server. Evidence: a headless-browser smoke test against that address, with its command and result recorded; no claim of a second-device test unless one was run. Declared target `gap-d1-live-project-dashboard-reachable` [rec: lucky-comet-0031].

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d1-live-project-dashboard-reachable`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- rapid-crest-8826 — documented-command and same-machine private-address browser evidence closes D1 at fixture scope
