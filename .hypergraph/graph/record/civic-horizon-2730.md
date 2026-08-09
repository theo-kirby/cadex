---
node_id: f49e2d70-87aa-5f67-bb03-ce3da6906f39
slug: civic-horizon-2730
title: 'Prehistory: the teardown — FreeCAD stripped to one engine'
created_at: '2026-08-09T15:15:58+00:00'
parents:
- lone-haven-0640
summary: 'Two days: docs written first, 17 workbench trees deleted under a two-commit protocol, and the per-domain surface replaced by one project script with a rebuild-digest test.'
---
## What

The first two days of the repository: 29 commits, Phases 0–2 and 4 of
`docs/ROADMAP.md`, ADR-001…ADR-016. The documentation set was written **first**
(`docs/VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `DECISIONS.md`); then 17
unused FreeCAD workbench trees were deleted; then the per-domain multi-program
surface was replaced by **one project script**.

## Why

Follows the break from VibeCAD. Before anything could be built on the engine,
the engine had to be understood and reduced to what the product actually uses —
the "dig deep on how FreeCAD really works" half of the north star.

## Method

The removal protocol established here is still in force (`docs/FREECAD.md` §3):
dependency audit, a **disable commit** (drop the tree from
`src/Mod/CMakeLists.txt`, verify build + launch + tests), then a **delete
commit** (verify again), then a `docs/DECISIONS.md` entry. Batch A was 13 trees
(ADR-007); batch B was Draft, Points, TechDraw and Spreadsheet (ADR-009); a
dead-code sweep inside `src/Mod/cadex` followed (ADR-010).

Phase 2 then made one script the sole source of truth: `params`/`num` declared
at the top of the script, one multi-domain worker, publication under a single
transaction with an ownership lint and orphan GC (ADR-011…ADR-013), and sliders
bound to `param_specs` and committing through `set_params` (ADR-014).

## Result

The exit criterion was a testable property rather than a feeling: **delete the
document, re-run the script, and the content digest matches**
(`cadex_rebuild.py`, ctest `CadexProjectRebuildDigest`, rebuild-vs-accepted
*and* rebuild-vs-rebuild). That property is still asserted on every
`open_project` today, which is why restart determinism is proven continuously
rather than once per audit.

Phase 4 added the mesh domain on `Mod/Mesh` + `Mod/MeshPart` (ADR-016) and hit
the first real determinism hazard: FreeCAD's native mesh set operations return
run-dependent orderings and triangulations, so mesh outputs needed canonical
vertex/facet reordering plus a vertex-set digest fingerprint before they were
digest-stable at all.

`v0.0.1` was tagged on 2026-07-24, the only tag in the repository. Per the
author it means nothing: versioning has been loose from the start and was never
kept up. It is not an era boundary and should not be read as one.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW engine — one project script is the sole source of truth, and rebuild-digest equality is the engine's load-bearing property.
- target: NEW inherited-tree-reduction — the two-commit removal protocol exists and Phase 1 is complete.
