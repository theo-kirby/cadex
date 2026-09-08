---
node_id: 2aa42cf1-88bf-53c5-9f14-722ee4c5bdba
slug: square-bay-3436
title: The walk's review reports rollout travel in millimetres and degrees, and ranks neither
created_at: '2026-09-08T18:06:21+00:00'
parents:
- solemn-journey-9731
summary: ''
---
## What

`cadex walk`'s review now reports whether the mechanism actually moved, in
two channels, in both places a reader looks.

`review.json` (`cadex-walk-review-v1`) gains a `motion` block beside
`clearance`. Per component: the per-axis `position_range_mm`, the
`max_displacement_mm` from the reference pose, and the `max_rotation_deg`
swing `2·acos(|q₀·q|)` away from the reference orientation. It names
`largest_translation` in millimetres and `largest_rotation` in degrees and
**declines to rank one against the other**, saying so in a `ranking` field.
The walk's `PROGRESS.md` row and its run notes carry the same two figures:
`motion N mm (component), N° (component) over N solved frame(s)`.

`PROGRESS_NUMBERS_LIMIT` in `project_docs.py` raises the progress row's
numbers cell from 160 to 320 characters — see `## Result`.

ADR-259, a ROADMAP bullet, and `docs/CLI.md`'s walk-review section in the
same commit (`19549da9`).

## Why

**Charter criterion advanced: "The walk exists and is tested headlessly"
(`crisp-reef-5607`), and the review half of "The agent can see its work
without a screen" (`damp-moon-9297`).** This is short-rung unit 1 of the
plan the overseer named, and it is the first half of the frontier's
lifecycle-review gap: the review could say what a rollout scored and
whether its parts collided, but not whether anything moved, so a retrain
that killed the motion and a retrain that merely scored worse read
identically.

Two channels rather than one, because displacement alone is a *wrong*
answer rather than a partial one — the premise `solemn-journey-9731` was
minted to correct. Measured here on the repository's own examples:
`hinged-arm` travels **0.0000 mm** and rotates **178.8334°**;
`linear-carriage` travels **4739.3783 mm** and rotates **0°**. A
millimetre-only row calls a working revolute rig motionless.

No ranking across channels, and none across projects: a scale that made
millimetres and degrees compare would put a carriage free-falling 4,739 mm
on an ideal guide above a swing arm doing its job. Travel is a fact about
one rollout, never a score.

Assumption taken without asking, written into the block and the doc: the
reference is the **first solved frame** and only solved frames are counted.
Frame 0 carries `frame_kind: "input"` and `nominal_time_s: null` — the pose
the solver was *given* — so counting it would report an input as an output.
The block states `frames_counted`, `frames_excluded` and
`excluded_frame_kind` so its 26 is never mistaken for the raw 27.

## Method

Confirmed all three of `solemn-journey-9731`'s premise corrections against
the two real traces under `build/lifecycle/*/runs/baseline/rollout/` before
writing anything: both are 27 raw frames = 1 `input` + 26 `solver_output`;
placements are absolute world poses (`swing` starts at `[12, 0, 6]`, `base`
at the origin); frame 0's `nominal_time_s` is `null`.

`motion_from_trace()` in `cli/cadex_cli/walk.py`, called from the existing
`review_from_outputs()` so the trace is opened once; serialized by the
existing `write_review()`; `_motion_cell()` in `__main__.py` for the row and
the note. No new trace locator, no engine, protocol, payload or `shell/`
diff.

Regressions in `cli/tests/test_walk.py`: four unit tests over frames lifted
verbatim from the two documented example rollouts — the rotating case, the
translating case, an all-identity trace, and the unavailable reasons — plus
the fake-cadex walk's trace extended to real frame shape so the end-to-end
test asserts the review file, the notes and the `PROGRESS.md` row.

## Result

**`pixi run python -m pytest cli/tests`: 231 passed in 209.88 s, no skips,
no backend override** — the engine-needing half ran, so this is not the
bare-checkout run that proves less than it looks like. The real-engine
lifecycle test reports the hinged arm at `motion 0 mm (swing), 178.8°
(swing) over 26 solved frame(s)` — the measured number, through the whole
walk.

One thing the change found rather than added: the first full run failed on
an *existing* assertion, `docs notes 1, no actuators`. The progress row's
numbers cell was capped at 160 characters, and the motion cell pushed the
ADR-256 documentation finding off the end of the row as `docs…`. Raising
the cap to 320 is part of this commit; without it the unit would have
silently dropped a finding the walk already reported.

Not done, and what still blocks the criteria: `motion` is in the walk's
review but **not yet in the iterate comparison** — short-rung unit 2, where
the carriage pair (baseline 103.298 mm at reward 3.296298, iterate 103.719
mm at 2.760187) is the worked example. `crisp-reef-5607` also still wants a
clean end-to-end walk run recorded on this machine.

I did **not** run the maintainer pass the overseer's message asked for
first: the dispatch forbids reconcile in a work iteration without
exception, and that role runs on its own schedule. The tail is 1 node plus
this one, and the plan view is a commit behind the frontier.

Dispatch closed: 1 unit — the walk's review and `PROGRESS.md` row now
report rollout travel in millimetres and degrees, ranking neither, with
four regressions on the documented examples' real frames and the full
`cli/tests` green at 231 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 19549da95f9bf3e70a18e40d308efc726145ffff

## State Impact

- target: crisp-reef-5607 — the headless walk's review now reports rollout travel per component in two channels (position range, max displacement from the first solved frame, max rotation swing), in review.json's new motion block and in the PROGRESS.md row and run notes; measured on the documented examples at 0.0000 mm / 178.8334° (hinged-arm) and 4739.3783 mm / 0° (linear-carriage). The walk still lacks a recorded clean end-to-end run on this machine.
- target: damp-moon-9297 — the review step gains a fourth eye beside render, section, inventory and clearance: what moved and by how much, from the rollout trace, with no screen. It declines to rank millimetres against degrees and says so in the block.
