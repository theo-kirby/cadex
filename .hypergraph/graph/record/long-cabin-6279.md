---
node_id: 3bf677a6-e631-53a6-ad30-39297918e3a5
slug: long-cabin-6279
title: 'ADR-592: a reach goal held in a body''s frame (R1)'
created_at: '2026-10-07T21:23:49+00:00'
parents:
- tiny-lake-4065
summary: ''
---
## What

ADR-592 (commit `ba33bcaa`): a point reach goal can be held in a component's frame — R1 of the orun5 charter.

- `assembly.goal(..., kind="point", frame=component)`: the draw is the world draw unchanged (same tries, same min_z / contact / separation tests, in the world); what is kept is the accepted point in the frame body's frame, `transpose(xmat[frame_id]) * (p - xpos[frame_id])`. Bundle rows gain `frame`/`frame_id` and `goal_algorithm` gains `GOAL_FRAME_ALGORITHM` only when declared, so world goals export byte-identical. Engine, trainer host draw and reference runner each carry the transform.
- The goal channels the policy reads are then the target as the base sees it.
- `assembly.observation(tip, "component_position", frame=component)` reads a position in another body's frame (stock `framepos` with `reftype`/`refname`), so a reward can compare the tip with the held goal. Refused on other kinds, on the read component itself, and beside `sensor=`.
- `CadexEvaluation.reach_metrics` reads the tip in a segment's frame at every trace frame, so final error / time-to-target / overshoot are measured to where the target was. Episode schedule, trace `goal_channels` and reach detail rows carry `frame`; the film places the target marker with the frame's pose.
- A spec holding its goals in other frames than the task's is refused (`success_goal_mismatch`); a frame that is the tip or no body is `goal_frame_missing`.
- Docs: `docs/XSCRIPT.md`, `docs/MUJOCO.md`, `docs/DECISIONS.md` ADR-592, the describe_api assembly note.

## Why

The critic named R1 as the next unit (top open capability, needed by P2). Before it, the critic asked to re-run `hypergraph check` and clear or explain tiny-lake-4065's "274 violations". Measured: `hypergraph check --record … --state … --config .hypergraph/config.yml` exits 0 with **0 violations, 6 warnings** (I5 pending impacts only). The 274 appear only when `--config` is omitted, which leaves the `plan` view unconfigured so every plan-targeting impact reads as I2. So there was no regression; tiny-lake-4065 ran the checker without `--config`. Nothing to clear.

## Method

- Mapped the goal pipeline: `_goal_records` → `draw_episode_goals` (engine), `draw_goals` (trainer), `draw_goals` (reference runner `dynamics_task_episode.py`) → `goal_schedule`/`goal_values` → evaluation segments → `reach_metrics`; film `target_track`.
- New `test_dynamics_goal_frame.py` (14 tests, all fast, on the two-link arm fixture with frame = the upper arm, which turns during every episode; plus synthetic samples):
  - bundle row and algorithm, world goal unchanged;
  - the held draw is the world draw seen from the frame on the same seed (shoulder distance invariant, forearm length from the elbow);
  - trainer and stock-MuJoCo runner draw the engine's numbers;
  - the tip read in the frame and the goal channels agree at every step;
  - refusals;
  - **the charter's drifting-base test**: base slides 400 mm and turns 90°; a tip riding with the base has final error 0; a tip left where it started is measured 316.2 mm (= hypot(300, 100)) from where the target really is; the reverse for a world target;
  - end-to-end evaluation: target narrowed to the still policy's settle point, held in the moving upper arm, passes.
- Mutation check: with the frame transform removed from `reach_metrics`, the drifting-base and end-to-end tests fail (2 failed).
- `cli/tests/test_film.py`: the marker travels with its frame; a missing frame placement is a reason.
- `describe_api` budget: the two new `frame=` signatures pushed the assembly section to 21,797 chars over the 21,500 budget (`test_every_page_of_the_live_contract_fits_one_tool_result`). Fixed by shortening my note and two nearby sentences of the assembly note (no pinned phrase lost; `refused rather than run` kept).

## Result

R1 holds: a reach goal can be held in a body's frame, the policy reads it in that frame, and the reach metrics measure against where it was at each frame.

Gates (foreground, GPU hidden):
- `pixi run build-engine` done.
- `pixi run test-engine`: 2664 passed, 60 skipped before the note trim. After the trim, one pinned-phrase failure was fixed, and the 16 files touching the API listing re-ran: 618 passed.
- `pixi run python -m pytest cli/tests`: 1218 passed, 1 skipped.
- No `OP_ARG_SPECS`, tool or protocol change.
- No packaged gate was run: no payload or protocol change.

The real engine was not run end to end on an xscript project with `frame=`. The worker resolution is covered by the API and dynamics tests only. P2 is where it first runs for real.

Concerns for the next iteration:
- A task that holds its goal in a frame must also read its tip in that frame (`component_position, frame=`). A reward written against a world `component_position` silently compares across frames. That is documented and not detected.
- The assembly `describe_api` section now sits about 0.1–0.4 % under its 21,500-char budget. The next API addition will need prose trimmed or the section split.
- The tail now holds 3 unreconciled records. Per the charter it is due a reconcile pass, which this work iteration must not run.

Next: L1 (closed linkage export and drive), the remaining capability; or P2, which now has both S2 and R1.

Dispatch closed: 1 unit — R1 goal held in a body's frame (ADR-592); hypergraph check 274 explained (run without --config; 0 violations with it)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: ba33bcaa9f26cb45189987229bc7ef2c6af59dd6

## State Impact

- target: wise-light-2451 — R1 met in code: goal(kind='point', frame=component) holds the target in that component's frame (draw kept as transpose(xmat)*(p-xpos), engine/trainer/runner pinned equal), component_position frame= reads the tip in it, reach_metrics measure against where the target was each frame; drifting-base test: riding tip 0 mm, left tip 316.2 mm; ADR-592, commit ba33bcaa
