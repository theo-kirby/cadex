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

Open charter criterion for run orun1: **D1. A frozen judge agrees with the owner on designs it never saw.** `docs/probes/orun1/ratings.json` is the owner's ground truth and is never edited; `dev` designs build the judge, `heldout` designs measure it. Before any held-out measurement the README (below the marker) freezes a **judge version** — model `claude-opus-5-5`, prompt, inputs, comparison form, call count and aggregation. **Inputs are images only**, rendered by the product at the accepted revision on the dark prototype floor; the judge never sees a thesis, notes, names or verdicts. **The bar, on held-out:** pairwise agreement **≥ 80%** over pairs whose owner verdicts differ by two levels or more; every held-out Love above every held-out No; Kendall's tau over all pairs, reported with its count. **Each judge version is measured on held-out once**; a new version needs a recorded change motivated by dev results only; every version and measurement is published. **Baseline:** ot10's frozen judge (T1–T7) on the same pairs and metric. The judge's prompt never reaches the product agent [rec: sweet-brook-2725]. The human owns the checkbox.

**Split, counted:** 29 dev / 26 held-out (the README had said 27/28), with **37** held-out pairs differing by two levels or more [rec: forest-sun-0304].

**Baseline measured — ot10's judge fails every part of the bar** (commit `68dc2d01`) [rec: rich-wing-8546]. Pre-registered in the README with ties counting as disagreement [rec: forest-sun-0304]; run by `docs/probes/orun1/runner/baseline.py`, which copies each held-out design to `~/cadex-projects/orun1-ho-<id>`, draws ot10's inputs (hero + `iso`, `iso_back`, `front`, `right`, `top`) with `render_set.py`, judges once with ot10's unchanged `judge.py`, and never re-judges a scored design [rec: polished-shade-7671]; scored by `runner/metrics.py` (6 tests) [rec: rich-wing-8546].

| metric | ot10 baseline | bar |
|---|---|---|
| agreement, owner gap ≥ 2 | 13.5% (5/37; 29 reversed, 3 tied) | ≥ 80% |
| every Love above every No | fails, 0 of 2 | holds |
| Kendall τ-b, all pairs | −0.079 over 325 (79 C, 98 D, 148 tied) | reported |

Mean ot10 total by owner verdict: Love 13.0 (n=2), Like 16.0 (11), Meh 15.0 (12), No 18.0 (1); the held-out No `biped-h-free` is joint top at 18 [rec: rich-wing-8546]. Per-design scores are in `docs/probes/orun1/baseline/`, metrics in `baseline/summary.json`.

**Held-out discipline from here.** The held-out set has been touched once, by the baseline only. Judge versions are built on the 29 dev designs, and which held-out pairs the baseline reversed may not be used to choose one [rec: rich-wing-8546]. The 26 `orun1-ho-<id>` copies remain as the held-out inputs a frozen version will render from. Renders should run serially or at low parallelism, because reopen under load can still refuse (see F1) [rec: forest-sun-0304]. No orun1 judge version exists yet.

## Negative knowledge

- [scope: ot10's frozen rubric judge (T1–T7) on the orun1 held-out set | confidence: high | evidence: rich-wing-8546] It disagrees with the owner on 29 of 37 gap pairs and ranks the held-out No above both Loves; it cannot serve as D1's judge or as a starting point tuned on held-out results.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- forest-sun-0304 — baseline pre-registered in the README; render runner proven on arm3; split counted 29/26 with 37 gap pairs
- polished-shade-7671 — catch-up record: baseline.py runner and the first 10 of 26 held-out scores (iterations 4–5)
- rich-wing-8546 — baseline complete: 13.5% gap-pair agreement, Love>No fails 0/2, τ-b −0.079 over 325 pairs
