---
node_id: f9df2f6f-cc2c-5889-b939-f50f5d8d28d0
slug: witty-spark-2613
title: Three modes, one shape
created_at: '2026-09-06T19:18:33+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **Three modes, one shape.** The walk runs headless (exercised), with the GUI attached (documented, not exercised while the headless-only constraint holds), and with training on a remote machine (the handoff is documented and scripted, not executed while the local-only constraint holds). The loop's steps and artifacts are the same in all three. Declared target `gap-three-modes-one-shape-walk`; truncated impact wording resolved from the full charter [rec: empty-wolf-3962].

Two of the three modes are in hand, 2026-09-06:

- **Headless, exercised**: `cadex walk` qualified on the repo-owned toy (ADR-199), tracked on `crisp-reef-5607` [rec: shy-cabin-0798].
- **Remote training, scripted and not run** (ADR-200, commit 5143099c) [rec: green-delta-7130]: `--remote` on `cadex train` and `cadex walk` puts the train leg on the box through `training/remote_train.sh` (ADR-089) — `remote_train.sh train <bundle> <out> [--allow-cpu] -- <the same trainer flags>` in place of the venv's interpreter — and nothing else moves: the bundle and model are exported into `DIR/train` where the script looks for them, the policy comes home to `DIR/train/<name>.cxpolicy`, the receipt is the same last JSON line, and the store, the digest edit, the verified rollout and `review.json` cannot tell the modes apart. The returned file is verified against the receipt's sha256, `training.trainer_out` keeps the box's path, and a dispatcher `FAIL:` reaches the envelope's `error`. Offline-tested against a stand-in dispatcher with the real script's argv contract and printed shape, plus `cadex train --remote --put` end to end against the real engine: 134 CLI tests, no skips. **Not executed**: no dispatch, no ssh, no GPU run; what a real box adds (reachability, the trainer-hash check, the device rule) is `remote_train.sh`'s and was not re-tested.
- **The project's documents state the mode** (ADR-200 follow-up, commit 8c1ff05f) [rec: wild-marsh-9611]: the `ARCHITECTURE.md` scaffold carries a `## Training` section the agent fills in — the mode (the venv on this machine, or `--remote` on the box `remote_train.sh` names), the statement that artifacts land at the same project-relative paths in both modes (`runs/<name>/train/`, `runs/<name>/rollout/`, `runs/<name>/review.json`, the `PROGRESS.md` row), and the cold-run limit; a `train --remote` row's What column ends in `(remote)`. A test in `cli/tests/test_project_docs.py` reads `docs/CLI.md` and requires the sentence naming the scaffold's section, so the walk doc and the scaffold are one ticket. Full CLI suite 136 passed, no skips.

**Still open: the GUI-attached mode is not yet documented against the same project contract** — the plan's short unit 3 [rec: green-delta-7130] [rec: wild-marsh-9611]. Reconcile judgement: stays `open` until that document lands; the criterion names all three modes.

## Negative knowledge

- [scope: a warm start with `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg: `remote_train.sh` copies two files out and the `--init-from` policy is not one of them, so the remote leg trains cold. Carrying the pair is a change to the dispatcher and its own unit.
- [scope: `--detach` through the walk | confidence: medium | evidence: green-delta-7130] Not passed through: a walk waits for its leg; a long run is dispatched by hand and continued from `cadex asset --put`, as `training/SETUP.md` says. `--timeout` ends the local ssh, not the run. The CLI reads none of `.remote.env`, keeping ADR-089's fail-loud shape.
- [scope: the scaffold writing the training mode as a value | confidence: medium | evidence: wild-marsh-9611] Not done: the scaffold is written once on first visit and never overwritten, and a project can be trained both ways over its life, so the section is a template the agent fills in and the per-row `(remote)` marker records which mode a number came from.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- shy-cabin-0798 — ADR-199: the headless mode exercised on the toy
- green-delta-7130 — ADR-200: the remote-training handoff scripted around remote_train.sh, offline-tested, never dispatched
- wild-marsh-9611 — ADR-200 follow-up: the project-doc scaffold names the training mode, the shared artifact paths and the cold-run limit, pinned to docs/CLI.md
