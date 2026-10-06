---
node_id: 87cefe0b-f85d-5de9-80b4-11899c677307
slug: lucky-shade-9428
title: F2. A run reads as what happened to it
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **F2. A run reads as what happened to it.** A run stopped through `train_stop`, or `loop.request_stop` with a reason, reads as **stopped** with that reason in `/api/project`'s stage and on the page; a walk killed without a stop request reads as **failed**; tests cover stopped, killed, finished and crashed through both `train_start` and `cadex walk` [rec: light-mist-9160]. The human owns the checkbox.

**Evidence complete, awaiting the owner's tick** [rec: true-ridge-9252] (code in commit `1ec21fa3`, ADR-559; the charter's "ADR-558" for this work went to F1). Reconcile judgement: status `working`.

- Stopped on request (`train_stop`, `request_stop`, or a walk's SIGINT/SIGTERM) → `stopped` with its reason. Killed with no request → `failed`, "killed or crashed"; this is detected by a released `walk.lock`/`supervisor.lock` flock (`review_record.run_process`). Finished → `ok`. Crashed → `failed` with the trainer's error [rec: true-ridge-9252].
- Tests in `test_loop.py`, `test_walk.py` (including a real SIGKILLed `cadex walk`), and two Chromium tests in `test_review_overlay.py`. Reverting only the supervisor mapping makes the loop tests fail (2 failed) [rec: true-ridge-9252].
- Gates: test-engine 2594 passed / 58 skipped; CLI suite 1188 passed / 1 skipped (GPU hidden). The change is `cli/` only, so the packaged gate does not apply [rec: true-ridge-9252].
- **Assumption carried for the owner** (ADR-559): a walk has no `train_stop`, so its stop request is Ctrl-C/SIGTERM and the reason is the signal's name. A supervisor terminated by a signal with no reason still reads `interrupted` in `train_status` and failed on the page [rec: true-ridge-9252].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-f2-run-reads-as-what)
- true-ridge-9252 — ADR-559 verified: endings tested both ways, fails without the fix, both suites green; pending the owner's tick
