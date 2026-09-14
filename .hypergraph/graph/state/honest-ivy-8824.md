---
node_id: 02de9e75-f5fb-5ea7-9215-3870abbd7be0
slug: honest-ivy-8824
title: F8. A smoke rollout is one command
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

Charter criterion: **F8. A smoke rollout is one command.** A short bounded simulation of an accepted design, zero-action or holding its initial pose for a declared duration, passes when state stays finite, no component pair interpenetrates beyond tolerance over the trace, and the design rests on the environment floor or holds its grounded base. Evidence: CLI tests with a passing and a failing fixture, and the receipts F5–F7 cite. Declared target `gap-f8-smoke-rollout-one-command`; a record may say "ticks F8" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The nearest existing behaviour: Finch's ungrounded re-acceptance (ADR-335) was checked by hand in stock MuJoCo — held standing 2 s, a shove made it fall onto and never through the environment floor (`dusty-otter-7562`). Every check ships with a fixture whose right answer is known in advance and a test that fails on the old code; each rollout is bounded to five minutes. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f8-smoke-rollout-one-command`
