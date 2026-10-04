---
node_id: 0c038c84-27a0-53b7-8cf9-50534da6a41d
slug: polished-reef-4161
title: 'orun2 D3: run pages show the charter''s done criteria from the run''s branch (ADR-514)'
created_at: '2026-10-03T22:22:44+00:00'
parents:
- mellow-otter-0798
summary: ''
---
## What

orun2 D3, second slice: each Ouroboros run's page (`/r/<run>/`) shows the
charter criteria it ran to, read-only, from the run's own branch (ADR-514).
Plus the critic's fix-first: `docs/DASHBOARD.md` §1 no longer claims the
server answers only `GET` and `HEAD`.

## Why

The critic's message: fix DASHBOARD.md's GET/HEAD-only claim first, then on
each run's page show the charter criteria from the run's goal file,
read-only. Both done. The critic also listed orun1's probe pages through `/r/`,
allow-listed record-linked artifacts with a browser test, and CLI turns as
runs. Those were named as later steps ("Then…", "After that…"), and
one-unit-per-iteration keeps them for the next iterations. They are not done.
D3 (`swift-nest-0229`) is the highest-ranked open criterion with work left.

## Method

- `docs/DASHBOARD.md` §1: rewrote the sentence. The page's first controls
  were view controls on GET/HEAD; D2's steering controls write with POST
  behind the per-launch token and the same-origin check (§18), bound to
  127.0.0.1 (§22). Also dropped the future-tense "will each write" sentence.
- `OuroborosRuns` (`cli/cadex_cli/review_server.py`): when the runs directory
  is a checkout's `.ouroboros/runs`, the run's `goal` file (from `run.yml`,
  default `.ouroboros/goal.md`) is read with `git show
  refs/heads/<branch>:<goal>`, then `refs/remotes/origin/<branch>`. When the
  run's branch is the checked-out one (the live run), it reads the working
  tree instead. `criteria()` parses only the checkboxes under `## Done
  criteria`: id, title (bold span, id stripped), ticked, and markdown as
  written. Guards: the goal path must be relative with no `..`; the branch
  must match a plain-ref regex with no `..`; git runs from an argument list
  with a 10 s timeout. `GET /r/<run>/api/run` gains `charter`; `/api/runs`
  does not.
- `run.html`/`run.js`/`review.css`: a Charter card with a "· n of m ticked"
  count, the source line, and one `<details>` row per criterion. The card
  redraws only when the charter JSON changed, so an opened criterion
  survives the 10 s poll.
- Checked by hand against this repo's real runs: orun1 → 6 criteria (F1,
  D1–D4, C1) from `ouroboros/orun1`; orun2 → 8 from the working tree; ot7 →
  F1–F10; ot11 → P1–P4, R1–R3, C1; ot4 → 13 (9 ticked), with its "Later
  criteria" section excluded.
- Tests (`cli/tests/test_app.py`), using a real git checkout fixture built
  in tmp:
  - branch source rather than the later checked-out charter;
  - working-tree source for the checked-out run, uncommitted edit included;
  - a deleted branch gives its reason;
  - nothing written, no branch moved;
  - refusals: a non-checkout runs directory, an escaping or absolute goal,
    an option-shaped or `..` branch;
  - the existing headless-Chromium run-page test extended: count, source,
    badges, fold, and an opened criterion staying open across a real poll
    redraw.

## Result

True now: `/r/<run>/` shows the run's done criteria from its branch.
`docs/DASHBOARD.md` §1 and §27 and ADR-514 describe it.
`cli/tests/test_app.py` is 16 passed, 0 skipped (browser test included).
Full suites: CLI `pytest cli/tests` with the GPU hidden is 1361 passed, 1 skipped; `pixi run test-engine` is 2593 passed, 56 skipped.

Concerns and assumptions for the next iteration:
- Assumption: the run branch is the right source for a finished run's
  charter. The working-tree goal is always the current run's. If Ouroboros
  ever snapshots the goal into the run directory, read that instead
  (ADR-514's reversal).
- `remotes/origin/ouroboros/nt1..nt3` have no local branch; the
  `origin/<branch>` fallback covers them. They have no run directory, so
  they are not listed anyway.
- No new dependency: `subprocess` is stdlib and `git` is the checkout's own
  tool.
- D3 still open:
  - render orun1's `docs/probes/orun1/` through the dashboard from the repo
    alone;
  - serve record-linked artifacts through an allow-listed read-only path,
    with a browser test opening orun1's probe pages via `/r/`;
  - list CLI agent turns as runs.
- The tail has 2 unreconciled records (with this one), under the threshold
  of 3.

Dispatch closed: 1 unit — run pages show the charter's done criteria from the run's branch (ADR-514); DASHBOARD.md GET/HEAD claim corrected

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 0220ce7c26718cc6fc16839c991ccb7098a2d83b

## State Impact

- target: swift-nest-0229 — /r/<run>/ now shows the run's done criteria (id, title, ticked/open, text) read from the run's branch via git show (working tree for the live run), ADR-514, browser-tested; still open: orun1 probe pages via /r/, allow-listed record-linked artifacts, CLI turns as runs
