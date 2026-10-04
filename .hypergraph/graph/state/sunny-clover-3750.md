---
node_id: b688c13f-c50a-563f-8a85-8063f0133e77
slug: sunny-clover-3750
title: S1. The shell is gone and nothing reaches for it (orun2)
created_at: '2026-10-03T10:54:40+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **S1. The shell is gone and nothing reaches for it.** - `git ls-files shell | wc -l` is 0. - No pixi task, `package/` script, CMake rule, test, `.gitattributes` LFS rule or live doc refers to `shell/`, `mesh_agent`, a `.blend`, or `CADEX_BLENDER_EXECUTABLE`. ADRs and `docs/history/` are the exception. - The removal follows the two-commit protocol: a disable commit, then a delete commit, each green. - The licensing posture is restated without the GPL half. - **`mesh.blender` is retired**, with an ADR naming every project and example that used it. - Codex and pi support is removed. - Shell-only tests are gone; tests that only *mention* the shell are rewritten. [rec: winter-stone-5109]

**Every S1 requirement now has measured evidence; ready for the owner to tick** [rec: mellow-pine-4848]:

- **Disable commit** (`324b0411`, ADR-495): the pixi tasks `setup`, `build-shell`, `app`, `install-app`, `uninstall-app` and `gate` are gone (setup is `setup-engine` then `build-engine`); `package/app/build_app.sh` and `make_app_icon.py` deleted; the CI `app` job became `engine-macos`. Shell-mentioning tests were rewritten, not weakened: the mujoco purity guardrail covers the dashboard's import closure and `review_static/*.js`; `rollout_bake_integration.py` became `rollout_review_integration.py`; `test_project_docs.py` pins the GUI-attached mode's retirement [rec: lucky-haven-1081].
- **`mesh.blender` retired** (`e53b71eb`, ADR-496): runner, worker, recipe branches, `examples/blender_enclosure.py`, `test_blender_recipe.py` and the `CADEX_BLENDER_EXECUTABLE` forwarding removed; `docs/BLENDER-RECIPES.md` in `docs/history/`. No project of 284 used it. It was never a cadexd op, so `OP_ARG_SPECS` is unchanged; `docs/INTEGRATION.md` dropped its runtime paragraph in the same commit. Packaged gate 24 passed [rec: clear-heron-4371].
- **Codex and pi retired** (`96a67c9e`, ADR-497): Claude Code is the only harness; AGENTS.md and VISION say so; the dead macOS runtime validator (imported the ADR-021-deleted `CadexProvider`/`CadexCodex`, no callers) is deleted; `test_claude_code_is_the_only_harness` pins that no `cli/cadex_cli` module names `codex`, `pi_tools`, `PiBackend` or `registerTool`. Engine 2582 passed / 56 skipped; CLI (GPU hidden) 1292 passed / 1 skipped [rec: crimson-union-6659].
- **Delete commit** (`6b21d3f7`, ADR-498): `git ls-files shell` = 0 (6,185 tracked files went), no `.gitattributes` LFS rule or shell submodule remains; licensing restated — the manifest is FreeCAD-only, `test_the_repository_carries_no_gpl_source` pins no GPL SPDX header and nothing under `shell/`, NOTICE/THIRD_PARTY/PROVENANCE rewritten; `BLENDER.md` and `BLENDER-TREE.md` in `docs/history/`. Engine 2582/56 skipped, CLI 1292/1 skipped, packaged gate 35 passed [rec: calm-quartz-1493].
- **Live-doc sweep** (`4266f639`, ADR-499): no live doc names `shell/`, `mesh_agent`, a `.blend` or `CADEX_BLENDER_EXECUTABLE`, pinned by `test_no_live_doc_names_the_deleted_shell`; only ADRs and the history set do [rec: mellow-pine-4848]. That sweep started from 192 live references counted before the disable commit [rec: old-arrow-4088].

**Re-audited at `f3b4828f`** (measurement only, nothing changed) [rec: empty-heron-1077]:
- `git ls-files shell` is 0 [rec: empty-heron-1077].
- Every remaining `shell/`, `mesh_agent`, `.blend` or `CADEX_BLENDER_EXECUTABLE` hit is allowed. The hits are: ROADMAP Phase 6 (historical), the parity ledger, the orun2 before-measurement and report, the guard tests themselves, the "left with shell/ (ADR-498)" notes, older read-only probes, and two false positives ("shell/timeout wrappers") [rec: empty-heron-1077].
- `test_project_docs.py` 40 passed. `test_licensing_compliance.py` 10 passed, 1 skipped. The skip is the packaged-gate test with `CADEX_ENGINE_ROOT` unset, so it does not count as a pass [rec: empty-heron-1077].

Reconcile judgement: status stays `working` — implemented and evidenced; the human owns the charter checkbox and roles do not tick it. Declared target: `gap-s1-shell-gone-nothing-reaches`; every orun2 gap title carries the run because earlier runs reuse the letters [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- lucky-haven-1081 — ADR-495 disable commit: no pixi task, package script, CI job or test (bar the licensing audit) reaches shell/; both suites green
- clear-heron-4371 — ADR-496: mesh.blender retired, no project used it; packaged gate 24 passed
- old-arrow-4088 — before count of live references for S1 to clear
- crimson-union-6659 — ADR-497: Claude Code is the only harness; Codex/pi retired and test-pinned
- calm-quartz-1493 — ADR-498: shell/ deleted, licensing restated without the GPL half; packaged gate 35 passed
- mellow-pine-4848 — ADR-499: no live doc names the deleted shell, test-pinned; every S1 requirement evidenced
- empty-heron-1077 — S1 re-audit at f3b4828f: shell 0 files, every remaining reference allowed, doc and licensing guards green
