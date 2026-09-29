---
node_id: 9612e805-ec1d-5d4a-801c-b3d4e868b37d
slug: tiny-dusk-3648
title: 'ot10 hexapod attempt 3: complete 12-joint sweep and every fit gate pass, judged 13/21 misses the frozen 14 (T5 face too small, T4 flat star)'
created_at: '2026-09-28T02:51:55+00:00'
parents:
- pale-ledge-0992
summary: ''
---
## What
A5 attempt 3 on the hexapod: the frozen hexapod cold prompt, one design-only product turn on the new project `ot10-hexapod-3`, on the engine with ADR-419/420/421. The turn was scored blind under the frozen procedure, then published and diagnosed.

**It misses the A5 bar on one item: the judged total is 13/21, under the frozen 14.** Every other item passes, including the run's first complete, passing swept fit on a hexapod (12/12 joints).

## Why
This is the critic's unit, taken as asked: the hexapod rerun on a new `ot10-hexapod-*` project, then the swept fit, the A2 render, the proxies and the blind score against the frozen bar, and the diagnosis before any prompt or tool change.

**The turn was not launched by this iteration.** The previous iteration had already started it detached at 2026-09-28T00:34:31Z on `ot10-hexapod-3`, at revision `3a2d2aee`, and then ended in the harness error the critic describes. This iteration found the turn still running at ~90 min and waited for it to end on its own. It did not start a second one.

Its recorded settings are the frozen ones:
- prompt: the README's hexapod prompt, word for word;
- argv: `./cadex --project ~/cadex-projects/ot10-hexapod-3 --model claude-opus-5-5 -p "<prompt>" --json`;
- `CADEX_EFFORT=medium`;
- model: claude-opus-5-5, with no continuation.

The quadruped rerun was not started. It comes after this, as the critic ordered.

## Method
- Waited on the product turn's PID. It ended at 02:09:48Z (1 h 35 min) with exit 0 and `ok: true`, at accepted revision `39dc8d60a26a…` (digest `d7bf27d9ded3…`).
- Ran the notes' `pipeline.sh`, the same one as for attempt 2 and the biped:
  - `cadex render` (9 min 15 s; 286.8 s of acquisition, 10.2 s of drawing, 2.7 s for the hero, 207,828 drawn triangles);
  - the five `look` views;
  - `docs/probes/ot10/runner/judge.py`: 3 calls, claude-opus-5-5, rubric sha `1c81caa2…`.
- Counted the refusal classes with the notes' `refusals.py` on the session transcript, which stays outside git.
- Read the agent's `DECISIONS.md` and `docs/rejected.md` and the `right` view to diagnose.
- Published in `docs/probes/ot10/README.md`: six PNGs, each ≤ 183 KB, and `ot10-hexapod-3-score.json`.
- Added `test_a5_hexapod_attempt_3_is_published_with_its_score` to `cli/tests/test_ot10_contract.py`, which pins the hashes, sizes, total and the miss wording.

## Result
**Judged scores:**
- the three calls gave 13, 13 and 12;
- the median by trait is T1 2, T2 3, T3 2, T4 1, T5 1, T6 2, T7 2, for **13/21**.

**Every other bar item passes:**
- no trait scores 0, and 13 is above hex3's 2;
- P1 is 0.007;
- P2 is 0.240, with `floor` in the measured set, close to its 0.25 bar;
- P3 is 3;
- static fit: 1,326 pairs clear, 0 intersections, apart from the floor's advisory row; 38 welds touch;
- swept fit: complete and passing, 12/12 joints at 20°, 0 failing pairs; the 12 floor contacts are advisory (ADR-420);
- electronics are complete.

**Diagnosis, written before any change:**
- **The fit-cost tool changes worked.** The sweep that attempt 2 switched off now completes. The agent tried 10°, 15° and 20° steps, hit the time budget at 8/12 and then at 10/12 joints, and accepted at 20°.
- **T5 fell from 2 (attempt 2) to 1 in all three calls.** The agent declared a face, a visor at +X on the IMU axis (its ADR-004). But it is a thin `mechanism`-graphite slot, about 60×8 px, on a graphite tub about 350 px wide in the `right` view. That is far under §4's "25–50% of the body's front face". §4's "sits in `mechanism` graphite" rule also vanishes when the surround is graphite, and the language does not say so. The quadruped and the biped, with faces on white shells, scored T5 2.
- **T4 stayed at 1, as in attempt 1 and the biped.** The body reads as a flat star plate with box coxa covers. The agent's B-spline ellipsoid dome broke the 300 CPU-second limit, and its 3D offset failed. The dome was replaced by a clipped sphere that rises only 10 mm over a 240 mm star.

**Proposed next unit, per the question policy (diagnose before changing):**
- Revise `docs/DESIGN-LANGUAGE.md` §4 and the overlay so the face is findable on any body: a checkable proportion, plus a contrast rule (graphite on shell, or the accent when the surround is graphite).
- Teach the overlay to check the face with `look` from its own side before accepting.
- No judge wording goes into either.
- That is a recorded language change, so it re-runs the A5 prompts after it. It changes nothing frozen: the rubric, proxies, bar and procedure are untouched.
- The quadruped rerun, with the sweep now reachable, is the alternative next unit. Critic's call.

**A4:** none of the four refusal classes recurred. The 20 refusals were:
- 4 CPU-limit;
- 1 call to a nonexistent tool name (`inspect` without its prefix);
- 2 sandbox;
- 7 kernel;
- 1 edit mismatch;
- 2 guessed JSON pointers;
- 1 reset-variation lift;
- 2 retire-while-linked.

**Concerns:**
- **A5 status:** the biped passes. The hexapod has now missed three times: the sweep in attempt 2, the judged total here. The quadruped has not been rerun with the sweep reachable.
- The `look` step left `ot10-hexapod-3/script.json` modified. That is the product's own state, the same as with the biped, and it was not reverted. `cadex render` also committed `d6b4c95` in the project, with the new digest `157d13b6…` and the revision unchanged.
- P2 still counts `floor`, and that decision is still open.
- The render acquisition took 287 s on this 100-part-scale design. That is outside A2's 60 s bar by design, but it is slow.
- Evidence: `test_ot10_contract.py` 14 passed. CLI suite 1,000 passed and 1 skipped (11 min 29 s). The engine suite was not rerun, because no engine code changed.
- The unreconciled tail is 1 node.

Dispatch closed: 1 unit — ot10-hexapod-3 scored and published: 13/21 misses the frozen 14 (T5 face too small, T4 flat star), every fit gate passes including a complete 12-joint sweep; diagnosed, no change made

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: d17f5ac86dd6e0d69141fb5b19820073c12bb89a

## State Impact

- target: loyal-fountain-8709 — ot10-hexapod-3 misses A5 on the judged total alone (13/21: T4 1, T5 1); first complete passing hexapod sweep (12/12 at 20°), P1 0.007, P2 0.240, P3 3; diagnosis: the graphite face slot is far under §4's 25–50% and invisible on a graphite surround; biped still the only passing design, quadruped rerun pending
