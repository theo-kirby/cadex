---
node_id: 7d9f51ad-6153-57d4-8d25-71e91cecac76
slug: mellow-hawk-8610
title: 'Prehistory: live mode — a machine you can push'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- humble-path-4466
summary: A running mechanism in the viewport with the policy answering, at 29x real time, shovable with the mouse — then made readable twice more.
---
## What

ADR-109, ADR-110 and ADR-136: a running mechanism in the viewport, with the
policy answering, that the user can shove with the mouse.

## Why

Follows the RL grind. Reading numbers off twelve-seed tables is a poor
instrument for a question like "does this look like it is balancing"; watching it
and pushing it is a better one.

## Method

Three read ops (`live_open` / `live_step` / `live_close`), a resident
`--safe-mode` worker running **the same** `evaluate_episode` the offline path
runs, and exactly one new seam — `forces=(step, data, time_s)`, additive and not
a digest input, needed because `apply_disturbance` rewrites `xfrc_applied` from
zero every step. The shell owns the clock.

## Result

**344 µs a control step (29× real time)** and a **1.72 ms** median `live_step`
round trip against a 33 ms bar, identical from the staged payload. Driven end to
end on mg-legs it runs at real time, takes 1.5 N from three sides, and goes over
at 8 N.

Then the instrument had to be made readable twice more:
- **ADR-110.** Every session opened with the whole declared episode running, so a
  hand push landed on top of four other forces. **Calm mode** is one boolean on
  `live_open` that reaches `evaluate_episode`'s existing *unseeded* episode —
  which live mode could never ask for, because the seed was coerced to `0`. The
  force arrow is drawn from the `xfrc_applied` a frame carries back, at `xipos`,
  so it is **measured rather than intended**, and it is a **sum**: a user's shove
  and the task's wind on one body are one arrow. Hold-to-push needed no engine
  change — re-sending a 0.15 s push every tick is a continuous force. Fixed on
  the way: ADR-109's `forces` guard read one half of its condition and let a push
  accumulate 4, 8, 12… N.
- **ADR-136.** Live mode truncated every six seconds, because it played the
  *task's* episode — the length a trainer wanted, not a viewer. Nothing physical
  is there: an observation carries no clock, so the policy cannot tell step 301
  from step 5. Two keywords on `evaluate_episode`, both defaulting to the old
  loop: `endless` drops the horizon, and `record_steps=False` is what makes that
  affordable — the per-step history is 6.1 kB a step and live mode reads none of
  it. Measured: half an hour of simulation, 300× the old horizon, grows the
  process by **+1.6 MB** against **+553 MB**, at the same throughput.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW dynamics-and-control — live mode: a policy you can watch and push, at 29× real time, from the shipped bundle.
- target: NEW shell — the Live editor and the force-arrow draw handler.
