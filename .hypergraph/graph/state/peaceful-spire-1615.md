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

Open orun3 charter criterion: **V3. The design's history plays in the viewport.** [rec: golden-snow-6627]

- When a revision is accepted, its tessellation is kept, stored by content hash per part. A part that did not change between revisions costs no new bytes. **Measured:** bytes added per revision across `orun3-biped`'s thirteen revisions, against the size of a full copy. [rec: golden-snow-6627]
- Revisions accepted before this change have no retained meshes. The page says so, and it never shows another revision's geometry in their place. Rebuilding old revisions to fill the gap is an explicit CLI command, not a side effect of opening the page. [rec: golden-snow-6627]
- The 3D viewport gets a revision timeline. Scrubbing it shows each retained revision's model. The previous revision is drawn as a ghost, and parts whose digest changed are tinted. A browser test drives the scrubber across at least three revisions. [rec: golden-snow-6627]
- The Revisions menu and the timeline agree on ordinals and on which revision is current. [rec: golden-snow-6627]

Declared target: `gap-v3-design-s-history-plays`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v3-design-s-history-plays)
