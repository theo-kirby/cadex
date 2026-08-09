---
node_id: 4ada7ce5-cfd3-5d64-8637-c7eb21d43f9e
slug: merry-eagle-4093
title: 'Prehistory: one repository — the shell moves in'
created_at: '2026-08-09T15:15:58+00:00'
parents:
- simple-hollow-8675
summary: ADR-030 imported the Blender fork under shell/ as a squashed snapshot; two toolchains kept apart by a scrubbing build script, and Phases 11/12 left the critical path.
---
## What

Phase 13a, pulled to the front of the roadmap (ADR-030). The Blender fork was
imported under `shell/` as a squashed snapshot of the separate `mesh` repository
@ `ac5af55948d`. `shell/` is now by far the largest directory in the tree —
96,020 files — and its birth date, **2026-07-25**, is the sharpest single signal
in the repository's timeline.

## Why

Follows the cadexd split, and depended on it: the seam between the two
repositories was already a process boundary pinned on both requests and
responses, so merging them was a repo-layout and build-orchestration job rather
than an architectural one.

## Method

`shell/lib/*` stay **submodules, never content** (1.3 GB prebuilt per platform,
plus ~790 MB in git-LFS). The FreeCAD tree stays at the repo root, so no CMake
path, pixi task, test or doc reference had to move. One build flow:
`pixi run setup && pixi run app`. The cross-repo payload machinery
(`fetch_cadex_engine.py`, `cadex_engine.txt`, and two CI workflows) was deleted
and folded into one in-tree `cadex-app.yml`.

**The one real technical risk was the toolchains.** The engine builds inside
pixi/conda-forge; the shell builds against `shell/lib/<platform>` with Xcode and
a homebrew `cmake`/`ninja`; and both supply zlib, libpng, OpenSSL and Python at
different versions. `package/app/build_app.sh` filters pixi and conda off `PATH`
and unsets the ~50 variables conda activation exports before invoking cmake on
`shell/`. Verified by construction: the resulting `CMakeCache.txt` is identical
to a pre-merge one apart from the source path.

## Result

Measured on an actual fresh clone rather than inferred: **~21 minutes end to
end** with a warm ccache (clone 9 s, setup 43 s, engine 5 min 27 s, payload
42 s, shell 14 min), then `CADEX-BLENDER-GATE ok: true`,
`engine_from_bundle: true`, picking 372/372, slider median 0.579 s.

The consequence for the roadmap is bigger than the merge itself: **Phases 11
(our engine) and 12 (our shell) stopped being on anyone's critical path** and
became optional internal swaps behind the unchanged protocol — not cancelled,
and kept available precisely by the test-pinned protocol. What went live instead
is Phase 13b: deleting from both inherited trees, in place, under the same
two-commit protocol.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW orientation-and-build — one repository, two toolchains that must not see each other; `pixi run setup && pixi run app` is the whole build.
- target: NEW inherited-tree-reduction — Phases 11 and 12 are unscheduled by choice; 13b is the standing work.
