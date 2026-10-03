---
node_id: 927fe4aa-54de-5087-847f-c63d36783581
slug: lucky-haven-1081
title: 'orun2 S1: shell/ disable commit — nothing builds, gates or reads shell/ (ADR-495)'
created_at: '2026-10-03T11:31:33+00:00'
parents:
- old-arrow-4088
summary: ''
---
## What

The **disable commit** for `shell/` (orun2 S1, ADR-495, commit `324b0411`). `shell/` stays on disk; nothing in the build, CI, packaging or tests reaches for it any more.
- `pixi.toml`: removed the tasks `setup`, `build-shell`, `app`, `install-app`, `uninstall-app` and `gate`. The setup is now `setup-engine` then `build-engine`.
- Deleted `package/app/build_app.sh` and `package/app/make_app_icon.py`. The icon script was GPL in an LGPL tree and was the only `SPDX_EXEMPT` row, so that row is gone too.
- CI: the macOS `app` job became `engine-macos`, with no shell-library cache, LFS pull, shell build, bundle gate or bundle upload. Both jobs now run `setup-engine`. The `.gitmodules` comment now says nothing checks out `shell/lib`.
- Tests were rewritten, not weakened:
  - The purity guardrail `test_the_shell_never_learns_about_mujoco` became `test_the_dashboard_never_learns_about_mujoco`. It covers `review_server`'s whole relative-import closure and `review_static/*.js`, and it fails if that closure goes vacuous.
  - `rollout_bake_integration.py` became `rollout_review_integration.py`. It still writes a trace from a live `cadexd`, then reads it through the dashboard's own `_first_frame_placements` and `_placement` on every frame.
  - In `test_project_docs.py`, the three `mesh_agent`-reading or GUI-leg-table tests were replaced by two: one pins that the GUI-attached mode is retired, and one checks that no `cli/cadex_cli` file names a `shell/` path, `mesh_agent` or `CADEX_BLENDER_EXECUTABLE`.
- ADR-201's GUI-attached mode is retired:
  - The project `ARCHITECTURE.md` scaffold no longer gives Rebuild Model/reopen guidance.
  - `docs/CLI.md` §2's GUI section and leg table became one paragraph naming the dashboard, and the §5 lock note was trimmed.
  - Comments in `agent.py` and `walk.py` were updated to match.
- Minimal command fixes in `README.md` and `AGENTS.md` (412 lines now, from 432), plus the renamed integration's mentions in `ARCHITECTURE.md` and `MUJOCO.md`.

## Why

This is the critic's named unit: horizon rung 2, the shell disable commit, serving S1 (`sunny-clover-3750`), the top-priority criterion. I followed the critic's scope: shell/ kept on disk, `mesh.blender` and Codex/pi left for rung 3, and `ENABLE_TOOL_SEARCH` left as an A1 item without fixing it. I made one deviation, which widens the scope: `test_project_docs.py`'s shell-reading tests pinned the GUI-attached mode's documentation. Rewriting those tests honestly meant retiring that mode in the scaffold and in `docs/CLI.md` in the same commit. Removing only the pins would have left unpinned claims about a shell that no longer builds. I left `test_licensing_compliance.py`'s shell scopes in place, because those files still exist on disk. Restating them is the delete commit's job, as the charter's medium rung 1 says.

## Method

1. Grepped pixi.toml, package/, CMake, CI, tools/, and both test suites for `shell/`, `mesh_agent`, `build_app`, `CADEX_BLENDER_EXECUTABLE` and `.blend`. No CMake file outside `shell/` references them, and neither does anything in tools/.
2. Computed the dashboard's import closure (`review_server` → browser, engine, evaluate, export, film, protocol, review_record, smoke, studio, train, video). It has no mujoco or CadexDynamics import. `evaluate_runner` imports CadexDynamics, but it runs as an engine-interpreter child and is outside the closure.
3. Ran `rollout_review_integration.py` against the real built engine on sb1x. The trace had 52 frames and components base and swing. Base did not move. Swing went from [100, 0, 150] to [67.82, 0, 76.51] with a quaternion change, so `moved: true`. Output ended `OK`.
4. Ran `pixi run test-engine`, then `CUDA_VISIBLE_DEVICES="" pixi run python -m pytest cli/tests -rs`.

## Result

What is true now:
- No pixi task, `package/` script, CI step, CMake rule or test reads `shell/`. One exception remains: `test_licensing_compliance.py`, which deliberately audits the shell files still on disk.
- `test-engine`: **2598 passed, 61 skipped**. The 61 matches an earlier 2543/61 run's skip count. The skips are the gated ones (MJX, and the real Blender recipe worker).
- `cli/tests` with the GPU hidden: **1290 passed, 1 skipped, 1 failed**.
  - The skip is `test_review_server.py:851`, which needs `CADEX_REVIEW_HOST` set.
  - The failure was `test_video.py::test_render_refuses_invalid_inputs_without_touching_training[encoder-studio]`. It read the stand-in trainer's heartbeat file mid-`write_text`, so the content was an empty string. That is a pre-existing race unrelated to this diff, which touches no video code. It passed 30 of 30 on three reruns of `-k refuses_invalid`.

I did not rebuild or stage the engine, and I did not run the packaged lifecycle gate. Nothing in the protocol, the payload or `src/Mod/cadex` engine modules changed: only tests, and CLI comments and scaffold text.

For the next iteration:
- **The `test_video.py` heartbeat race is a known flake.** It writes with truncate-then-write, so a reader can see an empty string. It is worth a small fix: make the reader tolerate `''`, or write atomically.
- **Remaining S1 work:**
  - rung 3: retire `mesh.blender` and `test_blender_recipe.py`, and the Codex/pi backends;
  - then the delete commit: `git rm shell` (which also removes the 4 `shell/lib` gitlinks and their `.gitmodules` entries), plus the licensing restatement (`SPDX_SCOPES` shell rows, `inherited-modifications.json`, `PROVENANCE.md`).
- **Live docs still describe the shell** (BLENDER*.md, `cadex-release-packaging.md`, `ASSEMBLY-VISIBILITY-AUDIT.md`'s `build_app.sh exec`, the `training/` and `analysis/` READMEs, and others). That is R1's job.
- **There is no `app` task now.** D1 defines the dashboard entry.
- **A1 item:** the shell set `ENABLE_TOOL_SEARCH=false` (ADR-163). Whether the CLI turn needs it is unmeasured, and I did not fix it.
- **`witty-spark-2613` ("Three modes, one shape")** loses its GUI-attached limb. The headless and remote limbs are unchanged.
- The tail now holds 2 unreconciled records.

Dispatch closed: 1 unit — shell/ disable commit (ADR-495): no pixi task, package script, CI step or test reaches shell/; mujoco guardrail and rollout integration re-pointed at the dashboard; GUI-attached mode retired.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 324b0411b0949d3bbf293ee79befbc9f706ef57e

## State Impact

- target: sunny-clover-3750 — disable commit landed (324b0411, ADR-495): pixi shell tasks, package/app/build_app.sh and make_app_icon.py, the CI app job and every shell-reading test except the licensing audit are gone or re-pointed; test-engine 2598 passed/61 skipped, cli/tests 1290 passed/1 skipped/1 pre-existing flake. Still open: mesh.blender + Codex/pi (rung 3), the delete commit with licensing restatement, live-doc references
- target: witty-spark-2613 — the GUI-attached mode (ADR-201) is retired with the shell (ADR-495): scaffold and docs/CLI.md no longer describe it and its mesh_agent pins are replaced; the criterion's GUI limb is moot, headless and remote limbs unchanged
- target: shy-crane-2573 — disabled (ADR-495): no pixi task, package script or CI job builds, launches or gates the shell; tree still on disk pending its delete commit
