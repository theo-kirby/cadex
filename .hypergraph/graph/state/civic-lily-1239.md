---
node_id: 0aa1d364-4c43-5079-b21f-0c7dda4871cc
slug: civic-lily-1239
title: D9. Everything ot5 proved still holds
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: open

## Current

**D9 has current-tree regression evidence; final assessment remains open after unfinished D7/D8 work.** Engine: 2,114 passed / 53 skipped; CLI: 560 passed / 1 skipped. The persistent Finch final page passed at 1400×900 and 400×850 with real solids, zero horizontal overflow, advancing playback and downloads matching the retained video digest. Receipts are `docs/probes/ot6/regression/README.md` and `verification.json` [rec: copper-haven-4303].

Charter criterion: **D9. Everything ot5 proved still holds.** The review server and record suites, live polling within five seconds, playback and download, restart during training, copy isolation, failed-run states and headless operation all pass after the redesign, the look change and the model changes. Evidence: the CLI suite green, the engine suite green, and the operator URL serving the active project with the current run selected. The human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

- [scope: D9 regression verification in copper-haven-4303 | confidence: high | evidence: copper-haven-4303] Skips are not exercised coverage. The private-address fixture skipped, but an independent browser probe exercised the persistent private address. Lifecycle fixtures are not new GPU training. Reconcile judgement: keep `open`; these passing checks do not complete the unfinished mechanism lifecycles.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d9-everything-ot5-proved-still`
- copper-haven-4303 — full engine and CLI suites green, live Finch playback and digest-matched downloads at both widths; final assessment remains pending
