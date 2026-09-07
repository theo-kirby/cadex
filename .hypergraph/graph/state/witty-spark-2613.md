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

Charter criterion: **Three modes, one shape.** The walk runs headless (exercised), with the GUI attached (documented, not exercised while the headless-only constraint holds), and with training on a remote machine (the handoff is documented and scripted, not executed while the local-only constraint holds). The loop's steps and artifacts are the same in all three. Declared target `gap-three-modes-one-shape-walk` [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the same criterion, unticked, and its ladder places "the walk's third mode: the remote handoff, scripted and documented, not executed" on the medium rung [rec: modest-summit-8554].

- **Headless, exercised — now including from `--prompt`**: `cadex walk` qualified on the repo-owned toy (ADR-199) [rec: shy-cabin-0798]; exercised again in nt3 on both example mechanisms under the charter's guards (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs) with peaks about 1 GB and walls under 16 s [rec: misty-rain-9048]; and then twice from a prompt on agent-designed mechanisms, the second at 1.115 GB peak and 189.4 s wall [rec: placid-sky-7374]. Tracked in detail on `crisp-reef-5607`, now `working`.
- **Remote training, scripted and not run** (ADR-200, commit 5143099c) [rec: green-delta-7130]: `--remote` on `cadex train` and `cadex walk` puts the train leg on the box through `training/remote_train.sh` (ADR-089) in place of the venv's interpreter, and nothing else moves: the bundle and model are exported into `DIR/train`, the policy comes home to `DIR/train/<name>.cxpolicy`, the receipt is the same last JSON line, and the store, the digest edit, the verified rollout and `review.json` cannot tell the modes apart. The returned file is verified against the receipt's sha256, and a dispatcher `FAIL:` reaches the envelope's `error`. Offline-tested against a stand-in dispatcher with the real script's argv contract, plus `cadex train --remote --put` end to end against the real engine: 134 CLI tests, no skips. **Not executed**: no dispatch, no ssh, no GPU run.
- **The project's documents state the mode** (ADR-200 follow-up, commit 8c1ff05f) [rec: wild-marsh-9611]: the `ARCHITECTURE.md` scaffold carries a `## Training` section the agent fills in — the mode, the statement that artifacts land at the same project-relative paths in both modes, and the cold-run limit; a `train --remote` row's What column ends in `(remote)`. A test in `cli/tests/test_project_docs.py` pins the sentence in `docs/CLI.md`. Full CLI suite 136 passed, no skips.
- **GUI attached, documented only** (ADR-201) [rec: red-comet-9710]: the same terminal `cadex` commands run beside the open `.blend`, with the same project documents and artifact paths. `_engine_session` holds `.cadex-cli.lock` for one command and releases it before the `PROGRESS.md` row and project commit; the shell takes no lock, so ownership is sequential by convention. Rebuild Model or reopening refreshes source, specs and values from the accepted project. The in-app agent has Mesh tools only, so the walk and project-doc maintenance remain the CLI's or a person's.
- **Refresh before the next GUI edit is required** (ADR-204) [rec: still-badger-2386]: real two-engine probes did not reproduce the earlier overwrite claim; dormant revision adoption and replay are removed defensively, stale script/parameter mutations keep their guard and return Rebuild Model/reopen guidance. 138 CLI tests, the shell build and the final headless bundle gate pass.

**Whole-walk artifact parity is verified offline.** Independent local and `--remote --allow-cpu` toy walks use the real engine and CPU trainer, with a test-only dispatcher standing in for remote transport. They produce identical relative output file sets, verified stored policy bytes and digests, rollout traces, committed review and project documents, and comparable numeric PROGRESS rows with the remote marker only on remote training. The shared mode-artifact table is linked and pinned to the project scaffold. Targeted parity test: 1 passed; full CLI gate: 148 passed, no skips [rec: gilded-basin-9946].

Reconcile judgement: `working`, folding the explicit MET verdict against the criterion's exact wording. Headless prompt walks are exercised; GUI attachment is documented and unexercised; remote handoff is scripted and documented, with no actual dispatch. The offline parity audit supplies the missing whole-walk evidence, so the stated criterion has no remaining gap. This does not establish remote transport reliability or concurrent GUI mutation safety [rec: gilded-basin-9946]. Sequential use and refresh before GUI edits remain required [rec: still-badger-2386].

## Negative knowledge

- [scope: stale shell mutations and concurrent project writes | confidence: high | evidence: still-badger-2386] Real-engine overwrite was not reproduced. Dormant replay is removed and stale guards are retained; Rebuild Model or reopen is required before GUI edits resume. Simultaneous acceptance/rebuilds remain un-serialized and require sequential use.
- [scope: a warm start with `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg: `remote_train.sh` copies two files out and the `--init-from` policy is not one of them, so the remote leg trains cold. Carrying the pair is a change to the dispatcher and its own unit.
- [scope: `--detach` through the walk | confidence: medium | evidence: green-delta-7130] Not passed through: a walk waits for its leg; a long run is dispatched by hand and continued from `cadex asset --put`. `--timeout` ends the local ssh, not the run. The CLI reads none of `.remote.env`, keeping ADR-089's fail-loud shape.
- [scope: the scaffold writing the training mode as a value | confidence: medium | evidence: wild-marsh-9611] Not done: the scaffold is written once on first visit and never overwritten, and a project can be trained both ways over its life, so the section is a template the agent fills in and the per-row `(remote)` marker records which mode a number came from.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- shy-cabin-0798 — ADR-199: the headless mode exercised on the toy
- green-delta-7130 — ADR-200: the remote-training handoff scripted around remote_train.sh, offline-tested, never dispatched
- wild-marsh-9611 — ADR-200 follow-up: the project-doc scaffold names the training mode, the shared artifact paths and the cold-run limit, pinned to docs/CLI.md
- red-comet-9710 — ADR-201: GUI-attached walk and lock scope documented; scaffold/doc wording pinned; false shell file-tools claim corrected
- grand-fjord-0624 — earlier source-only retry concern and refresh requirement; the overwrite evidence is superseded by still-badger-2386
- still-badger-2386 — ADR-204: corrects overwrite evidence, removes dormant retry, verifies explicit refresh recovery and preserves concurrency limits
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked; remote handoff stays on the medium rung
- misty-rain-9048 — headless mode exercised again on this machine under the charter's guards; GUI and remote modes stay documented-not-exercised
- placid-sky-7374 — headless mode exercised from a prompt under the guards (1.115 GB peak, 189.4 s wall); GUI-attached and remote modes unchanged, documented-not-exercised
- gilded-basin-9946 — criterion MET under its stated limits; whole-walk local/remote-flag CPU stand-in artifact parity and scaffold table verified; CLI gate 148 passed
