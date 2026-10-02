---
node_id: 1ce931ee-e26c-5678-a3f9-21c02951af7e
slug: idle-ledge-8635
title: D1. A frozen judge agrees with the owner on designs it never saw (orun1)
created_at: '2026-10-02T17:01:59+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun1: **D1. A frozen judge agrees with the owner on designs it never saw.** - `docs/probes/orun1/ratings.json` is the owner's ground truth and is never edited. Its `dev` designs are for building the judge; its `heldout` designs are for measuring it. - Before any held-out measurement, `docs/probes/orun1/README.md` (below the marker) freezes a **judge version**: model (`claude-opus-5-5`), prompt, inputs, the comparison form (pairwise, ranking or rubric: the run decides), the number of calls and how they are aggregated. - **Inputs are images only**, rendered by the product from the design's project at its accepted revision on the dark prototype floor: the hero and any `look` views the version names. The judge never sees a thesis, the agent's notes, a project or file name, the owner's verdicts or another design's verdict. - **The bar, on the held-out set:** - pairwise order agreement of **80% or more** over every held-out pair whose owner verdicts differ by two levels or more (Love against Meh or No, Like against No); - every held-out Love ranked above every held-out No; - Kendall's tau over all held-out pairs, reported with its pair count. - **Each judge version is measured on the held-out set once.** A new version needs a recorded change motivated by dev results, never by held-out ones. Every version and every held-out measurement is published, including the failures. - **Baseline:** ot10's frozen judge (rubric T1–T7, `docs/probes/ot10/README.md`) is measured on the same held-out pairs with the same metric, and reported beside the new one. - The judge's prompt never reaches the product agent. [rec: sweet-brook-2725]

Declared target: `gap-d1-frozen-judge-agrees-owner`. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: sweet-brook-2725]. Reconcile judgement: earlier runs have criteria with the same letters, so every orun1 gap title carries the run.

No work yet; the criterion opened with the run [rec: sweet-brook-2725].

## Negative knowledge

None yet.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
