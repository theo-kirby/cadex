---
node_id: e8a582bf-115e-5978-b1f1-e77f980d2b76
slug: stormy-grove-7025
title: 'orun2 D2: accept, reject and restore a revision from the dashboard through cadex revision (ADR-506)'
created_at: '2026-10-03T18:03:06+00:00'
parents:
- noble-glade-0483
summary: ''
---
## What

orun2 D2 item 4: a person accepts, rejects or restores a revision from the dashboard (ADR-506, commit `73224b74`).

- **Engine** (`CadexScriptStore.record_history`, `CadexScriptedRuntime.accept_project_candidate`): each `script_history/history.json` entry now keeps the `values` (params, nets, boards, mounts, cages) and the geometry `digest` it was accepted with. No protocol or `OP_ARG_SPECS` change.
- **CLI** `cadex revision list|accept|reject|restore [SELECTOR] [--note TEXT]` (`cli/cadex_cli/revisions.py`, `__main__.py`). `accept` writes a verdict line into `comments.jsonl` (no engine, no row, no commit). `reject` (the accepted revision only) puts back the one before it. `restore SELECTOR` puts back the one named. Both use the engine's `write_script` with `replace`, then `set_params` with the recorded values, and each one gets a PROGRESS row and a commit. The envelope's `revisions` reports `target/from/accepted/exact/same_geometry`. Verdicts reach the next `cadex -p` the way comments do.
- **Dashboard**: `POST api/revision` runs `cadex revision --project <root> --json [--note=…] <action> [<selector>]` behind the ADR-503 token and Origin check. The selector must be an ordinal or a hex prefix, never a flag. `/api/project` carries the trail. `#revision-panel` has Accept, Reject, a note, and the trail with Restore on each row (`docs/DASHBOARD.md` §21).
- Docs: ADR-506, DASHBOARD §21 and region 0c, CLI.md, ARCHITECTURE.md, and SHELL-PARITY rows (`restore_version`, `cadex_backend.py`, `agent.py` undo, Parameters editor) moved to ported with tests.

## Why

The critic's message for iteration 20: first write the missing records for iterations 17 and 18 (done: `placid-bell-2440` for ADR-504 and `noble-glade-0483` for ADR-505, both with impact on `twilight-aspen-1541`, export and check exit 0, commit `cc76a761` "record: placid-bell-2440, noble-glade-0483"), then build D2 item 4. This unit is item 4, the highest-ranked open D2 item.

**Deviation:** the critic also asked for a reconcile. This iteration's dispatch forbids the hypergraph-reconcile skill in a work iteration with no exceptions, so I did not reconcile. The tail is now 5 unreconciled records (mild-grove-9448, morning-peak-8268, placid-bell-2440, noble-glade-0483 and this one), so a reconcile pass is due next.

## Method

- A scratch project showed what source-only restore does. Rejecting a script edit that followed a slider move put back the old source with today's slider value, which is a different revision. A revision is its source plus its stored values, so the engine history now records the values.
- A stored value cannot be unset (`set_params` merges). So a restore sets any parameter the target left at its default to that default, and reports `exact`/`same_geometry` honestly instead of claiming the same revision.
- Verification, GPU hidden (`CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu`), after `pixi run build-engine`:
  - `pixi run python -m pytest cli/tests`
  - `pixi run test-engine`
  - `pixi run stage-engine`, then `CADEX_ENGINE_ROOT=<payload> pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`

## Result

- **D2 item 4 is evidenced** by the headless-Chromium test against a real engine (`test_browser_accepts_rejects_and_restores_a_revision`). The project has three revisions: the plate, then width 50, then thickness 12. The test clicks Accept (a verdict; nothing rebuilt), then Reject with the note "too thick" (exact revision #2 back, model redrawn 50 mm wide and 6 mm thick), then Restore on row #1 (`same_geometry`, the same digest as #1, redrawn 30 mm wide). A turn started from the page then received all three verdicts ahead of its prompt. PROGRESS has rows for reject and restore and none for accept.
- **Suites:**
  - Engine: 2583 passed, 56 skipped.
  - CLI full run: 1323 passed, 1 skipped (`CADEX_REVIEW_HOST` unset), 2 failed. One failure was mine: phone reading order, because the new panel lacked a CSS `order`. I fixed it, and `test_review_design.py` now passes (136 passed together with the second test below). The other was `test_review_lifecycle.py::test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone`, which got 'RUN sample' where 'RUN second' was expected. It passed alone and in 2/2 reruns of its file. I read it as a load-timing flake unrelated to this unit; if it recurs, the next iteration should look at it.
  - The full CLI suite was not re-run end to end after the CSS fix.
- **Packaged gate:** 24 passed on the restaged payload.
- **Concerns and assumptions:**
  - "Accept" is advisory: it is a verdict the agent hears, and nothing is locked.
  - A reject or restore leaves the intermediate source-only revision in the trail.
  - History entries from before ADR-506 have no values; restoring one keeps today's values and says so.
  - I added no new dependency.
- **D2 now:** items 1 (except image attach), 2, 3 and 4 are evidenced. Still open: item 1's image attach, 5 (section/exploded/collision views and rollout playback) and 6 (export STEP/STL and the concept sheet download).
- **The tail is fat** (5 unreconciled); reconcile is due.

Dispatch closed: 1 unit — D2 item 4: accept/reject/restore a revision from the dashboard through cadex revision (ADR-506), browser-tested against a real engine.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 73224b743499cec7f67fa6962926213aaa6198e7

## State Impact

- target: twilight-aspen-1541 — item 4 evidenced: cadex revision accept/reject/restore (verdicts in comments.jsonl reach the next turn; reject/restore via write_script + recorded values) run by POST api/revision behind the per-launch token; headless-Chromium test against a real engine accepts, rejects (exact revision back) and restores (same geometry) and a page turn receives the verdicts; open: item 1 image attach, items 5-6
