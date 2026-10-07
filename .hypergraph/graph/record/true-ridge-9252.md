---
node_id: 0548969c-f624-578c-8257-5edc90ae6315
slug: true-ridge-9252
title: 'F2 verified: a run reads as stopped on request, failed when killed (ADR-559); both suites green'
created_at: '2026-10-06T09:31:40+00:00'
parents:
- loyal-path-4209
summary: ''
---
## What

F2 is recorded and verified. ADR-559 and its code arrived in commit `1ec21fa3` ("ouroboros #6: no record") with no record node and no gate evidence. This iteration checked that the code covers what F2 asks for, measured that its tests fail without the fix, ran both suites, and wrote this record. A run stopped through `train_stop` or `loop.request_stop` with a reason now reads as **stopped**, with that reason, in `/api/project`'s stage and on the page. A walk sent Ctrl-C or SIGTERM also reads as stopped. A run killed with no stop request reads as **failed**, "killed or crashed", by checking for a held `walk.lock`/`supervisor.lock` flock (`review_record.run_process`). A finished run reads `ok`, and a crashed one reads `failed` with the trainer's error.

## Why

The critic asked for this first: it named commit `1ec21fa3` as unrecorded work and set F2 (`lucky-shade-9428`) as the next unit, with D1 to wait until F2 is recorded. F2 is the second-ranked criterion in the charter. One part of the critic's message was **not done**: it asked for a reconcile, but this dispatch's rules forbid reconciling in a work iteration "no exceptions". I recorded the work instead and left the fold to the reconcile pass (see Result).

## Method

- **Checked coverage** against F2's list, in the tests from `1ec21fa3`:
  - *Through `train_start` (`cli/tests/test_loop.py`):*
    - `test_each_ending_of_a_started_run_reads_on_the_page_as_what_happened` covers four endings through the bridge, each read through `ReviewProject(...).review()["stage"]` and `run.json`: finished reads `ok`; stopped through `train_stop` with a reason reads stopped/stopped with the reason; a supervisor SIGKILLed reads failed, "killed or crashed"; a crashed trainer reads failed with its error.
    - `test_a_running_run_is_read_stopped_and_leaves_its_checkpoint` calls `loop.request_stop(run_dir, "the reward is flat")` directly and asserts `run.json` says `stopped` with that reason.
  - *Through `cadex walk` (`cli/tests/test_walk.py`):*
    - `test_a_walk_that_finished_was_stopped_or_crashed_reads_as_that` covers finished, SIGTERM, SIGINT and crashed.
    - `test_a_walk_killed_mid_training_reads_as_failed` SIGKILLs a real `cadex walk` process mid-training; the run reads failed with `recorded_status: "running"`, and the file is left untouched.
  - *On the page (`cli/tests/test_review_overlay.py`):* two Chromium tests through `browser.py` watch the chip turn from training to failed (killed), and from training to stopped in `--warn` with the reason.
- **Fails without the fix, re-measured:** I reverted only the supervisor mapping in `loop.supervise` (`{"finished": "ok", "stopped": "stopped"}.get(state, "failed")` back to `"ok" if state == "finished" else "failed"`). Both loop tests above then **failed (2 failed)**. I restored the file; `git status` was clean afterwards. ADR-559 records that it measured the same for each half (5 tests each).
- **Gates:**
  - `pixi run test-engine`: **2594 passed, 58 skipped**, exit 0.
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: **1188 passed, 1 skipped** (1082 s), exit 0. No training job was on the GPU.
  - F2 touches only `cli/`, so neither the protocol nor the payload changed, and the packaged gate does not apply.

## Result

**What is true now:**
- F2's behaviour is complete and tested (stopped, killed, finished and crashed, through both `train_start` and `cadex walk`), and both suites are green on `ouroboros/orun4`.
- ADR-559 is in `docs/DECISIONS.md`, and `docs/CLI.md` and `docs/DASHBOARD.md` describe the `stopped` status and the stage.

**Assumption carried from ADR-559 (owner to revise):** a walk has no `train_stop`, so a stop request to a walk is Ctrl-C or SIGTERM, and its reason is the signal's name. SIGKILL is a kill. A supervisor terminated by a signal with no reason still reads as `interrupted` in `train_status` and failed on the page.

**Concern for the next pass:** the unreconciled tail is now 3 records (`civic-stream-8050`, `loyal-path-4209`, this one). That meets the charter's three-record trigger. The critic asked this iteration to reconcile, but work iterations are forbidden to, so the next reconcile pass should fold them. The next work unit is D1 (pan in the 3D viewport).

Dispatch closed: 1 unit — F2 verified and recorded: ADR-559's stopped/killed/finished/crashed endings tested through train_start and cadex walk, fails without the fix, both suites green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 1ec21fa39403eb7df51f62495b3bbb9819e88abe

## State Impact

- target: lucky-shade-9428 — met pending owner tick: ADR-559 (commit 1ec21fa3) reads train_stop/request_stop runs and signalled walks as stopped with their reason, killed runs as failed via a released flock, finished ok and crashed failed; tests through train_start and cadex walk fail without the fix; test-engine 2594 passed, CLI suite 1188 passed (GPU hidden)
