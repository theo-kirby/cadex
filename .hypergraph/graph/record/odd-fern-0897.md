---
node_id: 9187d98d-ad95-5a0c-a34d-bd757766609f
slug: odd-fern-0897
title: 'CLI suite lighter, first cut: measured 1017 s, five safe cuts to 793 s (ADR-562)'
created_at: '2026-10-06T11:52:23+00:00'
parents:
- stormy-glacier-7552
summary: ''
---
## What

First unit of the owner's note "Make the CLI suite lighter": measured the whole CLI
suite with `--durations=40` (GPU hidden, every piece in the foreground), then made five
cuts that are safe under the keep list, re-timed them, and wrote ADR-562 listing each
removed test and why. Commit `495fc73a`.

## Why

The critic named this unit: the owner's note puts the lighter suite ahead of the
remaining criteria, measure first, record the wall times and the slowest tests, then
make the first safe cuts and start the ADR. Done as asked.

## Method

Before, 1197 tests, `CUDA_VISIBLE_DEVICES=`:
- third `NR%3==0`: 400 passed, **185 s**;
- third `NR%3==1`: ran past the 10-minute limit (killed by `timeout 590` at ~85%,
  with two `F` printed before the kill); re-run as sixths `NR%6==1` **450 s** (242 passed,
  1 skipped) and `NR%6==4` **241 s** (113 passed), both green;
- third `NR%3==2`: 441 passed, **141 s**.
- Sum **1017 s (17.0 min)**.

Slowest tests and files (from the four `--durations=40` lists):
- `test_walk.py`: `test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates` 63.3 s;
  `test_remote_walk_…_cpu_dispatcher[hinged-arm]` 38.5 s, `[linear-carriage]` 36.7 s;
  `test_the_same_walk_handles_a_linear_carriage` 18.5 s; about 30 fake-leg tests at a
  4.1–8.3 s floor. cProfile of one: 11.2 of 12.4 s in `CadexStudio.studio` (four 512 px
  views + the 1024 px hero, pure Python).
- `test_evaluate.py`: three real evaluations at 30.5 s each; ~28 s of each is the film.
- `test_loop.py`: five tests with a **20.05 s teardown** each (fixture waited on
  `request_stop` for runs only registered, with no supervisor); real-trainer tests
  24.9 s and 22.0 s.
- `test_train.py`: iterate 29.3 s, real trainer 11.6 s. `test_video.py` 10.7/8.9/5.5/4.9 s,
  `test_look.py` 7.9/6.5/5.6 s, `test_render.py` 10.8/6.4/6.0 s, `test_sheet.py` four at
  ~6.2 s, `test_review_overlay.py` 10.6/8.6/7.0/6.6 s (page-poll waits),
  `test_review_checkpoints.py` 9.0 s.

Cuts (ADR-562 lists each): (1) `test_loop` fixture waits 20 s only for a running or
locked run, 2 s otherwise; (2) `test_walk`'s `fake_cadex` draws review views at 64 px,
hero stays 1024 px (a 128 px hero broke the sheet: "the sheet is laid out for a 1024 px
hero"); (3) removed `test_evaluate_never_restores_or_accepts_an_edited_working_script`,
folded into `test_an_accepted_policy_is_evaluated_as_one_command`; (4) the fail-verdict
evaluate test runs `--film none`; (5) removed the `linear-carriage` parametrisation of
the remote-walk parity test (the carriage's own real walk stays).

## Result

After: third `NR%3==1` runs **whole again in 467 s** (353 passed, 1 skipped), from
691 s across two sixths; `test_evaluate.py` alone 112 s → 43 s. Thirds 0 and 2 are
untouched (185 s, 141 s, measured this iteration on the same tree). Suite **793 s
(13.2 min)** from 1017 s, 1195 tests from 1197; every piece green. Nothing on the keep
list changed. Engine suite not run: no engine code changed.

Not yet the 8-minute target. Next cuts, measured above: the hero render in the walk's
fake legs (~2.5 s × ~30 tests; a cheaper path would be a test-side render stub that
still writes a 1024 px hero), `test_sheet.py`'s four ~6 s full-render tests,
`test_look.py`/`test_video.py` duplicated full-size renders, the overlay tests' page-poll
waits, and `test_train.py`'s 29 s iterate. Then a single-command whole-suite timing.

Concern: the first, over-limit third-1 run printed two `F` before it was killed; the
same files passed whole (467 s) and in sixths after. Not reproduced; if it recurs, it is
order- or load-dependent.

Dispatch closed: 1 unit — CLI suite measured (1017 s) and first safe cuts landed (793 s, ADR-562)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 495fc73a6b80027ae9770fc28bc44af66c487457

## State Impact

- target: early-arbor-7123 — the CLI suite is measured (1017 s over thirds) and lightened to 793 s by ADR-562's first cuts; third NR%3==1 fits one 10-minute command again; the 8-minute single-command target is still open
