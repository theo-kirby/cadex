---
node_id: 70bd1d5c-6a97-52f4-9d1c-29dc6aa00a6a
slug: peaceful-spire-1615
title: V3. The design's history plays in the viewport
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun3: **V3. The design's history plays in the viewport.** Each accepted revision's tessellation is kept by content hash per part, with bytes per revision measured against a full copy. Pre-store revisions say so and never borrow another revision's geometry, and rebuilding them is an explicit CLI command, never a page side effect. A revision timeline in the 3D viewport shows the previous revision as a ghost and tints parts whose digest changed, and a browser test scrubs at least three revisions. The Revisions menu and the timeline agree on ordinals and on which revision is current [rec: golden-snow-6627]. The human owns the checkbox.

**Met on evidence: store, timeline with ghost and tint, and backfill** [rec: brisk-dune-8872]. Reconcile judgement: status `working`, because every V3 item now has evidence, following the precedent of V1 (`vast-ivy-6277`) and V2 (`dry-rain-5997`).

- **Write half (ADR-546, commit `11a107b2`).** `review/revisions/` keeps each accepted revision's tessellation per part by sha256, so an unchanged part costs 0 new bytes. The store is written on every engine session open and close and after each `cadex mcp` modelling call, and it is bounded by `script_history/`. Revisions from before the store, mismatched rows and missing blobs read `retained: false` with a reason. Real-engine tests cover the CLI and bridge paths [rec: honest-jasper-7877].
- **Page half (ADR-547, commit `26f86db5`).** `GET /api/model/revision/<ordinal>` and `/mesh/revision/<sha256>.stl` serve the store. A "Revision history" source puts `#revision-timeline` in the 3D viewport: the newest revision follows unless an older one is pinned, parts whose digest changed are tinted `--info`, and the previous revision is ghosted where it differs. Unretained revisions draw nothing and say why. A Chromium test against the real engine scrubs 3 biped revisions and matches the Revisions menu's ordinals and current revision [rec: scarlet-wood-2990].
- **Backfill (ADR-548, commit `283b6eca`).** `cadex revision backfill [SELECTOR] --project DIR` rebuilds pre-store revisions in a scratch project and keeps a rebuild **only** when the engine lands on the trail's exact revision id (and digest, when recorded); otherwise the row is `failed` and its reason is kept under `unrebuilt` and shown on the timeline. Nothing that reads the store calls it. Real-engine and browser tests; project files byte-identical afterwards [rec: brisk-dune-8872].
- **Measured on `orun3-biped`: 9 of 13 revisions kept**, 7,126 B of blobs + 28,201 B index against 102,612 B for nine full copies (~11.4 KB per copy). Revisions 3, 6, 9 and 10 cannot be rebuilt by today's engine (`policy_on=1` on an ADR-520 stale policy) and are shown with that reason. This corrects ADR-546's earlier "9 kept" figure, which came from the `orun3-biped-v3meas` copy [rec: brisk-dune-8872].
- Suites with the GPU hidden: engine 2585 passed, 58 skipped; cli 1157 passed, 1 skipped [rec: brisk-dune-8872].

## Negative knowledge

- [scope: `orun3-biped` revisions 3, 6, 9, 10 under the current engine | confidence: high | evidence: brisk-dune-8872] They cannot be rebuilt by the current engine because their policy's task-bundle digest is no longer produced (ADR-520). Backfill reports them rather than substituting geometry.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v3-design-s-history-plays)
- honest-jasper-7877 — ADR-546 content-addressed per-part revision store; bytes measured on 9 biped revisions
- scarlet-wood-2990 — ADR-547 revision timeline with ghost and tint; Chromium test scrubs 3 revisions; backfill still open
- brisk-dune-8872 — ADR-548 explicit backfill, exact-id gate; 9/13 kept on orun3-biped; V3 evidence complete
