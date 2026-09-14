---
node_id: aea7b9a7-f0e2-5224-ae21-fe54d0a4ec03
slug: narrow-dune-9454
title: F6. The balancer is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**A tested bounded evidence collector is ready at `docs/probes/ot7/runner/` (ADR-354).** It validates frozen prompt hashes, permits one create and at most three ordered continuations, refuses restart and automatic unfrozen follow-ups, and retains per-turn measured static fit, raw swept coverage, inventory, transcript hashes and one final bounded smoke. Provider errors/timeouts stop prompting; missing evidence and unavailable sweeps remain explicit. CLI validation passed 693 tests/1 skipped. No design attempt ran, so this criterion remains open [rec: peaceful-hill-3013].

**Robin's create prompt is frozen** at `docs/probes/ot7/prompts/robin.create.prompt.txt` (sha256 `e20ee7ab…`), byte-identical to its ot6 prompt, with the same three ordered continuations. No design turn has run; F6 remains open [rec: silent-union-5108].

Charter criterion: **F6. The balancer is designed unassisted.** The same bar as F5 on Robin's ot6 create prompt (`docs/probes/ot6/robin/create.prompt.txt`). Declared target `gap-f6-balancer-designed-unassisted-same`; a record may say "ticks F6" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 comparison point is Robin (`ready-sand-2621`): the agent's candidate was accepted only after the actor edited its script twice (the reset-lift literal, then the D-bore replaced by an analytic prism after `part.offset` proved non-reproducible). Under this charter the actor never edits a design; when the agent cannot run, the refusal is recorded and the unit turns to tools, checks or tests. [rec: kind-dusk-1609]

Reconcile judgement: frozen prompts and collector fixtures establish readiness, but no unassisted design, fit or smoke result; retain `open` [rec: peaceful-hill-3013].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f6-balancer-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
