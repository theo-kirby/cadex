---
node_id: fab8229f-e774-54c6-aee5-47760bcaef42
slug: early-rain-5934
title: B3. Robin balances across the declared evaluation set.
created_at: '2026-09-22T17:39:47+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: open

## Current

**B3. Robin balances across the declared evaluation set.** On each of ten frozen reset seeds, the accepted policy runs the full 8 s at the task's 50 Hz control rate, stays within 30 degrees of accepted chassis attitude throughout, and never fires `fallen`. Report all ten trajectories' duration, peak tilt, minimum chassis height, termination, and policy/model digests. One failed seed fails this criterion; do not average it away. [rec: curious-branch-9704]

**Not started [rec: curious-branch-9704].** The criterion is declared by the ot9 operator directive and no work unit has yet produced evidence toward it. It flips to `working` only when a causally parented record carries the measured evidence; the owner ticks the checkbox [rec: curious-branch-9704].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
