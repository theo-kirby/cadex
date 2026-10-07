---
node_id: 17736948-d8a0-50ff-b93f-5654ac91e968
slug: falling-walrus-2752
title: M1. Predicates measure the motion, not only where it ended
created_at: '2026-10-07T17:58:12+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun5: **M1. Predicates measure the motion, not only where it ended.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

- New evaluation metrics, from the trace (A3): [rec: honest-bay-2056]
  - **angular progress about a point**: net signed turns of a body about
    a point and axis in a frame, and laps completed, so a body that
    rocks on an arc measures about zero; [rec: honest-bay-2056]
  - **distance from a point**: a body's final and mean distance from a
    point in a frame, with no goal declared. [rec: honest-bay-2056]
- A spec can bound them like any metric. A metric that could not be
  measured fails (the `judge` rule, ADR-586). [rec: honest-bay-2056]
- Tests: a circling trace passes a laps predicate; a rocking trace on
  the same arc fails it; a trace that ends early fails rather than
  crashes. [rec: honest-bay-2056]

Not started: no record yet claims work against this criterion [rec: honest-bay-2056].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-m1-predicates-measure-motion-not)
