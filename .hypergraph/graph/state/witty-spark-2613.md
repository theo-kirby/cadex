---
node_id: f9df2f6f-cc2c-5889-b939-f50f5d8d28d0
slug: witty-spark-2613
title: Three modes, one shape
created_at: '2026-09-06T19:18:33+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion: **Three modes, one shape.** The walk runs headless (exercised), with the GUI attached (documented, not exercised while the headless-only constraint holds), and with training on a remote machine (the handoff is documented and scripted, not executed while the local-only constraint holds). The loop's steps and artifacts are the same in all three. Declared target `gap-three-modes-one-shape-walk`; truncated impact wording resolved from the full charter [rec: empty-wolf-3962].

All three modes meet the charter’s stated evidence level, 2026-09-06:

- **Headless, exercised**: `cadex walk` qualified on the repo-owned toy (ADR-199), tracked on `crisp-reef-5607` [rec: shy-cabin-0798].
- **Remote training, scripted and not run** (ADR-200, commit 5143099c) [rec: green-delta-7130]: `--remote` on `cadex train` and `cadex walk` puts the train leg on the box through `training/remote_train.sh` (ADR-089) — `remote_train.sh train <bundle> <out> [--allow-cpu] -- <the same trainer flags>` in place of the venv's interpreter — and nothing else moves: the bundle and model are exported into `DIR/train` where the script looks for them, the policy comes home to `DIR/train/<name>.cxpolicy`, the receipt is the same last JSON line, and the store, the digest edit, the verified rollout and `review.json` cannot tell the modes apart. The returned file is verified against the receipt's sha256, `training.trainer_out` keeps the box's path, and a dispatcher `FAIL:` reaches the envelope's `error`. Offline-tested against a stand-in dispatcher with the real script's argv contract and printed shape, plus `cadex train --remote --put` end to end against the real engine: 134 CLI tests, no skips. **Not executed**: no dispatch, no ssh, no GPU run; what a real box adds (reachability, the trainer-hash check, the device rule) is `remote_train.sh`'s and was not re-tested.
- **The project's documents state the mode** (ADR-200 follow-up, commit 8c1ff05f) [rec: wild-marsh-9611]: the `ARCHITECTURE.md` scaffold carries a `## Training` section the agent fills in — the mode (the venv on this machine, or `--remote` on the box `remote_train.sh` names), the statement that artifacts land at the same project-relative paths in both modes (`runs/<name>/train/`, `runs/<name>/rollout/`, `runs/<name>/review.json`, the `PROGRESS.md` row), and the cold-run limit; a `train --remote` row's What column ends in `(remote)`. A test in `cli/tests/test_project_docs.py` reads `docs/CLI.md` and requires the sentence naming the scaffold's section, so the walk doc and the scaffold are one ticket. Full CLI suite 136 passed, no skips.

**GUI attached, documented only** (ADR-201): the same terminal `cadex` commands run beside the open `.blend`, with the same project documents and artifact paths. `_engine_session` holds `.cadex-cli.lock` for one command and releases it before the `PROGRESS.md` row and project commit; `cadex walk` holds no outer lock. The shell takes no lock, so ownership is sequential by convention. Rebuild Model or reopening refreshes source, specs and values from the accepted project; the re-accept box does not perform this refresh. The in-app agent has Mesh tools only (`--tools ""`), no shell or file tools, so the walk and project-doc maintenance remain the CLI’s or a person’s [rec: red-comet-9710].

**Refresh before the next GUI edit is required.** ADR-204 corrects the earlier source-only overwrite claim: real two-engine probes did not reproduce overwrite because current stale precondition failures omit `model_state`, which the old retry required to adopt a newer guard. Dormant revision adoption and replay are now removed defensively. Stale script/parameter mutations retain their guard and return Rebuild Model/reopen guidance; synthetic newer-guard responses cannot replay, and repeated real-engine refusals preserve accepted metadata until explicit refresh. CLI scaffold and mode docs reflect this; 138 CLI tests, the shell build and the final headless bundle gate pass [rec: still-badger-2386].

Reconcile judgement: `working` retains the criterion's evidence level—headless exercised, remote scripted, GUI documented. Foreign-revision refusal is implemented and tested; shared locking and serialization of concurrent acceptance/rebuilds remain absent, so sequential use remains required. This is not general concurrent-write safety or GUI execution evidence [rec: still-badger-2386].

## Negative knowledge

- [scope: stale shell mutations and concurrent project writes | confidence: high | evidence: still-badger-2386] Real-engine overwrite was not reproduced. Dormant replay is removed and stale guards are retained; Rebuild Model or reopen is required before GUI edits resume. Simultaneous acceptance/rebuilds remain un-serialized and require sequential use.

- [scope: a warm start with `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg: `remote_train.sh` copies two files out and the `--init-from` policy is not one of them, so the remote leg trains cold. Carrying the pair is a change to the dispatcher and its own unit.
- [scope: `--detach` through the walk | confidence: medium | evidence: green-delta-7130] Not passed through: a walk waits for its leg; a long run is dispatched by hand and continued from `cadex asset --put`, as `training/SETUP.md` says. `--timeout` ends the local ssh, not the run. The CLI reads none of `.remote.env`, keeping ADR-089's fail-loud shape.
- [scope: the scaffold writing the training mode as a value | confidence: medium | evidence: wild-marsh-9611] Not done: the scaffold is written once on first visit and never overwritten, and a project can be trained both ways over its life, so the section is a template the agent fills in and the per-row `(remote)` marker records which mode a number came from.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- shy-cabin-0798 — ADR-199: the headless mode exercised on the toy
- green-delta-7130 — ADR-200: the remote-training handoff scripted around remote_train.sh, offline-tested, never dispatched
- wild-marsh-9611 — ADR-200 follow-up: the project-doc scaffold names the training mode, the shared artifact paths and the cold-run limit, pinned to docs/CLI.md
- red-comet-9710 — ADR-201: GUI-attached walk and lock scope documented; scaffold/doc wording pinned; false shell file-tools claim corrected
- grand-fjord-0624 — earlier source-only retry concern and refresh requirement; the overwrite evidence is superseded by still-badger-2386
- still-badger-2386 — ADR-204: corrects overwrite evidence, removes dormant retry, verifies explicit refresh recovery and preserves concurrency limits
