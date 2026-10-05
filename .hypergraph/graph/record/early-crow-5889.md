---
node_id: 707dd73b-f6e6-5190-a502-f4ea4d58cc22
slug: early-crow-5889
title: 'V4 page half: the overlay shows the agent''s latest call, recent calls, idle after 5 min (ADR-550)'
created_at: '2026-10-05T13:44:30+00:00'
parents:
- forest-walrus-2370
summary: ''
---
## What
V4's page half (ADR-550, commit on `ouroboros/orun3`). The stage overlay's expanded detail now shows what the agent last did through `cadex mcp`. The data comes from `/api/project`'s `activity` (ADR-549).
- **The line** (`#overlay-activity-line`): the newest call's tool and argument summary, and how long ago it returned, timed against the server's `served_at`. A failed call shows `failed: <detail>` in `--bad`.
- **The list** (`#overlay-activity-log`, `#overlay-activity-list`): a closed `recent calls` disclosure with the newest five calls and their UTC times.
- **Idle**: once the newest call returned more than 300 s ago, the line reads `agent idle · last call <tool> <ago>` in `--ink-2`.
- **No log**: the line shows the server's reason (`data-state="none"`).

The new state is `#overlay-activity[data-state=none|active|error|idle]`. `renderOverlay` redraws it on the existing poll, so there is no new loop and no write. The DASHBOARD.md §2 row lists the hooks, and `test_review_design.py` pins them.

## Why
The critic named V4's overlay line as the next unit. It is the open half of `rare-beacon-3440`, the next charter criterion in priority order.

**Deviation:** the critic asked for a reconcile first: fold brisk-dune-8872 and forest-walrus-2370, then regenerate STATE.md. This dispatch forbids reconcile in a work iteration, with no exceptions, so I did not reconcile. The tail is now 3 unreconciled records, which is the charter's reconcile trigger. The next reconcile pass should fold:
- brisk-dune-8872 into peaceful-spire-1615 (V3's evidence looks complete: a candidate for working);
- forest-walrus-2370 and this record into rare-beacon-3440.

## Method
- Added the page code to `index.html`, `review.css` and `review.js` (`renderActivity`, called from `renderOverlay`).
- **Idle threshold, 300 s.** An agent returns a call every few seconds to a couple of minutes, so 5 minutes is past that gap. It is also half the 10-minute `designing` window, so the line goes idle before the stage does. ADR-550 records the cost: a call is logged when it returns, so a single call that runs longer than 5 minutes shows as idle until it returns.
- **Browser test** (`test_the_overlay_says_what_the_agent_is_doing_and_when_it_went_quiet`, Chromium through `browser.py`). It starts with no log, then appends calls with `append_activity` while the page polls, and checks each step:
  - the line follows each call;
  - a failure turns the line `--bad`;
  - the list shows outcomes in order and caps at 5;
  - rewriting the log with calls 7 and 60 minutes old turns the line idle;
  - deleting the log brings back the absence.
- **Other tests.** A second test pins the test's threshold to the page's `ACTIVITY_IDLE_S`. The 390 px test now has activity entries in it.

## Result
- **Overlay at 390 px**, expanded with activity: 280 × 210 px, 20.8% of the viewport (bar: 25%; before this change: 280 × 171, 17%). Collapsed it is still 40 px.
- **Overlay tests:** `test_review_overlay.py`, 10 passed.
- **CLI suite**, GPU hidden: `pixi run python -m pytest cli/tests` gives 1159 passed, 1 skipped.
- **Engine suite:** `pixi run test-engine` gives 2585 passed, 58 skipped.

With both halves landed, V4's evidence list is complete:
- the write half and its cap (ADR-549);
- the end-to-end test from `cadex mcp` to `/api/project` (ADR-549);
- the overlay line, the list and idle (ADR-550);
- the tool surface is unchanged.

**Concern:** the collapsed overlay still shows only the stage line, so the activity is seen only when the overlay is expanded. I chose this to keep V1's "collapses to one line".

Next unit per the critic: P1.

Dispatch closed: 1 unit — V4 overlay activity line, recent-calls list and 5-minute idle (ADR-550)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 50dce958a4ad3f047f3a172eac60ee7ab600187c

## State Impact

- target: rare-beacon-3440 — V4's page half landed (ADR-550): the overlay shows the newest cadex mcp call and its age, a recent-calls list of five, idle after 300 s, and the absence with no log, with a browser test that rewrites the fixture log; with ADR-549, V4's evidence is complete, a candidate for working
