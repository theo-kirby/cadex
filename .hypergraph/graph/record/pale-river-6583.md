---
node_id: 3fdd9a84-1c1e-5bb1-bc0a-f02b1169740e
slug: pale-river-6583
title: 'The Cycles disable commit (iteration #55, 70591c1e) is in git but in neither graph: no record node, and ADR-196 has no DECISIONS.md entry'
created_at: '2026-09-06T11:18:52+00:00'
parents:
- first-moss-9524
summary: ''
---
## What

Found during the 2026-09-06 reconcile pass (the maintainer's bookkeeping, not feature work): the Cycles **disable commit** — iteration #55, `70591c1e`, 2026-09-06 08:44 — has no record node in the record graph, and the ADR it cites, ADR-196, has no entry in `docs/DECISIONS.md`. The commit is real and is the disable half of a Phase 13b shell-side removal: `package/app/build_app.sh` passes `-DWITH_CYCLES=OFF` and removes the stale `addons_core/cycles` and `presets/cycles` copies from the installed bundle, `docs/BLENDER-TREE.md` §4 and `docs/ROADMAP.md` name it, and the inherited `shell/CMakeLists.txt` is untouched. Its commit message is the session-limit banner, because iteration #55 hit the quota after committing.

## Why

`first-moss-9524` reported the missing DECISIONS entry as owed; the reconcile pass found the missing record node beside it while checking whether the state graph already carried a Cycles claim (it did not). A removal that is in git but in neither graph nor log is invisible to the project, and the state graph may only cite record nodes — so this node exists to make the disable commit citable.

## Method

`git log --oneline | grep -i cycles` found nothing by message; `git show --stat 70591c1e` and the `build_app.sh` hunk identified it. `grep` over `.hypergraph/graph/{record,state}` for `ADR-196`, `70591c1e` and `Cycles` found only `first-moss-9524` (record) and the Phase 13b candidate list on `round-glacier-2865` (state).

## Result

No code change. Two things owed by the next inherited-tree unit, in order: the ADR-196 entry in `docs/DECISIONS.md`, then the Cycles **delete commit** (`shell/intern/cycles` plus the `build_app.sh` line, per the comment in that hunk). The two-commit protocol's disable half is done for Cycles; the delete half and the log entry are not.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 70591c1e8ca8e0ee7038b0d3589aa712c184cc26

## State Impact

- target: round-glacier-2865 — Phase 13b shell side has its first disable commit: Cycles, -DWITH_CYCLES=OFF in package/app/build_app.sh plus the stale add-on/preset copies removed from the bundle, inherited CMake untouched (70591c1e, 2026-09-06); it landed with no record node and ADR-196 has no DECISIONS.md entry — the delete commit and the log entry are the next inherited-tree unit
