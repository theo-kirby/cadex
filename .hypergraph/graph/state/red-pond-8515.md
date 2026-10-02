---
node_id: 9d7f39a5-0b47-5ee2-b664-17053c144edd
slug: red-pond-8515
title: F1. A project that was accepted always reopens (orun1)
created_at: '2026-10-02T17:01:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun1: **F1. A project that was accepted always reopens.** Three sweep projects (`digestbug-balancer-b-motors-in-body`, `digestbug-balancer-d-product-shell`, `digestbug-hexapod-h-free`) refuse to open with "The restore pass digest does not match the accepted digest": rebuilding an accepted script gives a different digest from the one accepted. Diagnose the cause, fix it in the product, and add a regression test that fails before the fix; two of the three had been resumed after an interrupted turn, and whether that matters is part of the diagnosis. After the fix all three open and render at their accepted revision, or the report says exactly why one cannot and what the product now does instead of refusing. Work on `orun1-*` copies; the originals stay read-only. [rec: sweet-brook-2725]

Declared target: `gap-f1-project-that-was-accepted`. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: sweet-brook-2725]. Reconcile judgement: earlier runs have criteria with the same letters (e.g. ot5's "F1. The agent sees measured fit"), so every orun1 gap title carries the run.

No work yet; the criterion opened with the run [rec: sweet-brook-2725].

## Negative knowledge

None yet.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
