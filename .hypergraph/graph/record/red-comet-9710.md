---
node_id: 595b5f06-ac31-5308-b348-0a71349f22e1
slug: red-comet-9710
title: 'The GUI-attached walk documented from the client code: lock scope, no shell lock, on-disk revision guard, Rebuild Model or reopen; the file-tools claim corrected (ADR-201)'
created_at: '2026-09-06T20:05:08+00:00'
parents:
- golden-mist-0498
summary: ''
---
## What

The GUI-attached lifecycle walk is documented against the client code, not a launch (ADR-201, commit on this node). `docs/CLI.md` §2 gains the paragraph the plan asked for: ownership is by time and the lock is the CLI's — `_engine_session` holds the advisory `flock` on `.cadex-cli.lock` for one command and releases it before the `PROGRESS.md` row and the project commit; `cadex walk` holds none itself, each leg does; **the shell takes no lock** (nothing under `shell/` names the file) and its `cadexd` child lives from the first engine request until `on_file_changed` → `close_all` or quit. Overlap is caught on write: the engine guards every write against the on-disk `script.json` (`prepare_project_candidate`), refuses a stale revision as `STALE_PROGRAM_REVISION`, and the shell's `Lifecycle.poll` retries once against the reported revision. The shell observes an accepted run through Rebuild Model (re-runs the stored source from disk, adopts specs/values/source), through reopening (`load_post` → `queue_open`, ADR-186), and never through the re-accept box (ADR-187). The in-app agent runs with `--tools ""` and Mesh tools only, from a temp dir: no shell, no file tool, so it cannot run the walk or edit the project docs. Same legs, same three documents and domain docs, same project-relative artifacts (`runs/<name>/train/`, `rollout/`, `review.json`, the `PROGRESS.md` row). §5 states the lock's scope; `docs/MUJOCO.md` §7c row 11 is rewritten; `docs/ROADMAP.md` ticks the mode as documented; ADR-201 appended. The `ARCHITECTURE.md` scaffold's `## Training` section gains the one sentence the doc names, and a new test in `cli/tests/test_project_docs.py` holds the sentence and the paragraph together.

**Corrected, because the code won:** `docs/CLI.md` and the scaffold's module docstring both claimed a shell-attached agent has file tools of its own and edits the three documents directly. `backend.py` disables every built-in tool on purpose. Both sentences now say the docs stay the CLI's and a person's with the GUI attached, and the test refuses the old wording.

## Why

Short unit 1 of the plan (`golden-mist-0498`) and the overseer's message: the last open mode of *three modes, one shape* (`witty-spark-2613`, mission 2), with documentation as the authorised evidence under this run's headless-only constraint. The overseer also asked for a maintainer pass first; it had already happened (commit 22853520, STATE.md reconciled through `wild-marsh-9611`, tail one node — the planner's own bet), and a reconcile is forbidden in a work iteration, so the unit went straight to the doc. Assumption, written here rather than asked: "the walk with the GUI attached" means the same `cadex` commands run from a terminal beside the open `.blend` — the only reading the code supports, since the in-app agent has no shell; §7c row 11's old "the in-app agent, which has a shell" was wrong and is replaced.

## Method

Read `cli/cadex_cli/session.py`, `__main__.py` (`_engine_session`, `main`, `_record_progress`, `_commit_run`), `walk.py` (`run_leg`), `shell/scripts/startup/mesh_agent/cadex_backend.py` (`project_root`, `on_file_changed`, `close_all`, `queue_open`, `_open_pump`, `locked_out_project`, `reaccept_stored_script`, `begin_rebuild_model`, `Lifecycle.poll`), `backend.py` (`--tools ""`, `--allowedTools`, the temp workdir), `__init__.py` (`_load_post_handler`) and `src/Mod/cadex/CadexScriptedRuntime.py` (`prepare_project_candidate`, the on-disk guard). Grepped `shell/` for the lock name: no hit. Wrote the paragraph from those, fixed the two wrong sentences, added the scaffold sentence and the test, rewrote §7c row 11, ticked ROADMAP, appended ADR-201. Ran `cli/tests/test_project_docs.py` (one wrap-sensitivity fix to the new test) and the full CLI suite.

## Result

`pixi run python -m pytest cli/tests`: 137 passed in 114 s, no skips, real engine (was 136). No engine, protocol, payload or `shell/` change, so no other gate applies. No GUI launched; nothing dispatched; the GPU box untouched. One runtime leg recorded and not taken: the shell holding the same advisory lock while its engine session is open, which would turn the sequential-ownership convention into a refusal — `shell/` work under `mesh_agent/`, its own unit with the gate. The unreconciled tail is two nodes after this one (the planner's bet and this).

Dispatch closed: 1 unit — the GUI-attached walk documented from the client code (lock scope, no shell lock, on-disk revision guard, Rebuild Model / reopen), the false file-tools claim corrected in doc and scaffold, scaffold sentence pinned by a test; CLI suite 137 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 257d1baa8e8c50ebcb4c787c24fd1d701af34562

## State Impact

- target: witty-spark-2613 — the GUI-attached mode is documented from the client code (docs/CLI.md §2, MUJOCO §7c row 11, ADR-201, commit 257d1baa): the same cadex commands beside the open .blend, the CLI's per-command flock released before the PROGRESS.md row and commit, the shell taking no lock so ownership is sequential by convention, an overlap refused as STALE_PROGRAM_REVISION off the on-disk script.json and retried once by the shell, the shell observing an accepted run on Rebuild Model or reopen. All three modes are now closed at the charter's grain (headless exercised, remote scripted, GUI documented). One runtime leg open, not taken: the shell holding the same advisory lock while its engine session is open
- target: calm-peak-5247 — the ARCHITECTURE.md scaffold's Training section states the GUI-attached mode in one sentence pinned to docs/CLI.md by cli/tests/test_project_docs.py; the false claim that the shell-attached agent has file tools is removed from the scaffold docstring and docs/CLI.md (backend.py runs it with --tools "" and Mesh tools only)
- target: chilly-union-8972 — CLI suite at 137 tests (one new, the GUI-mode scaffold/doc pin); docs/CLI.md §5 states the lock is per command and released before the PROGRESS.md row and the commit, and that the shell does not take it
