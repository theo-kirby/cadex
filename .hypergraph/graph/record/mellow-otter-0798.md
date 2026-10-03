---
node_id: 8e38d09b-029d-5430-a2b3-dd794ebacca7
slug: mellow-otter-0798
title: 'orun2 D3: Ouroboros runs listed beside the projects with each iteration''s critic verdict (ADR-513)'
created_at: '2026-10-03T21:58:12+00:00'
parents:
- proud-quill-5791
summary: ''
---
## What

D3's first unit: `cadex app` lists the Ouroboros runs of a runs directory beside the projects, and each run has a read-only page at `/r/<run>/` with its iterations, newest first, the critic's verdict for each, its reason, what it saw done, its message to the next iteration (folded), and the iteration's commit SHA. Commit `4decd8d0`, ADR-513, `docs/DASHBOARD.md` §27, `docs/CLI.md` row.

## Why

The critic's message named this unit as D3's first: D3 is the highest-ranked fully open criterion (D2 is evidenced; A1's remainder ranks after D3). I did what it asked, with one deviation: besides `review_server.py` and `review_static/`, `cli/cadex_cli/__main__.py` gained a `--runs` flag and `runs_directory()` (`--runs`, then `CADEX_RUNS`, then the checkout's `.ouroboros/runs`), because the server must be told where the runs live and `pixi run app` should show this repo's runs with no flag. No new write path, no new dependency.

## Method

- `OuroborosRuns` in `review_server.py`: reads exactly four files of a run (`run.yml` top-level scalars line by line, no YAML parser; `status.json`; `iterations.jsonl`; `critic.jsonl`), fresh per request, folding actor/commit/critique rows and critic verdicts into one entry per iteration; malformed lines counted in `skipped_lines`. Routes: `GET /api/runs` (`cadex-ouroboros-runs-v1`), `/r/<run>/` (run.html, run.js, review.css only), `GET /r/<run>/api/run` (`cadex-ouroboros-run-v1`); `/r/<run>` redirects. Run names must be plain tokens naming a directory holding `iterations.jsonl` or `status.json`.
- `projects.html`/`projects.js` gain a **Runs** card; new `run.html`/`run.js` draw the iteration grid with verdict badges in the existing tones.
- Committed fixture run `cli/tests/fixtures/ouroboros_runs/fx1/` (4 files: a housekeeping continue, a reject with must_fix, a pending iteration, one malformed line).
- Six new tests in `cli/tests/test_app.py`: listing (newest first, tallies, status-only run), per-iteration fold, a live verdict appearing on the next read, every non-page file (decoy transcript included) 404s and nothing is written into the run dir, absent directory = empty list, the `--runs` defaults, and a headless-Chromium test from the index's Runs card to the run page's rows, badges, reason and folded reply.

## Result

- `pixi run test-engine`: 2593 passed, 56 skipped. `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: 1359 passed, 1 skipped (the new browser test ran, not skipped; `test_app.py` alone 14 passed).
- True now: the dashboard lists Ouroboros runs beside projects and shows each run's iterations and critic verdicts, read-only from `.ouroboros/runs/<run>/`. D3 still open: the charter criteria per run, artifacts the run's records point to (renders, reports, probe pages), the run branch, CLI agent turns as runs, and orun1's `docs/probes/orun1/` rendering from the repo alone.
- Note: `docs/DASHBOARD.md` line ~41 still says the server "answers GET and HEAD only", stale since D2's writes; left for R1's doc pass.
- Reconcile tail is now 1 record.

Dispatch closed: 1 unit — Ouroboros runs listed beside projects with per-iteration critic verdicts at /r/<run>/ (ADR-513)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 4decd8d021dc541f89f392b47814d610e34d61ac

## State Impact

- target: swift-nest-0229 — first half evidenced: cadex app lists Ouroboros runs read-only from .ouroboros/runs/<run>/ beside projects, each run at /r/<run>/ with its iterations and critic verdicts (ADR-513, commit 4decd8d0, browser-tested); still open: charter criteria and record-linked artifacts per run, CLI turns as runs, orun1 probes rendering from the repo
