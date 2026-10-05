---
node_id: 2ce53272-c11d-5b0e-a9da-dbbbf6b644fd
slug: forest-walrus-2370
title: 'V4 write half: cadex mcp writes a bounded per-call activity log, read back in /api/project (ADR-549)'
created_at: '2026-10-05T13:24:37+00:00'
parents:
- brisk-dune-8872
summary: ''
---
## What

V4's write half (ADR-549). `cadex mcp` now appends one bounded JSON line per tool call to the project's activity log, `review/activity.jsonl`. `GET /api/project` carries the newest ten entries as `activity`.

Each line has:
- `t`: UTC, to the second.
- `tool`.
- `args`: a summary, never the arguments themselves. A scalar is shown as it is. A string over 40 characters or with a newline is shown only by its length (`source=<3000 chars>`). A list is shown by its size, and an object by its keys (`values={width,thickness}`).
- `outcome`: `ok` or `error`.
- `detail`: the bridge's own one-line summary of the call, else the reply's error.
- `ms`.

`args` and `detail` are cut at 160 characters. Once an append takes the file past 64 KiB, it is rewritten atomically, keeping the newest whole lines within 32 KiB. The log is written in `McpSession.call`, so failed calls and engine-open failures are logged too. Writing never fails the call. The project's git already ignores `/review/` (ADR-194).

New: `cli/cadex_cli/activity.py` and `cli/tests/test_activity.py`. Changed: `McpSession.call` in `cli/cadex_cli/__main__.py`, `ReviewProject.review` in `cli/cadex_cli/review_server.py`, `docs/CLI.md` (the mcp row, the file map, the test table) and ADR-549 in `docs/DECISIONS.md`.

## Why

The critic's message asked for two things first: the missing ADR-548 record (done as the parent record) and suite runs with the GPU hidden. It then named V4, the highest open criterion, as this unit: "one bounded line per tool call … cap tested … don't change `test_project_tool_surface.py` … one test that drives a tool call through `cadex mcp` and reads the entry back from `/api/project`. The overlay line comes after that, as its own change." This unit is exactly that. The page is not touched.

## Method

- Assumption (reversible): I put the log under `review/`, beside ADR-546's revision store, because the CLI already owns that directory and the project's git already ignores it. That is B1's "paths the CLI already owns", and it means the log is never committed to the project's repository.
- Assumption: an object argument is shown by its keys, not its size, because `set_params`' parameter names are what an owner needs to see. A long key list falls back to `{N keys}`.
- Tests, in `cli/tests/test_activity.py`:
  - Arguments are summarised and never logged whole.
  - The cap: 2,000 calls with 500-character sources and 400-character details leave the file at most 64 KiB, every line under 600 bytes, the newest call last and read first, and no scratch file left behind.
  - A missing log, and a torn last line, are reported as absent rather than filled in.
  - End to end, against the real engine: a `cadex mcp` subprocess builds a plate with `write_script`, and is refused `no_such_tool`. Then `/api/project` (served by `review_server.serve`) carries both calls, newest first. The source shows only as `source=<N chars>`, the detail starts `plate (`, and `git ls-files` in the project lists no activity file.
- Measured line sizes: a biped-sized `write_script` line is 232 bytes and a `set_params` line is 135 bytes. So the 64 KiB cap holds roughly 150 to 500 calls.
- Suites run with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`. No training was live, but the GPU was hidden anyway, per the charter.
- No new dependency. Only the standard library is used.

## Result

- **V4's write half is true.** Every `cadex mcp` tool call, failed calls included, lands as one bounded line in `review/activity.jsonl`. The file's cap (64 KiB, rotating to the newest 32 KiB) is tested, and `/api/project`'s `activity` carries the newest ten entries, or `available: false` with a reason.
- `test_project_tool_surface.py` is unchanged: no tool, argument or result field was added.
- Suites:
  - `pixi run test-engine`: 2585 passed, 58 skipped (src unchanged since that run).
  - `cli/tests` with the GPU hidden: 1157 passed, 1 skipped (the private-address smoke, needs CADEX_REVIEW_HOST), exit 0, 15m55s.
- **Open for V4:**
  - The overlay's activity line: the latest entry and how long ago it happened, an expanded list of the last few entries, and "agent idle" after a quiet spell instead of a stale action shown as current. It is the next unit, with a browser test and the DASHBOARD.md rows.
  - P1's route contract will need to list `activity` as a top-level key of `/api/project`.
- The unreconciled tail is now 2 records (the ADR-548 record and this one) on top of what the critic counted. The critic said to reconcile soon. This iteration is forbidden from reconciling.

Dispatch closed: 1 unit — V4 write half: `cadex mcp` writes a bounded per-call activity log, read back in `/api/project` (ADR-549)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: ba015523c54c4c6ec46b29c96a67fdb4e2eae999

## State Impact

- target: rare-beacon-3440 — write half landed (ADR-549): every cadex mcp tool call appends one bounded line (t, tool, summarised args, outcome, detail, ms) to review/activity.jsonl, capped at 64 KiB rotating to newest 32 KiB (tested), git-ignored; /api/project carries activity (newest 10); end-to-end test drives cadex mcp against the real engine and reads entries back; test_project_tool_surface.py unchanged; overlay line still open
