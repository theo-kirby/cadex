---
node_id: 99d8b1ab-1c54-5eb7-b79b-2010a124489b
slug: proud-valley-6103
title: Performance audit of large creature builds; inspect pages from one join, restore measures no fit (ADR-630)
created_at: '2026-10-10T12:06:05+00:00'
parents:
- small-brook-2395
summary: ''
---
## What

Performance audit of large creature assemblies after the 2026-10-09 Codex/GPT-6-Astra runs timed out at 300 s, and the fixes in ADR-630: inspection pages served from one join per accepted report, and a restore pass that measures no fit. Write-up: `docs/PERFORMANCE-AUDIT.md`.

## Why

Agents on `castra-deinonychus` (290 components, 41,905 pairs, 65 MB report) and `castra-leopard` saw `timed out awaiting tools/call after 300s` on `write_script` (accepted ~85 s in), then on the queued `inspect`/`look`; a read-only status script (open with a 900 s budget, then anatomy and fit) ran 36 min and was killed.

## Method

Copies of the four projects in a scratch directory (originals untouched). cProfile around the worker's `main()` re-running each accepted attempt's `request.json` (warm and `--cold` fit cache), cProfile of a sweep child (unpinned and pinned to one CPU), wall clocks on `open_project`, and request counting/timing around the CLI's `read_fit`, `read_inventory_summary` and anatomy read; the before numbers from a `git archive` of HEAD `587ffd43` as the module dir. Codex timeline from its session rollout.

## Result

- The sink was the bridge's post-build fit read: `read_fit` pages `inspect scope=clearance` 50 rows a page, 5,942 pages on the deinonychus, and every page re-parsed the 65 MB report and re-joined all pairs: ~0.48 s a page, ~48 min (4,821 pages measured in 2,333 s). Leopard: 2,419 pages, ~1,020 s. The worker build itself is 58 s warm, 130-143 s cold (static fit 56 s cold, sweep 27 s, 290 incremental joint solves 17-19 s, part build 15 s, tessellation 10 s); restore 52 s warm, 133 s cold.
- After ADR-630: deinonychus fit read 12.2 s (2 ms a page, identical verdict and 65 failing pairs), leopard 5.8 s; cold-cache open 133 s -> 43 s; the status script's job >36 min -> 57 s.
- Timeout mismatch: Codex's 300 s tool timeout equals the engine's default 300 s budget, and the reply comes after worker + publication + reads; `CadexdClient`'s 900 s is not enforced while the engine is silent (blocking `readline`). Documented in `docs/CLI.md` §2a.
- Dead end, backed out: counting the sweep's pair budget after the box cull sweeps the 15/21 (16/18) joints refused today, but every complete joint republishes all 41,905 pairs: cold build 143 -> 270 s, next build 21/21 swept and a 191 MB report. Must land with publishing only moving sweep rows (audit R1).
- Tests on the final tree: engine suite 2780 passed, 67 skipped; CLI suite 1249 passed, 11 skipped. No C++ change; the dev-tree engine loads src/Mod/cadex directly, so `pixi run build-engine` was not run (its install step writes into the shared pixi env).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-ada3aebdae9fade26
- commit: e594dfffbdbc33555f8e57e099ef0702831ebbf6

## State Impact

- target: wild-horizon-5461 — the build reply's fit read on a 290-component assembly falls from ~48 min to 12 s: inspect pages are served from one join per accepted report (ADR-630); a client tool timeout must outlast the engine budget plus the reads
- target: forest-wind-0342 — the restore pass measures no fit when the pinned accepted attempt is on disk and the working revision is the accepted one; cold open 133 s -> 43 s on castra-deinonychus (ADR-630)
- target: curious-quill-9036 — negative: on 290-component creatures 15 of 21 joints are refused by the sweep pair budget, which counts moving pairs before the box cull; counting after it sweeps them but triples the report (191 MB) because complete joints republish every rigid pair, so it waits on publishing only moving rows (docs/PERFORMANCE-AUDIT.md R1, R2)
