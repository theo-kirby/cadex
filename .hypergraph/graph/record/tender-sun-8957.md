---
node_id: ebd6f410-7379-5d7a-8894-6ac765d2cc27
slug: tender-sun-8957
title: 'ADR-579: CLI suite 722 s in thirds to 566 s as one command; 480 s not yet met'
created_at: '2026-10-06T23:44:19+00:00'
parents:
- light-dusk-7651
summary: ''
---
## What
ADR-579 (commit on `ouroboros/orun4`): the CLI suite gets lighter again. A new `small_presentation` fixture (`cli/tests/conftest.py`, built on ADR-563's `small_renders`) films at 128 px and draws the heroes at 64 px, scaled up to their real 1024 px. Three tests use it: the two evaluation command tests and the loop's MCP evaluate round. The two leg-timeout walk tests use a 1 s termination grace. The `test_loop.py` fixture waits 0.5 s, not 2 s, on a run that was only registered. `test_render.py::test_real_part_only_and_empty_refusal` uses `small_renders`. No test is removed and no assertion changes. `docs/probes/orun4/REPORT.md` §6, its ADR table and defect 3 are updated.

## Why
This is the critic's named unit: the owner's CLI-suite target, the last open item behind the withdrawn done claim. Following the critic's order: measure with `--durations=40` in GPU-hidden thirds, then cut or shrink fixtures and sleeps, then write one ADR with before and after.

## Method
- **Before**, `--durations=40` in thirds with `CUDA_VISIBLE_DEVICES=`: `NR%3==0` 150 s (395 passed), `NR%3==1` 341 s (324 passed, 1 skipped), `NR%3==2` 231 s (491 passed). Total **722 s**.
- **Regression found:** H2 and H3 (ADR-570, ADR-571) made a passed evaluation draw two 1024 px heroes and a 512 px shove video. The two evaluation command tests went from about 30 s to 74.0 s and 61.3 s. A cProfile of the film test put about two thirds of the time in the studio frames of the shove and seed videos (`video._studio_frames`) and a quarter in `CadexStudio.hero` and `print_bed`. Neither test asserts a pixel.
- **Full-size drawing stays pinned where it is the claim:** the 512 px studio video in `test_video.py`, the 1024 px hero in `test_look.py`, the print bed in the engine's `test_studio_print_bed.py`, and the leg grace in `test_stopped_leg_preserves_descendant_cleanup_grace`.
- **Per test, before → after:** evaluation tests 74.0 → 11.7 s and 61.3 → 11.0 s; loop round 22.0 → 7.3 s; leg-timeout tests 7.0 → 3.0 s each; five registered-run teardowns 2.0 → 0.5 s; render refusal 10.8 s → under 3 s.
- **Gate:** the whole suite as **one** foreground command, `CUDA_VISIBLE_DEVICES= timeout 595 pixi run python -m pytest -q -p no:cacheprovider --durations=40 cli/tests`: **565.7 s, 1210 passed, 1 skipped**, green.
- **Engine suite not run:** only `cli/tests` and docs changed, with no engine code.

## Result
- The CLI suite is green in **566 s as one foreground command**, inside the shell's 600 s limit, down from 722 s in thirds. The thirds are no longer needed to run it.
- **The 8-minute (480 s) target is still not met.** The slowest tests left are keep-listed or claim a real leg: the real-CPU walk lifecycle 59.8 s, the loop's real trainer 20.9 s, the remote-walk parity 18.6 s, the second-mechanism walk 17.5 s, the iterate refusal 14.6 s and the train digests 10.7 s. Together that is 142 s. The other ~1200 tests share ~425 s.
- **No floor is claimed.** The 86 s still needed could come from many small non-keep tests. Candidates measured:
  - `test_review_checkpoints` newest-checkpoint loop 9.0 s
  - `test_video` declared-materials film 8.9 s
  - `test_loop` each-ending 7.8 s
  - `test_review_status` own-poll 7.0 s
  - `test_look` declared-role 6.5 s
  - the `test_render` real views at 6 s each
  - `test_review_lifecycle` 5.8 s and 5.2 s

  The walk tests' legs run `cadex` as a subprocess, so in-process render fixtures do not reach them.
- **Concern:** no test now draws the shove video at 512 px. Its marks are still counted (`marked_frames > 0`) at 128 px.
- The record tail is now one unreconciled node.

Dispatch closed: 1 unit — ADR-579, CLI suite 722 s (thirds) → 566 s as one command, green; 480 s target not yet met

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: b44378271faa8f439c4fd7da43fd26bead7aabf9

## State Impact

- target: early-arbor-7123 — The CLI suite runs green as one foreground command in 566 s (ADR-579; 1210 passed, 1 skipped), from 722 s in thirds; a passed evaluation's presentation is drawn small in tests that do not claim its pixels. The owner's 480 s target is not yet met.
