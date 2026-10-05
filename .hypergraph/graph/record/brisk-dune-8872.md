---
node_id: 4e6818ec-a73b-5f47-ac62-e09bd70ce3ba
slug: brisk-dune-8872
title: 'V3 backfill: cadex revision backfill keeps a rebuild only on its exact revision id (ADR-548), 9/13 kept on orun3-biped'
created_at: '2026-10-05T13:24:32+00:00'
parents:
- scarlet-wood-2990
summary: ''
---
## What

`cadex revision backfill [SELECTOR] --project DIR` (ADR-548, landed in commit `283b6eca`, which iteration #11 committed without a record). It rebuilds the models that the per-revision store (ADR-546) never kept: every revision accepted before the store existed. It keeps the accepted revision from its staged attempt on disk. Every other revision has its stored source rebuilt in a scratch project, using the trail's stored values, else the values the project's own repository recorded in `script.json` at the revision's acceptance commit (with that commit's `assets/`), else none. A rebuild is kept **only** when the engine lands on exactly the trail's revision id, and on its digest when the trail records one. A revision whose id another kept ordinal already has is copied. A rebuild that lands elsewhere or is refused is a `failed` row, and its reason is remembered in the store's index under `unrebuilt`. `revision_models` and the timeline show that reason, never another revision's geometry. Nothing that reads the store calls the command: not the dashboard, not `revision list`, not a session.

## Why

This closes V3's last open item ("rebuilding old revisions is an explicit CLI command, not a side effect of opening the page"). This record is written retroactively, in iteration 12, because iteration 11 landed the code with no record. The critic's message asked for it first, with its 9/13 and bytes measurement, and with suite results from a run with the GPU hidden.

## Method

- Code: `cli/cadex_cli/revision_meshes.py` (`backfill`, the scratch rebuild, the id/digest gate, `unrebuilt`), `cli/cadex_cli/__main__.py` (the `revision backfill` action, no row and no commit), and the docs (`docs/CLI.md`, `docs/ARCHITECTURE.md`, and ADR-548 in `docs/DECISIONS.md`).
- Tests:
  - `cli/tests/test_revision_meshes.py`, against the real engine. A biped's foot is changed twice, then the trail's values and the store are stripped. Revision 3 is kept from disk, and 1 and 2 are rebuilt from the repository's values. With the repository also gone, revision 2 lands on revision 1's id, is reported failed, and stays unkept with its reason. The project's files are byte-identical afterwards. A rerun with a selector rebuilds nothing.
  - `cli/tests/test_review_revisions.py`, in the browser: the timeline says "missing" and names the command, and after backfill it draws revision 1, and revision 2 tinted over revision 1's ghost.
- Measured on `orun3-biped`, as iteration 11 reported in ADR-548.
- Re-verified in iteration 12, with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`:
  - `pixi run test-engine` on `283b6eca`: 2585 passed, 58 skipped, exit 0.
  - The full `cli/tests` suite on the tree that also carries ADR-549 (cli-only, additive): see Result.

## Result

- **9 of 13 of `orun3-biped`'s revisions now have a kept model.** The store holds 7,126 bytes of blobs (5 distinct part buffers) and a 28,201-byte index (30,876 bytes with the four failure reasons), against 102,612 bytes for nine full copies (one full copy is about 11,400 bytes).
  - Revision 13 was kept from disk, adding 5,704 bytes.
  - Revision 1 was rebuilt, adding 1,422 bytes.
  - Revisions 2, 4, 5, 8, 11 and 12 were rebuilt, adding 0 bytes each.
  - Revision 7 shares revision 5's id and was copied.
  - The backfill took 12 s, at 0.5 to 1.0 s per rebuild.
- **Revisions 3, 6, 9 and 10 cannot be rebuilt by today's engine.** Each sets `policy_on=1`, and the policy was trained on a task bundle whose digest the current engine no longer produces (ADR-520's stale policy). Their pages say so.
- `script.json` and `script_history/history.json` hash the same before and after.
- Suites, run with the GPU hidden: engine 2585 passed / 58 skipped. CLI: 1157 passed, 1 skipped (the private-address smoke, needs CADEX_REVIEW_HOST), exit 0, 15m55s.
- Concern: ADR-546's earlier "9 kept" figure came from another copy, `orun3-biped-v3meas`, where the revisions were restores. ADR-548 corrects it: of the 13 originals, 9 are kept and 4 cannot be rebuilt by any current build.
- V3's evidence list is now complete: store, timeline, ghost and tint, and backfill.

Dispatch closed: 1 unit — retroactive record of iteration #11's unit, ADR-548 `cadex revision backfill` (V3's last item), 9/13 kept on orun3-biped

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 283b6eca07b60a3f98e2bed1fc397c1b6fbc5b10

## State Impact

- target: peaceful-spire-1615 — backfill landed (ADR-548, 283b6eca): explicit command keeps a rebuild only when its revision id (and digest) matches; on orun3-biped 9 of 13 revisions kept, 7,126 B of blobs + 28,201 B index vs 102,612 B for nine full copies (~11.4 KB per copy); revisions 3, 6, 9, 10 unrebuildable (ADR-520 stale policy) and shown with their reason; V3's evidence list complete; CLI suite 1157 passed / 1 skipped with GPU hidden
