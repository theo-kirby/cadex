---
node_id: a25a378a-dcaf-55de-8c55-7e29788d61e6
slug: happy-gate-9091
title: 'Engine killed and restarted during real Lark training (ADR-325): D6 receipt, killed-engine exit status in the CLI, operator service restored under its unit'
created_at: '2026-09-13T13:40:02+00:00'
parents:
- easy-badger-5812
summary: ''
artifacts:
- docs/probes/lark-fresh/engine109-evidence.json
- docs/probes/lark-fresh/ENGINE109.md
- docs/probes/lark-fresh/engine_restart.py
---
## What

D6's last undemonstrated fact on Lark — the engine restarted during real training — now has a receipt on the persistent working copy: `docs/probes/lark-fresh/engine_restart.py`, its receipt `engine109-evidence.json` (run `lark109-engine2` on `ot5-lark-copy85`), the narrative `ENGINE109.md`, a guarding test in `cli/tests/test_lark_fresh_evidence.py`, and ADR-325. Two product-side changes rode with it: the CLI client now reports a killed engine's real exit status (`(exit status -9)`, not `None`) with a regression against the real engine in `cli/tests/test_client.py`, and the persistent operator dashboard on port 8765 was moved back under the documented `cadex-operator-review` user unit after being found running as a bare tmux-launched process.

## Why

Criterion D6 (save, reopen and restart preserve the project), the critic's named next unit, and the one D6 gap the state node `clever-field-7845` names as undemonstrated. The critic's first paragraph banned the current plan bet (the clearance-over-rollout-poses item, which belongs to the mg-legs arc and not to this charter) and asked for one criterion and the smallest thing that moves it; the concrete instruction that followed was this exact experiment. I did what it asked, with one interpretation stated rather than assumed: Cadex has no engine daemon — `cadexd` is one process per `./cadex` invocation and the trainer and dashboard open none — so "kill and restart the cadexd engine mid-run, through the public CLI only" is a public `cadex export` whose engine is SIGKILLed while working, followed by the next `cadex export` starting a fresh engine. The kill itself is the fault injection; every start and stop of an engine is the CLI's.

The service restoration was not in the instruction but was a precondition: the documented restart command every probe relies on (`systemctl --user restart cadex-operator-review`) had nothing to act on, and no `Restart=on-failure` applied. It was done with no trainer active, on the same address, port and project (D10).

## Method

Orientation: read `.ouroboros/AGENTS.md`, RESTART96 and its driver, the Wren restart observer, the CLI client's engine lifecycle (`CadexdClient.start/close/_read_frame`), the review server's default-run rule, and the interruption helpers (`TrainerGuard`, `check_page_identity`, `inventory`). Found port 8765 served by PID 325201 in `session-809.scope` with the unit absent (journal: unit stopped at 07:36:58, never restarted; iteration 104 launched the bare process). A dry run with no trainer measured an export at 1.5 s wall, the engine child visible 0.05 s after the CLI started, and a SIGKILL leaving no orphaned worker.

Service: SIGINT to the bare process (0.45 s to exit), `systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure …` with the documented arguments; `/api/project` answered 0.6 s after the stop began (`ot5-lark-copy85`, 13 runs, accepted `6f826037044a…`); MainPID 428532, Restart=on-failure. Receipt `service109-restore.json` in the copy's evidence directory.

Experiment (`lark109-engine2`): export, retain the training view, run record `running`, exclusion guard, trainer in `systemd-run --scope` with `MemoryMax=20G` and `timeout 900`, 100 updates × 1,024 envs, seed 0. At page iteration 4: `cadex export` → engine PID 444248 seen at 0.047 s, one resident worker under it, SIGKILL at 0.455 s → CLI exit 1 at 0.463 s, `ok: false`, `error: "The engine closed its protocol stream. (exit status -9)"`, zero outputs, no `FreeCADCmd`/`CadexGeometryWorker` alive 2 s later. Next `cadex export` → engine PID 444342 (different start ticks), exit 0 in 1.518 s, 28 outputs, accepted revision/digest unchanged, model XML and task bundle byte-identical to the trainer's inputs. Trainer PID 439475 / start ticks 103546924 identical before, across and after, and at all 4,959 guard scans (max gap 0.067 s, no violation). Open page: no navigation; seven newer committed updates (iterations 8–16) shown 0.197–1.388 s after commit with all three histories growing; fresh visits during and after training selected `RUN lark109-engine2`; completion page `completed`/`done`. Training exit 0, 100 GPU updates, peak host memory 5,489,143,808 B under the 21,474,836,480 B cap, policy `9c166417c633…`. 561 earlier `runs/` files byte-identical; accepted identity unchanged; dashboard unit `active` on MainPID 428532 throughout.

Two facts recorded, not hidden: the manifest's `latest_candidate`/`updated_at` move on every engine open, including the killed one (its restore had rewritten them before the SIGKILL), so `script.json` is not byte-identical while the accepted identity is; and the bounded driver, like RESTART96's, never `asset --put`s the policy the record names.

The first attempt, `lark109-engine`, passed its kill/restart/telemetry phases and trained to completion but lost its receipt: I ran a pytest subset on this machine during its completion wait, the driver's own exclusion guard tripped (pytest counts as a trainer by design), and the driver re-raised before saving. Fixed the driver to write its receipt whatever the guard concludes, wrote that run's record as `failed` with the explanation and its saved policy, and repeated cleanly. That attempt also showed the pre-fix CLI reporting `(exit status None)` — EOF arrives before the child is reaped — which is the client fix (`_read_frame` waits up to 5 s for the exit status).

Verification: `pixi run python -m pytest cli/tests -q -x` on final source — **472 passed, 1 skipped in 473.96 s, exit 0** (includes the new engine-death regression against the real engine and the engine109 receipt test); `git diff --check` clean. No engine, payload or shell code changed, so no build, engine suite or packaged gate was run.

## Result

True now: D6 has Lark receipts for save/reopen, dashboard restart during real training (RESTART96) and engine kill/restart during real training (ENGINE109). Port 8765 is served by the `cadex-operator-review` user unit (MainPID 428532, Restart=on-failure) on `ot5-lark-copy85`, 15 runs, and a fresh visit selects `lark109-engine2` (completed); `lark109-engine` is visible as `failed` with its explanation. The CLI names a killed engine's exit status. ADR-325 records the per-invocation reading of "engine restart" and the rule that the operator URL is served by the unit, never a bare process.

Concerns for the next iteration: (1) `write_run_record(policy_name=…)` derives an `assets/<name>` locator whether or not the asset was put — the bounded drivers (RESTART96, ENGINE109) leave it dangling and the panel shows it missing; a one-line `cadex asset --put` in those drivers or a record that only names an asset that exists would close it. (2) The exclusion guard counts pytest as a trainer; never run the CLI suite on this machine while a probe's trainer is active. (3) Same-machine limit as always: no second-device browser test exists or is claimed. No new dependency.

Handoff bet (different criterion from the banned one, as asked): **D10/D8 — make the failed-observation run honest on the dashboard**: `lark109-engine` shows `failed` with telemetry `done` and a saved policy; check the panel explains that combination (training finished, observation did not) and points at the next CLI action, and fix the record writer's dangling asset locator in the same unit. If the owner ticks nothing after this, the remaining structural fact stands: every D1–D11 node carries Lark evidence and only the owner moves the checkboxes.

Dispatch closed: 1 unit — engine killed and restarted during real Lark training with receipt, test, ADR-325 and the operator service restored under its unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 2aaad3311ccee731389078327171c7c06b26705a

## State Impact

- target: clever-field-7845 — D6's engine half now has a Lark receipt on the persistent working copy (ADR-325, docs/probes/lark-fresh/ENGINE109.md, engine109-evidence.json, run lark109-engine2): during a bounded 100-update GPU run a public cadex export had its engine SIGKILLed at 0.455 s (CLI exit 1, 'closed its protocol stream (exit status -9)', no engine or worker left alive) and the next cadex export started engine PID 444342, exit 0, reproducing the accepted revision 6f826037044a…, digest c039961cd41d… and the trainer's model/task bytes; trainer PID 439475/start ticks 103546924 identical throughout 4,959 guard scans; seven committed updates reached the open page in 0.197–1.388 s with no navigation; fresh visits selected RUN lark109-engine2 during and after training; 561 earlier runs/ files and the accepted identity unchanged; dashboard unit active on the same MainPID. Pinned by cli/tests/test_lark_fresh_evidence.py. Recorded limits: script.json's latest_candidate/updated_at move on every engine open including the killed one; the bounded driver names an asset it never puts; same-machine browser only. The first attempt lark109-engine lost its receipt to the probe's own exclusion guard (a pytest run during its wait) and is kept as a failed record with its saved policy.
- target: deep-clover-6012 — Port 8765 was found served by a bare tmux-launched python -m cadex_cli review (PID 325201, session scope) after iteration 104 restarted it outside the stopped cadex-operator-review unit; with no trainer active it was moved back under the documented systemd-run unit (MainPID 428532, Restart=on-failure), /api/project answering 0.6 s after the stop began, same project and 13 runs. ADR-325 makes the rule explicit: the operator URL is served by the user unit, never a bare process. The unit then stayed active on the same MainPID through the lark109-engine2 experiment; a fresh visit now selects lark109-engine2 (completed) among 15 runs, with lark109-engine visible as failed with its explanation.
- target: chilly-union-8972 — ADR-325: CadexdClient._read_frame waits up to 5 s for a dead engine's exit status before raising, so a killed engine reads '(exit status -9)' rather than None; test_client.py pins it against the real engine. docs/probes/lark-fresh/engine_restart.py is the reusable engine-kill/restart driver; drivers now write their receipt whatever the exclusion guard concludes. cli/ suite at head: 472 passed, 1 skipped, exit 0.
- target: crisp-sun-1239 — Iteration 109 did the critic's named unit (D6 engine restart during real training) rather than the banned clearance bet. Every D1–D11 node carries Lark evidence; D6 no longer names an undemonstrated fact. Handoff bet on a different criterion: D10/D8 — make the failed-observation run lark109-engine honest on the dashboard (status failed with telemetry done and a saved policy) and fix write_run_record's dangling assets/<name> locator for policies never put. Standing limits: pytest counts as a trainer to the exclusion guard, so never run the CLI suite while a probe trains; no second-device browser test exists or is claimed.
