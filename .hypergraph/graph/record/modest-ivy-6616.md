---
node_id: 39f46a70-6e19-5c14-aa77-9858753ec2fa
slug: modest-ivy-6616
title: 'ADR-580: CLI suite 566 s to 474 s as one command, under the 480 s target'
created_at: '2026-10-07T00:25:49+00:00'
parents:
- tender-sun-8957
summary: ''
---
## What

ADR-580 brings the CLI suite under the owner's 8-minute target as one foreground, GPU-hidden command: **474.4 s, 1211 passed, 1 skipped**, down from 566.3 s, which was measured again at the start of this iteration. No test is removed and no assertion is weakened.

- `review_server.serve` and `serve_projects` poll for shutdown every `SHUTDOWN_POLL_S = 0.05` s. The standard library's 0.5 s made every `shutdown()` wait about half a second, and about 150 test servers stop in one suite run. The new test `test_app.py::test_a_served_page_and_the_app_stop_promptly` requires both servers to stop in under 0.15 s. It fails with the old 0.5 s; I checked by setting the constant back.
- `test_walk.py`: the real lifecycle walk now uses `small_presentation`, and the remote-walk parity and linear-carriage walk use `small_renders`. The review render is drawn in the calling process, and none of these tests claims its pixels.
- The carriage walk and `test_train.py`'s iterate refusal now train with `test_loop.FIXTURE_TRAINER`. The carriage walk gets it through a leg bootstrap, the same way the remote parity test does. Three tests still pin real CPU training: the lifecycle walk, the trainer-digest test and the loop's real trainer.

## Why

The critic asked for this unit: close the remaining 86 s to get under 480 s, using shrunk fixtures or sleeps before cuts, add no xdist, then write an ADR and a record.

The critic also asked whether the iterate refusal (14.6 s) and the remote-walk parity (18.6 s) really need a real leg:
- **Iterate refusal:** no. Its claim is the refusal, so it now uses the fixture trainer.
- **Remote-walk parity:** it already used the fixture trainer. Its remaining cost was the full-size review render, twice, which is now drawn small.

I did not work through the critic's other named candidates (checkpoints loop, declared-materials film, each-ending, own-poll, declared-role, render real views). Measurement found two larger levers: the 0.5 s shutdown poll spread across every served test, and the walks' full-size renders. Those two closed the gap. Of the critic's candidates:
- **Declared-role:** asserts pixel counts, so it was left alone.
- **The others:** drive real rollouts or the page's 2 s poll.

## Method

1. Measured the whole suite with `--durations=80` (566.3 s), then with `--durations=0` after the walk changes (525.8 s). The `--durations=0` run gave per-file totals and showed setup/teardown at 45 s. The teardowns were 0.50 s each: `serve_forever`'s idle poll.
2. Profiled one carriage walk in process with cProfile. Its 16.8 s split into 9.3 s of real JAX CPU training in the train leg and the in-process `write_render`, which drew five studio frames at full size.
3. Timed the changed tests on their own:
   - lifecycle 59.9 s → 46.7 s;
   - parity 18.7 s → 10.0 s;
   - carriage 17.4 s → 4.9 s;
   - iterate refusal 14.7 s → 5.9 s;
   - three server-heavy files 36.0 s → 16.7 s.
4. Gate: `CUDA_VISIBLE_DEVICES= pixi run python -m pytest -q -p no:cacheprovider cli/tests` as one foreground command. It took **474.43 s** (wall 7 min 54.7 s), 1211 passed, 1 skipped.

## Result

The CLI suite now meets the owner note's 8-minute target as one foreground command, so it no longer needs splitting into thirds. The margin is small, about 5 s, and run-to-run variance could push one run over. If that happens, the next levers are measured and named in ADR-580's evidence: the real lifecycle walk at 46.7 s, the loop's real trainer at 20.9 s, and the evaluation command tests at about 11 s each. All of them are on the keep list or claim real training.

Product change: `cadex app` and `cadex review` servers now stop within 0.05 s of `shutdown()`. Their idle wakeup rate goes from 2/s to 20/s, which costs almost nothing.

`pixi run test-engine`: 2611 passed, 59 skipped in 344.9 s. No engine file changed in this unit.

The unreconciled tail is two nodes (tender-sun-8957 and this one). The critic asked for a reconcile and a done claim after this unit. A work iteration is forbidden to reconcile, so that is left to the reconcile pass.

Dispatch closed: 1 unit — ADR-580, CLI suite 566 s → 474 s as one command, under the 480 s target

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 938e59c1d8c3ccf3aac2becc4acb8c601f60cd3e

## State Impact

- target: early-arbor-7123 — The CLI suite runs green as one foreground GPU-hidden command in 474 s (ADR-580; 1211 passed, 1 skipped), under the owner's 480 s target; dashboard servers stop within 0.05 s of shutdown(); the walks draw their review render small where pixels are not the claim, and the carriage walk and iterate refusal train with the fixture trainer.
