---
node_id: ca718905-dbd5-533a-b471-ec4cba11842d
slug: staid-wave-3739
title: 'orun2 D2 item 5: rollout playback in the dashboard viewer from the run''s trace (ADR-511)'
created_at: '2026-10-03T20:26:15+00:00'
parents:
- narrow-crest-4950
summary: ''
---
## What

Rollout playback in the dashboard's viewer (orun2 D2 item 5, ADR-511). A run that rolled out now has
a `playback` summary on `api/model/run/<name>` and its frames at `api/playback/run/<name>`
(`review_server.trace_playback`, `run_playback`). *Model settings* gains Play and a `#play-time`
slider in simulation seconds that drive the viewer's `setPoses`, with the viewport clock and a note
giving the time, the frame, and each actuator's command in force against its range.

## Why

The critic named this unit: rollout playback through `setPoses`, using time-based frames with each
quaternion's sign kept continuous, per the `cadex_animate.py` ledger row, plus a browser test against a
real engine that checks a mid-trace frame's placements equal the trace. It was the last open piece of
D2 item 5. The critic also asked to "then reconcile". A work iteration is forbidden to reconcile, so
this record does not. The tail is now 2 unreconciled records (narrow-crest-4950 and this one), and the
next pass should be a reconcile.

## Method

- Re-derived the frame rules from the ledger row, copying nothing from the shell:
  - only frames with `nominal_time_s` play, sorted by time, and the untimed input frame is dropped;
  - each component's quaternion is negated when its dot product with the previous frame's is
    below 0;
  - `actuator_commands` is held zero-order over the interval before its frame, and the reset
    frame has `None`.
- The page reuses Explode's lerp/slerp, factored into `blendPoses`.
- The frames travel on their own route so that the manifest stays small.
- Real rollout: a CPU walk of `examples/lifecycle/linear-carriage` (`--iterations 1 --envs 4`,
  about 19 s, the same as `test_walk`'s carriage test) leaves `runs/baseline/rollout/assembly-simulation-trace.json`
  with 26 timed frames at 25 fps over 1.0 s, in which the slide moves.
- Tests in `cli/tests/test_dashboard_inspect.py`:
  - `test_playback_is_timed_frames_with_a_continuous_quaternion_sign` (unit);
  - `test_browser_plays_a_real_rollout_with_the_trace_s_placements`: headless Chromium, real engine,
    real trainer venv, skipped without one. It checks:
    - the manifest summary matches the trace;
    - the mid-trace frame k=13 at its own time has the trace's placements exactly and that frame's command;
    - halfway between two frames the slide is at the mean and the command is the next frame's;
    - Play runs to the last frame and stops;
    - an unknown run is a 404.
- Docs: `docs/DASHBOARD.md` §25, ADR-511, and in `docs/SHELL-PARITY.md` the `cadex_animate.py` row and
  the Policy editor row are now ported, with the bars dropped.

## Result

- Rollout playback works from a browser against a real engine. Both new tests pass (2 passed, 20.6 s).
- `pixi run test-engine`: 2592 passed, 56 skipped.
- CLI suite (GPU hidden): 1345 passed, 1 skipped (20 min).
- Every part of D2 item 5 now has a browser test:
  - section and exploded views (ADR-510);
  - the collision view (ADR-508);
  - rollout playback (ADR-511).
- Not done:
  - the accepted attempt's own `assembly.simulation` trace is not offered for playback, only runs (ADR-511 says so);
  - actuator commands show as numbers, not bars.
- Not changed: no `OP_ARG_SPECS` change, no tool surface, no new dependency.
- Next: reconcile (the frontier has been flat; D2 can move off working), then A1, the agent's
  non-blocking channel to the owner.

Dispatch closed: 1 unit — rollout playback in the dashboard viewer from the run's trace, browser-tested on a real walk (ADR-511)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: c6373d5125c2d1eb8ca2e6620e24e4349bbb3692

## State Impact

- target: twilight-aspen-1541 — D2 item 5 complete: rollout playback in the viewer plays a run's own trace in simulation seconds through setPoses (ADR-511), browser-tested on a real walk; with section, exploded and collision views every item-5 view has a real-engine browser test
