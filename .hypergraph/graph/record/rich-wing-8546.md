---
node_id: 74a8a857-4679-57e1-9407-58eba1662b01
slug: rich-wing-8546
title: 'orun1 D1 baseline measured: ot10''s frozen judge fails the held-out bar (13.5% gap-pair agreement, tau-b -0.079)'
created_at: '2026-10-02T21:35:26+00:00'
parents:
- polished-shade-7671
summary: ''
---
## What

Completed and measured the D1 baseline: ot10's frozen judge
(`docs/probes/ot10/runner/judge.py`, rubric T1–T7, unchanged) over all 26
orun1 held-out designs, scored with the pre-registered `runner/metrics.py`.
Results are in `docs/probes/orun1/README.md` below the marker ("D1 baseline
result"), per-design scores in `docs/probes/orun1/baseline/<id>-score.json`
and the metric output in `baseline/summary.json` (commit `68dc2d01`).

## Why

The critic's message for this iteration: record iterations 4–5 first (done
as `polished-shade-7671`), then run `baseline.py --jobs 3` to `missing: []`,
compute the three metrics, write the table into the README and record. This
is horizon rung short-2 — the baseline before any judge-building. Done as
asked; no deviation.

## Method

- `pixi run python docs/probes/orun1/runner/baseline.py --jobs 3`: the 10
  designs already scored were skipped (not re-judged); the other 16 were
  copied to `~/cadex-projects/orun1-ho-<id>`, rendered with ot10's input set
  (studio hero + `iso`, `iso_back`, `front`, `right`, `top`) and judged once
  each. Final line: `{"designs": 26, "missing": []}`. No harness failure, no
  usage limit, no refusal.
- `metrics.py docs/probes/orun1/baseline --out baseline/summary.json`;
  `test_metrics.py` 6 passed. Per-gap-kind counts cross-checked by hand from
  `summary.json`.

## Result

ot10's judge fails every part of D1's bar on the held-out set:

| metric | ot10 baseline | bar |
|---|---|---|
| pairwise agreement, owner gap ≥ 2 | 13.5% (5/37; 29 reversed, 3 tied) | ≥ 80% |
| every Love above every No | fails, 0 of 2 | holds |
| Kendall τ-b, all pairs | −0.079 over 325 (79 C, 98 D, 148 tied) | reported |

Mean ot10 total by owner verdict: Love 13.0 (n=2), Like 16.0 (11), Meh 15.0
(12), No 18.0 (1). The held-out No `biped-h-free` scores 18 (joint top);
Loves `biped-c-exposed-mechanism` 12 and `quadruped-e-hard-surface` 14. By
gap kind: Love × Meh 5 agree / 18 reversed / 1 tied; Love × No 0/2;
Like × No 0/11. The ot10 rubric is anti-aligned with the owner: it rewards
the soft-box-with-face finish ot10 prescribed. (That last sentence is a
reading, not a measurement.)

Consequences for the next iteration:
- The held-out set has now been touched once, by the baseline only. Judge
  versions must be built on the 29 dev designs; nothing in this result (which
  designs were reversed) may be used to choose a judge version. The reading
  above that ot10's rubric rewards the rejected archetype is already visible
  in the dev ratings and the README's operator reading, which is where any
  judge design should cite it from.
- `~/cadex-projects/orun1-ho-<id>` copies (26) remain; they are the
  held-out inputs a frozen judge version will render from.
- Tail is now 4 unreconciled records (idle-loom-0473, forest-sun-0304,
  polished-shade-7671, this one) — over the charter's three-record trigger;
  a reconcile is due.

Dispatch closed: 1 unit — D1 baseline measured: ot10 judge 13.5% gap-pair agreement, Love>No fails, τ-b −0.079 (325 pairs)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 68dc2d013b1fc645ed0ede1f0acb332947865b50

## State Impact

- target: idle-ledge-8635 — Baseline complete (commit 68dc2d01): ot10 judge on 26 held-out designs, gap>=2 agreement 13.5% (5/37), Love>No fails 0/2, tau-b -0.079 over 325 pairs; no orun1 judge version yet
