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

Open charter criterion for run orun2: **S1. The shell is gone and nothing reaches for it.** - `git ls-files shell | wc -l` is 0. - No pixi task, `package/` script, CMake rule, test, `.gitattributes` LFS rule or live doc refers to `shell/`, `mesh_agent`, a `.blend`, or `CADEX_BLENDER_EXECUTABLE`. ADRs and `docs/history/` are the exception. - The removal follows the two-commit protocol: a disable commit, then a delete commit, each green. - The licensing posture is restated without the GPL half: - `test_licensing_compliance.py`, `docs/inherited-modifications.json` and `docs/PROVENANCE.md` say what is now true; - an ADR records that the repo no longer carries GPL code, if that is what the audit finds. - **`mesh.blender` is retired**, with an ADR naming every project and example that used it: - the op, its runner, worker and adapters, `examples/blender_enclosure.py`, its tests and `docs/BLENDER-RECIPES.md` are all removed; - `OP_ARG_SPECS` and `docs/INTEGRATION.md` change in the same commit. - Codex and pi support is removed. - Shell-only tests are gone. Tests that only *mention* the shell are rewritten: - purity guardrails; - `rollout_bake_integration.py`; - `test_project_docs.py`. [rec: winter-stone-5109]

**Progress, rungs 1–3 of the removal** [rec: lucky-haven-1081] [rec: clear-heron-4371]:

- **Disable commit landed** (`324b0411`, ADR-495): the pixi tasks `setup`, `build-shell`, `app`, `install-app`, `uninstall-app` and `gate` are gone (setup is now `setup-engine` then `build-engine`); `package/app/build_app.sh` and `make_app_icon.py` deleted, taking the only `SPDX_EXEMPT` row with them; the CI `app` job became `engine-macos` with no shell cache, LFS pull, build or bundle gate. Shell-mentioning tests were rewritten rather than weakened: the mujoco purity guardrail now covers the dashboard's import closure and `review_static/*.js`; `rollout_bake_integration.py` became `rollout_review_integration.py` (live `cadexd` trace read through the dashboard's own placement code — 52 frames, swing moved, `OK`); `test_project_docs.py` pins the GUI-attached mode's retirement and that no `cli/cadex_cli` file names `shell/`, `mesh_agent` or `CADEX_BLENDER_EXECUTABLE`. The only test still reading `shell/` is `test_licensing_compliance.py`, deliberately. Gates: test-engine 2598 passed / 61 skipped; `cli/tests` 1290 passed / 1 skipped / 1 pre-existing heartbeat-race flake [rec: lucky-haven-1081].
- **`mesh.blender` retired** (`e53b71eb`, ADR-496): the `blender` method and recipe branches, `cadex_blender_runner.py`, `cadex_blender_worker.py`, `examples/blender_enclosure.py`, `test_blender_recipe.py`, the CMake install lines and `CADEX_BLENDER_EXECUTABLE` forwarding removed; `docs/BLENDER-RECIPES.md` moved to `docs/history/`. A grep of all 284 projects and the jobs directory found no user — only the example. `mesh.blender` was never a cadexd op, so `OP_ARG_SPECS` is unchanged; `docs/INTEGRATION.md` dropped its runtime paragraph in the same commit. The `test_video.py` heartbeat race was fixed (atomic `.tmp` + `replace()`). Gates: test-engine 2582 passed / 56 skipped; `cli/tests` 1291 passed / 1 skipped; build + stage ok, payload free of `cadex_blender_*`; packaged lifecycle gate 24 passed [rec: clear-heron-4371].
- **Still open:** Codex/pi retirement (its own ADR; the code lives in `shell/`, the rest is docs and guidance wording), the `shell/` delete commit with the licensing restatement (`test_licensing_compliance.py`, `inherited-modifications.json`, `PROVENANCE.md`), and the live-doc references (192 counted before the disable commit [rec: old-arrow-4088]). `docs/ROADMAP.md`'s ADR-185 checkbox line still describes the bridge: the charter forbids hand-editing ROADMAP while AGENTS.md asks for checkbox updates, and the record defers that to R1 [rec: clear-heron-4371].

Reconcile judgement: `open` → `working`. Two of the criterion's named rungs have landed green with measured gates; `git ls-files shell` is still 19k, so it is nowhere near ticked [rec: lucky-haven-1081] [rec: clear-heron-4371].

Declared target: `gap-s1-shell-gone-nothing-reaches`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- lucky-haven-1081 — ADR-495 disable commit: no pixi task, package script, CI job or test (bar the licensing audit) reaches shell/; both suites green
- clear-heron-4371 — ADR-496: mesh.blender retired, no project used it; packaged gate 24 passed
- old-arrow-4088 — before count of live references for S1 to clear
