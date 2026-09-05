---
node_id: ea5e4567-9455-5c56-9e69-af71ebc9539b
slug: brave-stone-9609
title: Parts library — hardware catalog and remaining families
created_at: '2026-09-05T21:41:12+00:00'
parents:
- forest-wind-0342
summary: ''
---
Status: open

## Current

Catalogued hardware is available as the **lib script namespace** over `CadexCatalog`, composed as parametric BREP values with exact mounting interfaces and deliberately simple cosmetics (ADR-181, Phase 17) [rec: twilight-lake-8164].

**L0 fasteners/bearings and L1 servos work**: bolts, nuts, washers, inserts, clearance/tap-drill data, ball bearings, bushings, SG90/MG90S/MG996R/DS3218 servos and measured micro horns. Catalog rows cite sources and label approximate dimensions; servo actuators use rated-voltage stall torque converted once into engine units. Twenty-seven library tests include a real-kernel build of all generators, and the packaged lifecycle gate passed [rec: twilight-lake-8164].

**L2 boards and L3 motors/mechanisms remain open.** 25T horns and servo pigtail terminals are deferred for lack of dimensioned sources; manufacturer STEP files are the identified next source [rec: twilight-lake-8164].

## Negative knowledge

None yet.

## Provenance

- twilight-lake-8164 — L0/L1 landed with catalog and kernel validation; L2/L3 and unsourced interfaces remain open
