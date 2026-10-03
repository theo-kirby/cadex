---
node_id: ce9dcc0e-85e2-5a19-bbd7-0c0a973bfb6e
slug: noble-glade-0483
title: 'orun2 D2: a comment on the design or a picked part, received by the next turn (ADR-505) — backfilled record'
created_at: '2026-10-03T17:30:28+00:00'
parents:
- placid-bell-2440
summary: ''
---
## What

Backfilled record for iteration 18's unit, commit `6d1a1eb2` ("ouroboros #18: no record"): orun2 D2 item 3 — a comment on the whole design or on a part picked in the viewer, which the next agent turn receives (ADR-505).

## Why

The critic's message for iteration 20 asked first for this record, causally parented on iteration 17's, with its impact on D2 (`twilight-aspen-1541`). The unit landed without one.

## Method

What `6d1a1eb2` changed (read from the commit and ADR-505):
- `cli/cadex_cli/comments.py` (new): append-only `comments.jsonl` in the project root with `comment` and `delivered` lines; `add_comment`, `read_comments`, `pending_comments`, `mark_delivered`, `with_comments`.
- `cli/cadex_cli/__main__.py`: `cadex comment [--part NAME] TEXT` (no engine, no row, no commit); `cadex -p` puts undelivered comments ahead of its prompt and marks them delivered once the turn has run; a failed turn delivers nothing; the envelope carries `comments`.
- `review_server.py`: `POST api/comment` runs `cadex comment --project <root> --json [--part=<name>] -- <text>` through `run_leg` behind the ADR-503 token/Origin check; `/api/project` carries the last comments.
- `review_scene.js` / `review.js`: click picking (press and release under 5 px, ray cast to the solid), the pick shown, the comment list with delivery state (`docs/DASHBOARD.md` §20).
- Tests: `cli/tests/test_comments.py` (new) and a browser test in `test_dashboard_writes.py`.

Re-verified this iteration at HEAD `6d1a1eb2` with the GPU hidden (same command as the previous record).

## Result

- **D2 item 3 is evidenced.** In headless Chromium against a real engine on a two-part project: a whole-design comment, real mouse clicks that pick `plate` then `post`, a drag that picks nothing, a comment on `post`, then a turn from the page — `fake_claude` received both comments ahead of `go on`, the list shows them received, none pending, the pick survives the rebuilt model.
- Re-run at HEAD: `test_dashboard_writes.py` + `test_comments.py` **16 passed, 0 skipped**.
- As with iteration 17, that iteration's full-suite numbers were not recorded and are not invented here.
- Parity: `SHELL-PARITY.md` maps the shell's pins to pick-to-comment at part granularity (ADR-505).
- Concern: comments travel in the user prompt, so a resumed conversation keeps them as said once; a comment pins only the revision, not geometry.

Dispatch closed: 1 unit — backfilled record for ADR-505's comment and part-pick write path (commit 6d1a1eb2).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 6d1a1eb286d260977d3f38986fff246a86abc0c0

## State Impact

- target: twilight-aspen-1541 — item 3 evidenced: cadex comment writes comments.jsonl, the next cadex -p receives pending comments ahead of its prompt; POST api/comment runs it as a child behind the token; headless-Chromium test against a real engine picks parts by click and a page-started turn receives both comments
