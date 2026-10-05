---
node_id: 08ae7ed9-504c-52d2-be6a-f83e8d0a067a
slug: vast-ivy-6277
title: V1. The 3D viewport has a training and stage overlay
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **V1. The 3D viewport has a training and stage overlay.** [rec: golden-snow-6627]

- The overlay is a new element in the 3D viewport's area, with stable hooks listed in `docs/DASHBOARD.md` §2 and pinned by `test_review_design.py`. [rec: golden-snow-6627]
- It shows: [rec: golden-snow-6627]
  - the project's stage: idle, designing (a revision accepted recently), training (the iteration out of the total, and the ETA), evaluating, or failed; [rec: golden-snow-6627]
  - reward-per-step and loss sparklines from `progress.json`'s curves; [rec: golden-snow-6627]
  - the best reward and its iteration; [rec: golden-snow-6627]
  - `progress.json`'s `warning`, styled as a warning; [rec: golden-snow-6627]
  - which run it is reading, when there is more than one. [rec: golden-snow-6627]
- It updates on the page's existing poll, with no new polling loop. A browser test driven through `cli/cadex_cli/browser.py` shows it changing as a fixture's `progress.json` is rewritten. [rec: golden-snow-6627]
- It collapses to one line, and the collapsed state is a per-browser convenience. Measured at 390 px wide, it covers no more than a quarter of the viewport when expanded. [rec: golden-snow-6627]
- An ADR records it as the first panel brought back after ADR-533. [rec: golden-snow-6627]

Declared target: `gap-v1-3d-viewport-has-training`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v1-3d-viewport-has-training)
