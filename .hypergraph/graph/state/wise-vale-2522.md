---
node_id: 22629834-b0cb-5d7e-9773-a7f0cf4afef3
slug: wise-vale-2522
title: L1. A closed linkage exports and is driven
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun5: **L1. A closed linkage exports and is driven.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

- The assembly can declare a loop closure: two bodies joined by a
  constraint that closes a chain (A2). The MJCF export writes it as an
  equality constraint, and an actuator on one joint of the loop drives
  the whole chain. [rec: honest-bay-2056]
- The fit sweep moves the closed chain consistently, by solving the
  loop, or refuses with a reason that names the loop. [rec: honest-bay-2056]
- The smoke check holds a linkage steady, and the export's closure
  error stays within the MJCF pose tolerance (ADR-584). [rec: honest-bay-2056]
- Tests: a four-bar driven by its crank, and a slider-crank, each
  reaching the analytic output angle across the crank's range within
  tolerance; an over-constrained loop is refused. [rec: honest-bay-2056]

Not started: no record yet claims work against this criterion [rec: honest-bay-2056].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-l1-closed-linkage-exports-driven)
