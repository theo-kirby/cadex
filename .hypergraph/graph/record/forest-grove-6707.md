---
node_id: 890ba3f5-0680-53ed-9645-591292f385f6
slug: forest-grove-6707
title: 'orun5 long-term: fresh project readable from first tool call (0.11 s), REPORT 10.3 closed; reconcile deferred'
created_at: '2026-10-08T04:17:22+00:00'
parents:
- glad-valley-4220
summary: ''
---
## What

Measured the long-term defect "a project reads 'not found' until its first script" end to end, on a real `cadex mcp` and a real `cadex app`, and closed REPORT §10.3 with the numbers. Added the probe as `docs/probes/orun5/fresh_project_probe.py`. Rewrote the REPORT's done-claim paragraph so the tail it names is true.

## Why

The critic asked for a reconcile pass first (fold tidy-badger-2182 and glad-valley-4220, advance the mark, regenerate views), then the done claim, then a measurement unit for an open §10 defect. **Deviation:** this iteration's dispatch forbids the hypergraph-reconcile skill, `hypergraph update`, state-node writes and STATE.md edits in a work iteration "no exceptions", and says the next unit is a horizon-ladder rung, never a reconcile. So I did not reconcile. I took the critic's follow-on unit instead, the long-term rung 3 measurement. I chose "not found" over the checkpoint stall because it needs no GPU and no machine lock, and it gives a deterministic answer in one unit. The tail is now three records (tidy-badger-2182, glad-valley-4220, this one), and a reconcile pass must fold them.

## Method

`fresh_project_probe.py` starts `cadex app --projects <tmp> --port 0` and `cadex mcp --project <tmp>/orun5-fresh` (the directory does not exist). It sends MCP `initialize`, `tools/list` and one `tools/call describe_api`, then closes stdin. It never writes a script. It probes `/api/projects` and `/p/orun5-fresh/api/project` at each stage and lists the files on disk. Run twice, under `pixi run python`, from `f172085e`.

## Result

The probe ran twice with the same result:

- **Before the server starts, after `initialize` and after `tools/list` (0.00–0.05 s):** nothing is on disk. The index omits the project and `/api/project` is 404 `not found`. No agent has touched the project yet, so this is correct.
- **After the first tool call (`describe_api`, 0.06 s):** the project holds `review/activity.jsonl`, `.cadex-cli.lock`, `.git`, `PROGRESS.md`, `DECISIONS.md` and `ARCHITECTURE.md`. At 0.11 s it is listed, and `/api/project` returns 200 with `accepted.available: false`, "no script.json".
- **After `cadex mcp` exits:** the same.

ADR-575 holds end to end, and the defect is resolved with nothing left to fix. REPORT §10.3 now says so. The verified date is 2026-10-08 at `f172085e`.

The change is docs and one probe script only. No code under `src/`, `cli/` or `training/` changed. `test_licensing_compliance.py` passes (11 passed, 1 skipped). No orun5 report test pins the REPORT.

**Concern for the next iteration:** the tail stands at three unreconciled records. The critic's reconcile must run as a reconcile pass, not a work iteration. The REPORT's last paragraph names all three. The trainer's checkpoint stall (§10.2) is still unmeasured, and it is the last open long-term defect. It needs the GPU and the machine lock.

Dispatch closed: 1 unit — fresh-project "not found" measured end to end: readable at the first tool call (0.11 s), REPORT §10.3 closed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: f172085e09a554b0b1aed47cad135ea7bdec1d27

## State Impact

- target: grand-otter-5246 — REPORT §10.3 closed by measurement: a fresh project is listed and returns 200 at its agent's first tool call (0.11 s), never before; fresh_project_probe.py reproduces it
- target: jolly-loom-0622 — ADR-575 re-measured end to end on orun5 (real cadex mcp + cadex app): 404 until the first tool call, 200 with 'no script.json' from 0.11 s
