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

**The permitted-paths rule is pinned across the reader, model and mesh routes (ADR-317/318).** A `runs/<name>` symlink escaping the configured project is listed `unreadable` with `run directory escapes the project directory`; it contributes no policy digest, reads no telemetry, returns `available: false` on `/api/model/run/<name>` and serves no mesh bytes. Two reader regressions, an HTTP regression failing on the old server and a headless-browser regression cover this; the full CLI suite recorded **445 passed, 1 skipped**. The persistent service was restarted onto the patched server and verified over its private URL on `ot5-lark-copy85`; escaped-run fixtures remain isolated from that working project. Retain `working`, with same-machine private-address evidence only [rec: easy-field-3407].

**D1 has its documented command and private-address browser smoke evidence (ADR-286).** The one-project inspection dashboard serves accepted and recorded historical model/spec inputs, document snapshots and permitted artifacts without an engine or project writes. Same-machine headless Chromium opened the synthetic fixture over Tailscale in 0.12 seconds and matched project name, accepted revision and location.host; the final browser/HTTP suite passed all 15 tests. Reconcile judgement: set `working`, because D1 explicitly requires this smoke and does not require a second device or a fresh biped. No second-device visit or persistent running server is claimed; the test stopped its server. The human-owned charter checkbox is unchanged [rec: rapid-crest-8826].

Charter criterion: **D1. A live project dashboard is reachable** One documented command serves one selected project over the machine's Tailscale/private-network address, and a browser can open it without a desktop session on the server. Evidence: a headless-browser smoke test against that address, with its command and result recorded; no claim of a second-device test unless one was run. Declared target `gap-d1-live-project-dashboard-reachable` [rec: lucky-comet-0031].

**The owner ticked D1 in the charter on 2026-09-13 after run ot5 stopped at iteration 111; the criterion is closed for ot5 with its evidence unchanged, and ot6's charter (ADR-328) supersedes it [rec: patient-pond-3886].**

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d1-live-project-dashboard-reachable`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- rapid-crest-8826 — documented-command and same-machine private-address browser evidence closes D1 at fixture scope
- easy-field-3407 — ADR-317/318 containment, four regressions, full CLI gate and patched persistent-service verification
- patient-pond-3886 — the owner ticked D1 on 2026-09-13 after run ot5 stopped at iteration 111; evidence unchanged
