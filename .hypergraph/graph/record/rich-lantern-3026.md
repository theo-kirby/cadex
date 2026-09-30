---
node_id: 758a9773-6d6a-55f2-ab17-e31aeb9f99ae
slug: rich-lantern-3026
title: 'ot11 P1: the judge''s blind spot on stepping and slip is a recorded limit, the film draws the target marker, and P1, P2 and P3 are declared met (ADR-463)'
created_at: '2026-09-30T15:27:53+00:00'
parents:
- frosty-crane-8494
- rough-cloud-5656
- vast-moss-6116
summary: ''
---
## What

Closed the two items left on P1's list (ADR-463, commit `181a2b02`).

1. **The judge's blind spot on stepping and slip is a recorded known limit.** `docs/probes/ot11/contract.json` gains `judge_scope`, beside the frozen `judge` block and not in it: `jobs` (the owner's four sentences of 2026-09-30) and `known_limits` (one entry: the manner score V2 is not a reading of stepping or foot slip; W5 and W7 are authoritative). `decisions` gets its second entry. `docs/probes/ot11/README.md` gains *What the judge is for, and what it does not see*.
2. **The film draws the target marker.** `cli/cadex_cli/film.py` marks a point goal's target with a ring in the overview, the detail and the video, read from the trace's `goal_channels` and each frame's `goal` row (ADR-462). The README's "target marker is not drawn" departure is closed in the product, not in the contract.

## Why

The critic's message named exactly this unit: record the blind spot in the README and `contract.json` as a `decisions` entry held by `test_ot11_contract.py`, say that nothing is re-evaluated, draw the reach target marker with a regression test that fails before it, and declare P1 `met`. It also accepted P2 and P3 as met on the folded evidence and asked this record to declare both. Target: frontier nodes `rough-shore-6557` (P1), `damp-flame-5523` (P2), `even-nest-5028` (P3). I did what was asked; one placement differs from the first attempt and is noted under Method.

## Method

- **Known limit.** Written from the receipts, and the test reads them: `retained/judge-w2-2-seed-{1101,1110}.json` and the four `retained/probe-marks-{a,b}-w2-2-seed-*.json` give eighteen calls, all scoring V2 = 2; `retained/p2-w2-2-evaluation.json` gives step shares 8.5 % and 3.6 % (W5 limit 70 %) and slip shares 60 % and 81 % (W7 limit 15 %) on the same seeds. `test_the_judges_blind_spot_on_stepping_and_slip_is_a_known_limit_and_the_predicates_are_the_authority` holds the JSON, the page and those receipts together and asserts the rubric digest, the bar and the confirmation rule are unmoved.
- **Placement.** I first put `jobs` and `known_limits` inside `judge`. `test_ot11_judge.py` pins that block's key set ("the frozen judge block is as it was: the procedure adds beside it"), so they moved to a top-level `judge_scope`, the way ADR-460 added `judge_procedure`. The frozen block is byte-for-byte what it was.
- **Contradictions.** The contract records the owner's sentence ("the predicate wins, and the disagreement is recorded") and adds no rule of its own: a judged seed under the bar is reported as under the bar with the predicate beside it. The bar is not lowered for that case.
- **Marker design.** A hollow ring drawn over the rendered frame, not a depth-tested solid: a ball at the target would vanish inside the hand exactly when a reach succeeds. Cyan `#6FF0F0` (the dashboard's `--info`, used by no appearance role) inside a rim of the scene's background, radius 9/256 of the frame edge. The overview's window and the video's hold every target; the detail holds them when there is no floating base; a detail that follows a base keeps the design's size and reports `marked_frames`. `video._studio_frames` gained optional `held` and `overlay`; a run's studio video passes neither.
- **No silent unmarked film.** If the report's row says a seed drew a point goal and the trace names none, the film is refused with that reason.
- **Regression tests.** Six new tests in `cli/tests/test_film.py` (ring read back from both sheets' pixels at the projected target of each frame's own time, hollow, one jump at the switch; absent without a point goal; whole when the target is inside a solid; fixed window holds it, following window does not; every video frame marked; malformed goals refused). Run against `film.py` and `video.py` at `339b8bf1`: all six fail (8 failed, 33 passed, two more through the updated `windows` fixture).
- **Byte identity.** Seed 1101 of `ot11-w2-negative` drawn from its stored trace into scratch directories by the film at `339b8bf1` and by this one, nothing written to the project: overview `0a31b81b…` and detail `911e522d…` from both (no inventory, every part as shell).
- `test_ot11_judge.py`'s "not adopted" check said `"marks" not in film_source`; it now checks for the floor-marks patch's own names (`_marks(`, `def touched`, "floor mark") and expects decisions `["ADR-454", "ADR-463"]`.
- Docs: `docs/CLI.md` (*The film*, and the `test_film.py` row), `docs/DECISIONS.md` ADR-463.

## Result

- **P1 is met on its list.** The contract freezes spec, seeds, pass rule, judge and bar for walk, reach and balance; both known negatives are measured and fail for the stated reasons; the judge's blind spot is a recorded limit; the film is the frozen filmstrip, marker included.
- **Nothing frozen changed, so nothing was re-evaluated.** No seed, condition, predicate, threshold, rubric line, judge input, judge instruction or bar moved. Every earlier reading and score stands.
- **P2 and P3 are declared met** on the critic's acceptance of the evidence already folded (ADR-455 to ADR-459 for P2, ADR-462 for P3). The owner's checkboxes are untouched.
- `pixi run python -m pytest cli/tests`: 1219 passed, 1 skipped (1212 and 1 before). `pixi run test-engine`: 2507 passed, 57 skipped, as before. No packaged gate: no engine, protocol or payload file changed. No new dependency. Nothing removed.

Concerns and assumptions for the next iteration:

- **The marker has been drawn on hand-written traces only.** No arm with a point goal has been evaluated through the product. The engine's trace shape is pinned on the engine side (`test_dynamics_goal_model.py`) and the film's reading on the CLI side; the refusal above is what makes a drift between them loud. The first ot11 reach evaluation is the first real marked film, and the judge has never seen a marked sheet.
- **A single still view cannot give the target's depth.** The ring is a screen position; the overview (35° round) and the detail (side-on or front) together locate it. Reach error is Q2's to measure, and the judge is not the authority for it.
- The film's `style_sha256` changed with its source. The retained receipts keep the digest they were drawn under; any new film of the two negatives would carry the new one with the same pixels.
- Next, per the critic: P4, the loop architecture ADR, balance first.

Dispatch closed: 1 unit — the judge's blind spot recorded as a known limit with nothing re-evaluated, the target marker drawn in the film with regression tests, and P1, P2 and P3 declared met.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 181a2b0252248df9f42ab249e859c6cfe0fd9feb

## State Impact

- target: rough-shore-6557 — status open -> met. P1's list is closed (ADR-463, commit 181a2b02): the judge's blind spot on stepping and slip is a recorded known limit in contract.json (judge_scope, second decisions entry) and README, with W5 and W7 authoritative and nothing re-evaluated because no frozen item changed; the film now draws the target marker the frozen filmstrip text states. Owner's checkbox untouched.
- target: damp-flame-5523 — status open -> met, on the critic's acceptance of the folded evidence (ADR-455 to ADR-459: assembly.success in xscript, cadex evaluate, the report with per-seed and per-predicate verdicts, reward by term, terminations, the three metric families, film and video on the dark floor, the dashboard's Evaluation tab, w2-2 as a failing fixture). New in this unit: the film marks a point goal's target. Owner's checkbox untouched.
- target: even-nest-5028 — status open -> met, on the critic's acceptance of the folded evidence (ADR-462: assembly.goal, goals drawn per episode by one algorithm the engine, the reference runner and the trainer run, a drift test, no JAX or MJX in the engine). Owner's checkbox untouched.
- target: chilly-union-8972 — cadex evaluate's film marks where an episode was asked to go (ADR-463, commit 181a2b02): a trace with a point goal is drawn with a hollow cyan ring over the solids at the target in force at each frame's time, in the overview, the detail and the video; the film block carries target, marked_frames and marker; a seed whose report drew a point goal and whose trace names none is refused; a trace with no point goal is drawn byte for byte as before. Only hand-written traces so far: no real reach has been filmed.
