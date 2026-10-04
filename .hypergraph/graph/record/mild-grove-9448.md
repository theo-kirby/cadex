---
node_id: 8446b8db-67c0-5563-be8a-9cba963ddacc
slug: mild-grove-9448
title: 'orun2 D1: a bare ./cadex and pixi run app serve the dashboard over a projects directory (ADR-502)'
created_at: '2026-10-03T16:16:35+00:00'
parents:
- light-path-5130
summary: ''
---
## What

orun2 D1, first half: a bare `./cadex` and `pixi run app` serve the dashboard over a projects directory, bound to 127.0.0.1 (ADR-502, commit `a9df266e`).

## Why

The critic named D1 as the next criterion by priority, now that S1 and R1 have their evidence. It asked for four things: `./cadex` with no `--project` serving the dashboard over a projects directory on 127.0.0.1; a `pixi run app` task; the fresh-clone sequence in README and docs/CLI.md; and a test that starts the server, fetches the first page and lists the projects. The after-measurements are deferred until D2 lands, as the critic said. I did all of this as asked, with no deviation.

## Method

- **Server.** `cli/cadex_cli/review_server.py` gains `ProjectsDirectory`, `ProjectsServer` and `serve_projects`.
  - `/` serves `projects.html` and `projects.js`. They are new files and share the tokens in `review.css`.
  - `/api/projects` (`cadex-projects-v1`) lists every non-hidden subdirectory that holds a `script.json`. The list is re-read on each request, and each entry carries its accepted identity and run count.
  - `/p/<name>/…` sends the request to the unchanged project router. `_route` now takes the project as a parameter. `/p/<name>` with no trailing slash redirects with a 301.
- **Page.** The review page could only live at `/`, because it asked for every resource by an absolute path.
  - `index.html` and `capture.html` now link their files relatively.
  - `review.js` computes `BASE` from `location.pathname` (`/p/<name>`, or empty at `/`). Every request is prefixed with it, including the server-absolute mesh URLs, through a fetch wrapper passed to `viewer.load`.
  - `review_scene.js` is deliberately untouched, so `video.py`'s scene `style_digest` does not move.
  - In single-project `cadex review` the requested URLs are byte-identical to before, so existing fetch-interceptor tests stay valid.
- **CLI.** `cadex app [--projects DIR] [--host] [--port]` is added.
  - A bare `cadex` (no prompt, no subcommand) now runs `app`; help is `-h`.
  - The projects directory is `--projects`, then `CADEX_PROJECTS`, then `~/cadex-projects`. It is created if absent, so a fresh clone reaches a first page without a project.
  - `review` and `app` both skip the PROGRESS row and the commit.
- **Pixi.** `pixi.toml` gains `app = { cmd = ["./cadex", "app"] }`.
- **Docs.** README's Build and run section now reads `pixi run setup-engine`, `pixi run build-engine`, `pixi run app`, and mentions `tailscale serve` for remote viewing. docs/CLI.md has a new command row. DASHBOARD.md §1, AGENTS.md's command block (still 215 lines) and ADR-502 are updated.
- **Tests.** The new `cli/tests/test_app.py` has 8 tests:
  - the listing: projects only, live, with accepted identity and run count;
  - the prefix mount and its 404s, including hidden and non-project directories;
  - bare-invocation routing;
  - the directory defaults;
  - the bad file and bad port refusals;
  - the real `./cadex` shim run as a subprocess against an existing directory and an absent one. It reports `127.0.0.1`, serves the index and the listing, stops cleanly on SIGTERM and writes nothing to the project;
  - the `pixi run app` task;
  - a headless-Chromium walk from the index to `/p/biped/`, where the accepted model and a run's retained mesh both reach `loaded`.

  `test_commands.py`'s bare-invocation test is rewritten to pin `-h` as the help, and test_app.py pins the bare invocation as the app.

## Result

- **Gates.** The CLI and engine suites below ran on the source tree. No protocol or payload change, so no packaged gate.
  - `pixi run test-engine`: 2582 passed, 56 skipped.
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: 1304 passed, 1 skipped.
  - After the doc edits, test_project_docs, test_app, test_review_design and test_commands were re-run: 207 passed.
  - The browser test ran against a real Chromium and did not skip.
- **What is true now.** From a clone, `pixi run setup-engine && pixi run build-engine && pixi run app` serves the dashboard at http://127.0.0.1:8765/ over `~/cadex-projects`.
- **What D1 still needs.**
  - The measured before/after numbers: tracked files, tree size, LOC by tree, setup steps, wall time from clone to first page, and installed footprint. The critic deferred these until D2 lands.
  - A wall-clock run from an actual fresh clone on sb1x.
- **Behaviour changes.**
  - A bare `cadex` no longer exits 2 with help; it starts a server.
  - `~/cadex-projects` is created if absent.

  Both are reversible defaults, recorded in ADR-502.
- **D2 and D3.** The projects index is the natural place for D3's run list beside projects. D2's write endpoints must add the token or same-origin check under both the `/` and `/p/<name>/` mounts.
- **Reconcile.** The unreconciled tail is 1 node.

Dispatch closed: 1 unit — `cadex app`, a bare `./cadex` and `pixi run app` serve the dashboard over a projects directory on 127.0.0.1 (ADR-502), pinned by test_app.py including a browser walk.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: a9df266e8971165a20e64203e2c2dbe2b74c5dbc

## State Impact

- target: sweet-bloom-8352 — first half evidenced: `pixi run setup-engine && pixi run build-engine && pixi run app` (or a bare `./cadex`) serves the dashboard over ~/cadex-projects on 127.0.0.1, index at / and each project at /p/<name>/ (ADR-502, commit a9df266e, cli/tests/test_app.py incl. a Chromium walk); remaining: the measured before/after numbers and a wall-clock fresh-clone run on sb1x
