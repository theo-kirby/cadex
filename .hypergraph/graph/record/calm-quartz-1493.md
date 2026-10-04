---
node_id: 7e79fe56-8f10-5a22-a65e-991500e840fa
slug: calm-quartz-1493
title: 'orun2 S1: shell/ deleted — the repository carries no GPL code (ADR-498)'
created_at: '2026-10-03T13:02:19+00:00'
parents:
- crimson-union-6659
summary: ''
---
## What

**The `shell/` delete commit (ADR-498, commit `6b21d3f7`), with the licensing restatement.** It follows the ADR-495 disable commit (`324b0411`), so the two-commit protocol is complete.

- **Deleted:**
  - all of `shell/`: 19,446 tracked files, about 9.3M lines, including `mesh_agent`, Blender's `extern/`, `shell/.gitattributes` (111 lines of LFS rules, 6,716 LFS pointers) and the four `shell/lib/<platform>` gitlinks;
  - the `.gitmodules` entries for those gitlinks and the `/shell/build_*` `.gitignore` rules;
  - `docs/probes/named-angle/background_probe.py`, the one GPL file outside `shell/` (it imported `bpy` and `mesh_agent`);
  - `*.blend1` and `*.blend@` from the `.gitignore` the CLI writes into new projects.
- **Licensing:**
  - `docs/inherited-modifications.json` drops its `blender` tree (44 entries).
  - `test_licensing_compliance.py` drops the GPL SPDX scopes, the `bl_mesh_agent*` header check, the §2a eight-files test and the shell-client seam test. It gains two tests:
    - `test_the_manifest_names_only_the_fork_still_in_the_tree`;
    - `test_the_repository_carries_no_gpl_source`: nothing tracked under `shell/`, no GPL/AGPL SPDX identifier in the first 12 lines of any tracked non-Markdown file, and `NOTICE` and `THIRD_PARTY_LICENSES.md` do not name `shell/`. It failed on the unchanged `NOTICE` before I fixed it.
  - `NOTICE` drops the Blender entry. `THIRD_PARTY_LICENSES.md` has one fork row and maps obligations to the payload root.
  - `docs/PROVENANCE.md` updates §1 (line counts re-measured), §3 (now history), §7 (one licence), §8 and §9.
  - The licence sections of README, CONTRIBUTING, `docs/INTEGRATION.md`, `cli/README.md` and the `cli/cadex_cli` docstring are restated the same way, and so is `tools/apply_modification_notices.py`.
- **Docs:**
  - `docs/BLENDER.md` and `docs/BLENDER-TREE.md` move to `docs/history/` with superseded banners.
  - `AGENTS.md` goes from 404 to 353 lines: shell repo-map rows, the GPL-boundary and Blender-tree policy bullets, the `shell/` diff rule and the doc-index rows are gone, and a `SHELL-PARITY.md` row is added.
  - FREECAD, VISION and ORGANIC are repointed to the history copies.
  - `docs/SHELL-PARITY.md`: all 29 *drop (proposed)* rows are now **dropped (ADR-498)**.
  - Comments in 4 engine files and 5 suites no longer cite `shell/`. The `_ASSET_SUFFIXES` comment loses the "must stay three" reason, which existed only for the shell's mirror. No behaviour changed.

## Why

The critic named this unit: medium rung 1, the `shell/` delete commit, with its own ADR covering the licensing restatement, the LFS rules, docs that reach for `shell/`, and the two BLENDER docs moved to history. S1 is the top-ranked criterion.

**Where I deviated:** I fixed docs that point at `shell/` paths or describe the licence. I did **not** rewrite the docs whose whole subject is the shell's UI or data flow. ADR-498 lists them as R1's:
- `docs/ARCHITECTURE.md` (pipeline diagram; a build table listing `pixi run setup`/`build-shell`);
- `docs/MUJOCO.md`;
- `SECURITY.md` and `PRIVACY_POLICY.md` (they describe `mesh_agent` data flows and the `.blend` transcript);
- VISION's interface section;
- AGENTS.md's "Where this is going" paragraph;
- `docs/ROADMAP.md`. The charter forbids hand-editing it.

Each of these needs a dashboard rewrite, not a path fix. Doing all of them would have made this two units.

I also wrote two record nodes this iteration. The critic required the catch-up record for iteration 6 (`crimson-union-6659`), and this node is parented on it.

## Method

1. GPL audit with `git grep` for SPDX GPL headers outside `shell/`. The only hit was `background_probe.py`. The Bison parsers in `src/App` and `src/Base` are LGPL under the Bison exception.
2. `git rm -r shell` and the edits above.
3. `pixi run test-engine`.
4. `pixi run build-engine && pixi run stage-engine`, then the packaged gate plus the licensing suite against the restaged payload.
5. The CLI suite with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`.

## Result

What is true now:
- `git ls-files shell | wc -l` = **0**. Tracked files: **6,185** (25,633 before the run, per `docs/probes/orun2/D1-BEFORE.md`).
- No pixi task, `package/` script, CMake rule or `.gitattributes` LFS rule refers to `shell/`. No root `.gitattributes` exists, and no `.gitattributes` anywhere contains `lfs`. `.gitmodules` holds only OndselSolver.
- Engine suite: **2582 passed, 56 skipped**.
- CLI suite, GPU hidden: **1292 passed, 1 skipped** (18:20).
- Packaged gate (`test_cadexd_lifecycle.py` + `test_licensing_compliance.py` with `CADEX_ENGINE_ROOT` = the restaged linux-x64 payload): **35 passed**. That includes the payload-licence test, which did not skip.
- `tools/apply_modification_notices.py --check` exits 0.

**S1 is not yet fully met.** The live docs listed under Why still mention `shell/`, `mesh_agent` or `.blend`: ROADMAP 48 lines, MUJOCO 26, ARCHITECTURE 17, PRIVACY_POLICY 15, INTEGRATION 10 (historical op notes), SECURITY 9, VISION 6, and stragglers in `docs/*-AUDIT.md`, IDEAS, CLI, cadex-release-packaging, `training/README.md` and `analysis/README.md`. No test pins "no live doc mentions shell/" yet. That guard should land with the R1 rewrite, once it can pass.

SECURITY.md and PRIVACY_POLICY.md are user-facing and now describe a deleted app. They are the most urgent R1 items.

Two unreconciled records now sit in the tail (`crimson-union-6659` and this one).

Dispatch closed: 1 unit — shell/ delete commit (ADR-498), licensing restated without the GPL half, all three gates green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 6b21d3f717e952def5dc5679ac4630b2ded2b7f9

## State Impact

- target: sunny-clover-3750 — Delete commit landed (ADR-498, 6b21d3f7) after the disable commit: git ls-files shell = 0 (6,185 tracked files), no .gitattributes LFS rule or shell submodule remains, licensing restated (manifest FreeCAD-only; test_the_repository_carries_no_gpl_source pins no GPL SPDX header and nothing under shell/; NOTICE/THIRD_PARTY/PROVENANCE rewritten), BLENDER.md and BLENDER-TREE.md in docs/history/. Engine 2582 passed/56 skipped, CLI (GPU hidden) 1292/1 skipped, packaged gate 35 passed. Still open for S1: ARCHITECTURE, MUJOCO, SECURITY, PRIVACY_POLICY, VISION interface, ROADMAP still describe the shell (R1 rewrite).
- target: easy-wind-9848 — Since ADR-498 the repository carries no GPL code: the Blender half of docs/inherited-modifications.json is gone, and test_licensing_compliance.py fails if a tracked source file declares a GPL SPDX header or anything is tracked under shell/. The payload's conda readline (GPL-3) stays ADR-171's counsel item.
- target: shy-crane-2573 — Deleted (ADR-498, commit 6b21d3f7); the tag v1-blender-shell is the last tree that carries it; docs/SHELL-PARITY.md records where each part went.
