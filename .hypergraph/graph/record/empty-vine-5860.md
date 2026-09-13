---
node_id: 1af45b4e-cab7-52a1-ab75-e44170d04bc2
slug: empty-vine-5860
title: A completed run whose policy was never stored is listed as a problem with the store command; both Lark gaps closed live; bounded drivers store through the CLI (ADR-327)
created_at: '2026-09-13T14:34:19+00:00'
parents:
- lean-orchard-0769
summary: ''
---
## What

A completed run whose policy is retained only under its own `train/` is now a retention gap the reader reports (ADR-327). `read_run_record` lists an `ok` run whose `policy_store` is `unstored` or `digest mismatch` with a retained trainer copy under `problems`, carrying the one command that closes it; `policy_store` gains `store_command` (the bare `cadex asset --project <project-dir> --put <project-dir>/runs/<run>/train/<name>`, with `--name <other>.cxpolicy` on a mismatch, `null` once stored or when nothing is retained). The entry leaves on the poll after the store write with no record rewrite and the run still `completed`; a `failed` run in the same state stays off the list, its row carrying the advice (ADR-326). The two bounded probe drivers (`restart_training.py`, `engine_restart.py`) store the policy through the public CLI before they write the record, so the record names a store copy that exists, and a store failure after finished training records `failed` with an error saying so. Regressions: `test_browser_lists_a_completed_run_whose_policy_was_never_stored_as_a_problem` (headless Chromium, two bounded `ok` runs of the Lark shape, store write seen on the next poll, the other run's gap untouched, fresh visit unchanged) and a reader test covering unstored, digest mismatch, stored, failed-not-listed and nothing-retained. Live receipt on the persistent operator URL: `docs/probes/lark-fresh/policy_store111.py`, `policy-store111-evidence.json`, pinned by `test_lark_fresh_evidence.py`; README and LIFECYCLE (D5, D8 rows) cite it; `docs/CLI.md` reader and dashboard sections updated; ADR-327.

## Why

The critic's named unit, done as asked: D5/D8 (a completed run's result must be retained where the project reads it, and the page must say what to run) and D10 (the persistent page shows explicit gaps rather than a green `completed` with the policy only in the trainer's directory). Chosen over the banned clearance bet. The reader change was made first so the page could name the command, then the page's own advice was followed on the persistent copy for both runs, then the drivers were fixed so the next real bounded run never opens the gap.

## Method

Read the ADR-326 reader, writer, page rendering, the two drivers' record calls and the live `/api/project` over `100.104.232.88:8765` (`lark96-restart` and `lark109-engine2`: `ok`, `unstored`, trainer copy retained, `project_artifacts.policy: missing` from their pre-ADR-326 locators). Implemented the reader rule and `store_command`, updated the two equality tests, added the reader and browser regressions, patched both drivers to `./cadex --project <p> asset --put <policy> --name <name> --json` on success with the envelope's sha256 checked before recording `ok`. Targeted tests green. Restarted `cadex-operator-review` deliberately on the patched reader with no trainer active (MainPID 559912 → 568980; `service111-restart.json` in the copy's evidence directory) and confirmed the served problem entries. Ran the probe: fresh visit selects `lark109-engine2`; for each run the page listed the `policy_store:` problem with the command, the command ran from `/` with `<project-dir>` filled in (exit 0, 0.83 s each), the open page dropped the problem and flipped to `stored` in 0.505 s and 1.012 s with one navigation entry; both `run.json` byte-identical; 601 `runs/` files unchanged; `assets/` gained exactly the two policies with the recorded digests, prior assets unchanged; accepted revision `6f826037044a…` / digest `c039961cd41d…` unchanged; MainPID 568980 before and after; no trainer seen. Full verification: `pixi run python -m pytest cli/tests -q` — **481 passed, 1 skipped in 484.96 s, exit 0**; `git diff --check` clean. Committed as `a0706aec`, then restarted the unit once more on the committed code (568980 → 604845, active, `Restart=on-failure`, no trainer): `/api/project` serves `ot5-lark-copy85`, 15 runs, every policy-carrying run `stored`, no problems anywhere. No engine, payload, shell or dependency change, so no build, engine suite or packaged gate was run.

## Result

True now: every run on the persistent Lark copy has its policy in the project store with its recorded digest and its record untouched; the reader treats an `ok` run with an unstored, retained policy as a problem naming the store command; the bounded drivers store through the CLI before recording. Port 8765 serves the working copy under its unit (MainPID 604845) on the committed code.

Concerns and assumptions: (1) The driver store step is exercised by no real run yet — it is code-reviewed and compiled; the next real bounded run on the copy is its proof, and the reader would list any gap it left. (2) Pre-ADR-326 records still also carry `project_artifacts.policy: missing` until stored; both lines were shown and both cleared on the store write, which is honest but says one thing twice — left as is. (3) The unit was restarted twice deliberately this iteration (before the probe and after the commit), never during training; the store operations themselves left the MainPID unchanged, which is the invariant the receipt pins. (4) Same-machine browser over the private address; no second-device claim. No new dependency. The unreconciled tail is now three records (happy-gate-9091, lean-orchard-0769, this one): the next unit is the reconcile pass, as the critic said.

Handoff: after the reconcile, the long-term rung — repeat the lifecycle from a clean agent-authored project and switch the persistent URL to it deliberately (D10), to expose Lark-fixture dependencies; its first bounded run also proves the drivers' new store step for real.

Dispatch closed: 1 unit — completed runs with unstored policies listed as problems with the store command, both Lark gaps closed live on the persistent URL, bounded drivers store through the CLI, ADR-327.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: a0706aec42baf6eea6695f4f3033b607fa7bd96b

## State Impact

- target: cool-gate-3332 — D8 gains the completed-run retention gap (ADR-327): an ok run whose policy is retained only under train/ is listed under problems with the exact cadex asset --project <project-dir> --put command, cleared on the poll after the store write with no record rewrite; a failed run in the same state keeps its advice on the policy-store row and is not listed. Reader test and headless-browser regression in cli/tests; live receipt docs/probes/lark-fresh/policy-store111-evidence.json pinned by test_lark_fresh_evidence.py.
- target: sharp-union-6036 — D5: every run on the persistent Lark copy now has its policy in the project store with its recorded digest (lark96-restart and lark109-engine2 stored by running the command their own problem line named, from /), both run.json byte-identical, 601 earlier run files and the accepted identity unchanged; policy_store carries store_command, and the two bounded drivers store through the CLI before recording so the next real run never opens the gap (ADR-327).
- target: deep-clover-6012 — The persistent operator URL was verified across the change: cadex-operator-review restarted deliberately twice with no trainer active (559912 → 568980 on the patched reader before the probe, 568980 → 604845 on the committed code after it); the store operations themselves left MainPID 568980 unchanged; /api/project serves ot5-lark-copy85 with 15 runs, a fresh visit selects lark109-engine2 before and after, no problems anywhere and every policy-carrying run stored.
- target: chilly-union-8972 — ADR-327: read_run_record lists ok + unstored/digest-mismatch with a retained trainer copy under problems carrying policy_store.store_command; docs/CLI.md reader and dashboard sections updated; docs/probes/lark-fresh restart_training.py and engine_restart.py run cadex asset --put before write_run_record. cli/ suite at head a0706aec: 481 passed, 1 skipped, exit 0.
- target: crisp-sun-1239 — Iteration 111 did the critic's named unit (D5/D8/D10 retention gap) rather than the banned clearance bet. Three records are now unreconciled (happy-gate-9091, lean-orchard-0769, this one): the next unit is the reconcile pass. After it, the long-term rung: repeat the lifecycle from a clean agent-authored project and switch the persistent URL to it deliberately, which also proves the drivers' new store step on a real run.
