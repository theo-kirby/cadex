---
node_id: 24999ced-c15e-59f7-88d3-3792e2cf3b41
slug: swift-nest-0229
title: D3. Autonomous runs are first-class in the dashboard (orun2)
created_at: '2026-10-03T10:54:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **D3. Autonomous runs are first-class in the dashboard.** - The dashboard lists runs beside projects: - CLI agent turns; - Ouroboros runs (read-only from `.ouroboros/runs/<run>/` and the run branch). - Each run shows: - its iterations and critic verdicts; - the charter criteria; - the artifacts its records point to (renders, reports, probe pages). - orun1's review material (`docs/probes/orun1/`) renders in the dashboard from the repo alone. It replaces what `~/orun1-review/build.py` built by hand, which proves the per-run review pages are no longer needed. [rec: winter-stone-5109]

| Item | State | Evidence |
|---|---|---|
| Ouroboros runs listed beside projects | evidenced | `cadex app` shows a **Runs** card; `OuroborosRuns` in `review_server.py` reads four files per run (`run.yml` scalars, `status.json`, `iterations.jsonl`, `critic.jsonl`) fresh per request; `GET /api/runs`; runs dir from `--runs`, then `CADEX_RUNS`, then the checkout's `.ouroboros/runs`; no new write path or dependency (ADR-513, commit `4decd8d0`, browser-tested) [rec: mellow-otter-0798] |
| Iterations and critic verdicts | evidenced | `/r/<run>/` lists iterations newest first with verdict, reason, what the critic saw done, its message on (folded) and the commit SHA [rec: mellow-otter-0798] |
| Charter criteria | evidenced | `/r/<run>/` shows the run's done criteria (id, title, ticked/open, text), read from the run's branch via `git show`, the working tree for the live run (ADR-514, browser-tested) [rec: polished-reef-4161] |
| orun1 material from the repo alone | evidenced | `docs/probes/<run>/` listed in `api/run` and served read-only at `/r/<run>/probes/` (allow-listed suffixes, plain segments, no symlinks, CSP sandbox + nosniff); README drawn by `markdown.js`, images as a gallery; orun1's committed README and 60 heroes render, proven in headless Chromium (ADR-515, commit `2aca3739`) [rec: lean-star-6139] |
| Record-linked artifacts outside `docs/probes/<run>/` | open | not yet built [rec: lean-star-6139] |
| CLI agent turns as runs | open | not yet built [rec: lean-star-6139] |

Declared target: `gap-d3-autonomous-runs-first-class`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: flipped `open` → `working` because four of six items now carry browser-tested evidence; it stays `working` (not `done`) until the remaining two land and the owner ticks it [rec: lean-star-6139].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- mellow-otter-0798 — Ouroboros runs listed with iterations and critic verdicts (ADR-513)
- polished-reef-4161 — run pages show the charter's done criteria from the run's branch (ADR-514)
- lean-star-6139 — run pages serve and render docs/probes/<run>/ read-only; orun1 renders from the repo (ADR-515)
