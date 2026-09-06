---
node_id: 996f340d-6268-5fda-bb13-c0a33c31d403
slug: restless-harbor-4224
title: 'cadex asset --put and put_asset in the CLI surface: a trained policy comes home headlessly (ADR-190)'
created_at: '2026-09-06T01:37:56+00:00'
parents:
- wise-tooth-2750
summary: ''
---
## What

`cadex asset --put FILE` and `put_asset` in the CLI agent's tool surface (ADR-190): the headless door for a trained policy coming home. The no-model subcommand copies one or more files into the project store through the existing `put_asset` op and reports the store's listing — name, bytes, sha256 — as `assets` rows in the `--json` envelope; with no `--put` it lists the store by following `inspect scope=assets`'s page chain. The agent's tool list gains `put_asset` (last, `source_path` required, `name` optional) with prose that names the four things it carries and says the reply's sha256 is the digest `assembly.policy` requires; the overlay gains one paragraph saying the agent cannot train and naming `cadex export --out` and `cadex asset --put` as the caller's two ends of the leg. No protocol op, no engine change, no `shell/` diff. Commit `c30b53d5`.

## Why

The overseer's message for this iteration named it: "put_asset, the headless policy-install surface the walk needs", and it is item 2 of the ordered frontier on `calm-peak-5247` (§7c). The reconcile it asked for first had already run as the previous commit (`bf4291cf`, STATE.md reconciled through `wise-tooth-2750`, zero unreconciled), and a work iteration may not reconcile in any case. The lifecycle audit (`sweet-light-3396`) found row 5 reachable only over raw NDJSON and found the agent inventing a "`put_asset` CLI command"; the export ADR-189 landed was upstream of exactly this. Choices made without a human: `--put` repeatable rather than positional, because a policy travels with its receipt; the listing as an envelope field rather than a note, because the sha256 is what a pipeline pipes into the next command; **no** `--rebuild` flag, because the rebuild that makes a policy real is the script change naming it, and folding that into the store write would hide the digest the script has to carry.

## Method

Read `tools.py`, `__main__.py`, `bridge.py`, `report.py`, `session.py`, the `link` precedent (ADR-138) and its real-engine test, `cadexd._op_put_asset`, `store_project_asset`, and `CadexInspection`'s page builder. Added `put_asset` to `CLI_TOOL_OPS` with descriptions; a `put_asset` line in the bridge's progress summary; `assets` on `RunReport` (JSON and prose); `read_project_assets` in `session.py` following `next_offset` like `read_script_source`; `command_asset` with usage errors before the engine runs and the engine's refusal as exit 3; the overlay paragraph. Seven tests in `cli/tests/test_asset.py`, five against the real engine. Then the walk itself on a scratch copy of `~/cadex-balance-ns` (never the live project): `cadex export` → `training/cadex_train.py` from the repo's untracked `.venv` → `cadex asset --put` → a sed re-pointing `weights=` and `sha256=` → `cadex script --set` → the exported trace's `policy` block. Docs: `docs/CLI.md` §2, §3, §4; `docs/MUJOCO.md` §7c row 5 and frontier items 2 and 3; ADR-190; a ROADMAP tick under "Later".

## Result

- `cli/tests`: **92 passed** (85 before), 24 s, engine present so nothing skipped. The first listing test failed once because `inspect` pages its value under `path`; fixed by following the chain rather than reading a top-level key.
- The chain on the scratch copy, no NDJSON driver, no staging path read: export 6 files; train 2 it × 8 envs, exit 0, **16.2 s** wall; `asset --put` stored **28 053 B**, sha256 `170ac841…`, listing returned both policies; `script --set` accepted at `758ef975…`; trace `total_reward` **−297.4** for the untrained policy (height −297.0, spin −0.34, torque −0.002) against the rehearsal policy's 1729.9. The one thing typed by hand was the trainer command — §7c item 3, the `cadex train` dispatcher, is now the next rung.
- Not touched: the engine's `INSPECTION_FAILED` frame (item 5), the iterate shape (item 4), the project scaffold (item 6). Every `cadex export` still leaves a fresh attempt directory; still not chased.
- Scratch under `/tmp/nt1-asset-scratch`, outside the repo.

Dispatch closed: 1 unit — `cadex asset --put` and `put_asset` in the CLI surface (ADR-190); §7c row 5 closes, chain 3→7 run headlessly with only the trainer command by hand.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: c30b53d52a574b5d42086d1b0bf98049af3e8b28

## State Impact

- target: calm-peak-5247 — §7c row 5 (policy home) closes: cadex asset --put FILE for a pipeline and put_asset in the agent's tool surface (ADR-190), envelope assets rows carry the sha256; chain 3→7 run headlessly on a scratch copy with only the trainer command by hand (2 it × 8 envs 16.2 s, 28 053 B stored, trace −297.4 for the untrained policy); frontier item 2 done, item 3 the cadex train dispatcher is next; the overlay now tells the agent it cannot train and names cadex export / cadex asset --put instead of guessing flags
- target: chilly-union-8972 — a sixth subcommand, cadex asset (--put FILE repeatable, --name for one; no --put lists the store via inspect scope=assets page chain); put_asset joins CLI_TOOL_OPS; assets is a new optional envelope field; cli/tests 92 passed
