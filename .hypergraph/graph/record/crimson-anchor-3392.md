---
node_id: 60d17c79-2dfd-5325-b53d-8b8a4ba63477
slug: crimson-anchor-3392
title: 'CLI suite lighter, second cut: small renders, page poll on demand, iterate test cut — 793 s to 647 s (ADR-563)'
created_at: '2026-10-06T12:30:04+00:00'
parents:
- odd-fern-0897
summary: ''
---
## What

Second unit of the owner's note "Make the CLI suite lighter": the cuts ADR-562 listed,
made and measured, recorded as ADR-563 (commits `d45f062e`, `1a43e816`).

- `small_renders` fixture (`cli/tests/conftest.py`): review views at 64 px, hero drawn
  at 64 px and scaled to 1024 px so every file is still written at its real size and
  the sheet still composes. Used by `test_walk.py`'s `fake_cadex`, `test_sheet.py`'s
  four render tests and `test_look.py::test_render_and_bridge_look_report_the_proxies`.
- `test_video.py`: the dashboard-serving and environment/floor films at 128 px.
- `test_review_overlay.py`: the three activity/evaluate browser tests call the page's
  own `poll` (`window.cadexReview.refresh`) rather than wait on its 2 s timer; the 5 s
  sleep became two such calls. The timer itself stays pinned by
  `test_the_overlay_follows_progress_json_on_the_pages_own_poll`; orun4's killed/stopped
  fix tests untouched.
- `test_train.py`'s iterate test renamed and cut to its unique claim (refusal of a task
  change naming the old digest, then the blanked sweep); its second real training,
  re-declare and rollout removed, since the walk's real iterate test makes that claim.
  `docs/MUJOCO.md`'s audit paragraph names the split.

## Why

The critic named exactly these cuts: the walk hero stub writing a 1024 px file,
test_sheet's four renders, the duplicate full-size renders in test_look and test_video,
the overlay page-poll waits, test_train's 29 s iterate, each in an ADR with before/after,
then one whole-suite command with `timeout 590`. All done as asked.

## Method

Per file, before → after, `CUDA_VISIBLE_DEVICES=`: test_walk 211.8 → 144.3 s (fake-leg
tests 2.7 → 0.3 s); test_sheet four tests ~25 s → <1 s each; overlay three tests
25.9 → 2.9 s; test_train 62.1 → 48.9 s (iterate 29.3 → 16.0 s); test_look proxies
7.8 → <3 s; test_video two films 15.5 → <3 s each.

Whole suite as one command, `timeout 590`: killed at 591 s (exit 124). Then thirds, each
foreground: `NR%3==0` 166 s, 400 passed; `NR%3==1` 352 s, 353 passed, 1 skipped;
`NR%3==2` 129 s, 441 passed. All green, `-rf` showed no failures.

## Result

CLI suite **647 s (10.8 min)**, from 793 s (ADR-562) and 1017 s at the run's start; no
test file removed; nothing on the keep list weakened (contract tests, the real-engine
lifecycle walk, orun4 fix tests all intact). Engine suite not run: no engine code changed.

Still not the 8-minute target, and still not one command under 590 s. What remains is
mostly real-engine end-to-end: `test_walk.py` real walks 63 s / 39 s / 19 s,
`test_evaluate.py` 31 s, `test_loop.py` real trainer 26 s and 22 s, `test_train.py`
16 s + 12 s, `test_render.py` real renders ~30 s, and two 7 s leg-timeout tests (2 s bound
plus grace). Candidates for the next cut: whether the remote-walk parity test (39 s)
can use a fake trainer since `test_the_walk_takes_the_toy_…` already runs real legs, and
whether the two test_loop real-trainer tests duplicate each other. Or: pytest-xdist on
32 cores would get under 8 minutes, but it is a new dependency and the suite's tests
share ports/locks — needs a written reason and a check.

The two unexplained `F` from ADR-562's over-limit run did not recur in any run this
iteration.

Dispatch closed: 1 unit — CLI suite second cuts (ADR-563): 793 s to 647 s, all thirds green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 1a43e8162229f64fd3f92e8e3922f175155b366a

## State Impact

- target: early-arbor-7123 — ADR-563's second cuts take the CLI suite to 647 s over thirds (from 793 s); one command still exceeds 590 s; the 8-minute target is still open
