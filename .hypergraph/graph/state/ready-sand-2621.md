---
node_id: cba79b00-c24d-5645-a748-33e794aa38d3
slug: ready-sand-2621
title: D7. A two-wheeled balancing robot goes through the lifecycle
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: open

## Current

**D7 remains open after Robin's first failed design attempt.** The product-agent turn in fresh external project `ot6-robin` exited 1: the candidate's reset penetrated the floor 1.31 mm beyond the reset pose, a repair targeted text absent from the still-accepted probe, and the provider usage limit ended the turn. Only `part/probe_motor` is accepted; there is no accepted balancer, certified inventory or fit check, or training. The prompt and digest-bearing failure receipt are under `docs/probes/ot6/robin/`. At experiment close the persistent dashboard still loaded Finch's `finch1-final`, 29 components and 95 212 triangles. Recovery remains product-agent resubmission of the retained failed candidate as a complete script, followed by inventory and fit before a dashboard handoff [rec: wise-brook-4842].

Charter criterion: **D7. A two-wheeled balancing robot goes through the lifecycle.** The product agent designs it from a prompt in a fresh project (MG90S or another catalog motor, catalog wheels or modelled printable wheels, a body that mounts the board and battery volume), it meets D5's inventory and fit rules, trains once (bounded), and its videos and measurements are on the dashboard. Declared target `gap-d7-two-wheeled-balancing-robot`; the full lifecycle remains unfulfilled, and the human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

- [scope: Robin first design attempt | confidence: high | evidence: wise-brook-4842] The reset-floor refusal does not establish an engine defect. The accepted catalog probe is not a robot, and the provider-reported usage reset does not guarantee future availability. Reconcile judgement: retain `open`, recording the failed attempt without claiming a permanent blocker.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d7-two-wheeled-balancing-robot`
- wise-brook-4842 — failed Robin product-agent attempt, probe-only acceptance and Finch dashboard end check
