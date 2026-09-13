---
node_id: 845888c4-0dab-517b-8b47-c9d9761b9392
slug: cool-hill-9617
title: D5. The biped is a buildable mechanism
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: open

## Current

Charter criterion: **D5. The biped is a buildable mechanism.** A redesigned biped in a fresh project uses MG90S servos from `lib.servo` with catalog horns, bearings and fasteners, and modelled printable parts that mount them. Evidence: a per-solid inventory in the project (`docs/INVENTORY.md`: every solid, its source as catalog family and part id or "modelled", its mass) with no bare primitive standing in for a part; a fit check that every servo sits in a pocket with the declared clearance and every horn meets its link; no floor, slab or wall in the design; a viewport screenshot in which the servos and horns are recognisable; and the collision proxies declared per part with their relation to the solid recorded. Declared target `gap-d5-biped-buildable-mechanism-redesigned`; nothing is implemented or claimed for it yet — the record that supplies evidence names this criterion, and the human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

None yet.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d5-biped-buildable-mechanism-redesigned`
