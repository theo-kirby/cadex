---
node_id: 70bd1d5c-6a97-52f4-9d1c-29dc6aa00a6a
slug: peaceful-spire-1615
title: V3. The design's history plays in the viewport
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun3: **V3. The design's history plays in the viewport.** Each accepted revision's tessellation is kept by content hash per part, with bytes per revision measured against a full copy. Pre-store revisions say so and never borrow another revision's geometry, and rebuilding them is an explicit CLI command, never a page side effect. A revision timeline in the 3D viewport shows the previous revision as a ghost and tints parts whose digest changed, and a browser test scrubs at least three revisions. The Revisions menu and the timeline agree on ordinals and on which revision is current [rec: golden-snow-6627]. The human owns the checkbox.

- **Write half (ADR-546, commit `11a107b2`).** `review/revisions/` keeps each accepted revision's tessellation per part by sha256, so an unchanged part costs 0 new bytes. The store is written on every engine session open and close and after each `cadex mcp` modelling call, and it is bounded by `script_history/`. **Measured:** 9 kept biped revisions take 8,544 B of blobs plus a 26,854 B index, against 102,596 B for full copies. The charter named orun3-biped's thirteen revisions, but the measurement covers the 9 kept. Revisions from before the store, mismatched rows and missing blobs read `retained: false` with a reason. Real-engine tests cover the CLI and bridge paths [rec: honest-jasper-7877].
- **Page half (ADR-547, commit `26f86db5`).** It adds `GET /api/model/revision/<ordinal>` and `/mesh/revision/<sha256>.stl` over the store. A "Revision history" source puts `#revision-timeline` in the 3D viewport: the newest revision follows unless an older one is pinned, parts whose digest changed are tinted `--info`, and the previous revision is ghosted where it differs. Unretained revisions draw nothing and say why. A Chromium test against the real engine scrubs 3 biped revisions and matches the Revisions menu's ordinals and current revision [rec: scarlet-wood-2990].
- Suites at `26f86db5`, GPU hidden: cli 1150 passed, 1 skipped; engine 2585 passed, 58 skipped [rec: scarlet-wood-2990].

**Remaining:** the explicit CLI backfill command that rebuilds models for pre-ADR-546 revisions. Status stays `open` until it lands [rec: scarlet-wood-2990].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v3-design-s-history-plays)
- honest-jasper-7877 — ADR-546 content-addressed per-part revision store; bytes measured on 9 biped revisions
- scarlet-wood-2990 — ADR-547 revision timeline with ghost and tint; Chromium test scrubs 3 revisions; backfill still open
