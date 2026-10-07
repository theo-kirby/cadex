---
node_id: 924e64b5-817d-5917-9842-4192c1c8f1f5
slug: wise-light-2451
title: R1. A goal can be held in a body's frame
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **R1. A goal can be held in a body's frame.** A reach goal (point or pool) can be declared relative to a component so it moves with it, the policy's goal channel being what the base sees; reach metrics measure against where the goal was at each frame; tests show a goal on a drifting base staying put in that frame with final error measured against it. The human owns the checkbox [rec: honest-bay-2056].

**Implemented for point goals** (ADR-592, commit `ba33bcaa`) [rec: long-cabin-6279]. Reconcile judgement: status `working`; the record covers `kind="point"` only and does not mention pool goals, which the charter names — noted, not assumed.

- **Surface**: `assembly.goal(..., kind="point", frame=component)`. The draw is the world draw unchanged (same tries and tests); what is kept is the accepted point in the frame body's frame, `transpose(xmat) · (p − xpos)`. Bundle rows gain `frame`/`frame_id`, and `goal_algorithm` gains `GOAL_FRAME_ALGORITHM` only when declared, so world goals export byte-identical. Engine, trainer host draw and reference runner carry the transform and are pinned equal [rec: long-cabin-6279].
- **Reading the tip**: `assembly.observation(tip, "component_position", frame=component)` (stock `framepos` with `reftype`/`refname`); refused on other kinds, on the read component itself, and beside `sensor=` [rec: long-cabin-6279].
- **Measuring**: `CadexEvaluation.reach_metrics` reads the tip in the segment's frame at every trace frame; schedule, trace `goal_channels` and reach rows carry `frame`; the film places the target with the frame's pose. Mixed frames in a spec refuse (`success_goal_mismatch`); a frame that is the tip or no body is `goal_frame_missing` [rec: long-cabin-6279].
- **Tests** (`test_dynamics_goal_frame.py`, 14; `cli/tests/test_film.py`): the charter's drifting-base test — base slides 400 mm and turns 90°, a riding tip has final error 0, a tip left behind measures 316.2 mm (= hypot(300, 100)), the reverse for a world goal; an end-to-end evaluation with the target held in the moving upper arm passes. Mutation check: removing the transform from `reach_metrics` fails 2 tests [rec: long-cabin-6279].
- **Gates**: `pixi run test-engine` 2664 passed, 60 skipped before a describe_api trim, then the 16 listing-touching files 618 passed; CLI 1218 passed, 1 skipped; no protocol change [rec: long-cabin-6279].
- **Not done**: no xscript project has run `frame=` on the real engine end to end; P2 is the first [rec: long-cabin-6279].

## Negative knowledge

- [scope: tasks holding goals in a frame | confidence: high | evidence: long-cabin-6279] A reward written against a world `component_position` while the goal is held in a frame silently compares across frames. Documented, not detected [rec: long-cabin-6279].
- [scope: describe_api assembly section | confidence: high | evidence: long-cabin-6279, tiny-lake-4065] The section sits within ~0.1–0.4 % of its 21,500-char budget after two trims this run; the next API addition needs prose cut or the section split [rec: tiny-lake-4065] [rec: long-cabin-6279].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-r1-goal-can-be-held)
- long-cabin-6279 — point goals held in a component's frame (ADR-592); drifting-base test passes
