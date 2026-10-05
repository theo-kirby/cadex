---
node_id: d7720d6c-ee44-5c66-bca0-33cf43ddc1c5
slug: honest-jasper-7877
title: 'V3 write half: accepted revision models kept by content hash per part (ADR-546)'
created_at: '2026-10-05T12:27:18+00:00'
parents:
- forest-mist-3382
summary: ''
---
## What

V3's write half: each accepted revision's model is kept by content hash per part (ADR-546, commit `11a107b2`). Iteration 8 landed this change without a record. This node is that missing record, written in iteration 9 at the critic's request.
- `cli/cadex_cli/revision_meshes.py` is the new store, under `review/revisions/` in the project. The project's own git already ignores that path (ADR-194).
  - `parts/<sha256>.tess.bin` and `.tess.json` each hold one part's tessellation, named by the sha256 of its buffer. A part that did not change, and a mirrored pair, cost no new bytes.
  - `index.json` (`cadex-revision-meshes-v1`) maps each history ordinal to its revision, its digest, the part blobs and the component placements.
- `retain` runs on every engine session's open and close (`_engine_session` in `__main__.py`), and in `cadex mcp` after each successful modelling call (`Bridge.call`). It is idempotent, it keeps a revision only when the trail's latest entry agrees on the digest, and it never fails the call that triggered it.
- `_prune` bounds the store by `script_history/` (25 entries): a row whose ordinal left the trail is dropped, along with any blob only it named.
- `revision_models` reads absence honestly. A revision accepted before the store, a row naming another revision, or a missing blob each reads `retained: false` with its reason, and no other revision's geometry stands in for it.
- `cadex revision list` carries this as `revisions.models`.
- Docs: ARCHITECTURE.md (the store) and CLI.md (`revision list`). ADR-546 is added.

## Why

V3 is the next-ranked open criterion after V2's two halves (ADR-544, ADR-545). The engine prunes a replaced revision's attempt (`ATTEMPT_KEEP`), so the geometry has to be kept at the moment of acceptance, and the CLI has to do it because the page is read-only (ADR-537, charter B1). The record is late: iteration 8 committed the change as "ouroboros #8: no record", and the critic asked iteration 9 to write it.

## Method

- Measured on `orun3-biped-v3meas`, a copy of `orun3-biped`. Each of the biped's 13 stored revisions was restored in turn, then the foot was changed twice through `cadex params`. The revisions before ADR-506 stored no values, so they came back with today's values, and the 13 collapsed to 7 distinct revisions.
  - A full copy of one revision's tessellation is 11,400 bytes.
  - The first revision kept added 5,704 bytes.
  - Each restore added 0 bytes of blobs and 2,906 bytes of index.
  - Each foot change added about 1,420 bytes of blobs.
  - After 9 kept revisions the store held 8,544 bytes of blobs and a 26,854-byte index, against 102,596 bytes for nine full copies.
- `cli/tests/test_revision_meshes.py`, 4 tests:
  - against the real engine, through the CLI path, a foot change adds only the foot's bytes;
  - against the real engine, through the `Bridge.call` (`cadex mcp`) path, the same holds;
  - with no engine, the absence reasons;
  - with no engine, the pruning bound.
- Full suites at `11a107b2`, run in iteration 9 in a separate worktree on that commit, with the GPU hidden (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`):
  - `pytest cli/tests`: **1137 passed, 11 skipped, 0 failed** (15 min 44 s);
  - `pixi run test-engine`: **2585 passed, 58 skipped, 0 failed** (7 min 36 s).

## Result

What is true now: V3's write half holds. Every accepted revision from now on keeps its model, deduplicated per part, bounded by the trail, and honest about revisions accepted before the store existed. On this box-built biped the index (mostly placements) outweighs the blobs; on a finer model the blobs dominate.

Suites: the CLI suite is green at `11a107b2`, as above. The 11 skips are more than the 1 skip at `802b265e`. The skip reasons were not printed in that run (no `-rs`). The run on the next unit's tree prints them, and its record names them.

Not done in this unit: the page half (the route, the timeline, the ghost, the tint) and the explicit backfill command for revisions accepted before the store.

No new dependency.

Dispatch closed: 1 unit — ADR-546 content-addressed per-part retention of accepted revision models (late record for iteration 8's commit 11a107b2)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 11a107b2fec50b8d343b70449671cdfc4461a359

## State Impact

- target: peaceful-spire-1615 — Write half landed (ADR-546, commit 11a107b2): review/revisions/ keeps each accepted revision's tessellation per part by sha256 (unchanged part = 0 new bytes; 9 kept biped revisions = 8,544 B blobs + 26,854 B index vs 102,596 B full copies), written on every engine session open/close and after each cadex mcp modelling call, bounded by script_history/, old revisions read retained:false with reason; real-engine tests on CLI and bridge paths; suites green at 11a107b2 (cli 1137 passed/11 skipped GPU hidden, engine 2585/58). Page half and backfill command open.
