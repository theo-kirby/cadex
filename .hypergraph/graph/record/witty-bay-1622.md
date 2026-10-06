---
node_id: 7b0198e9-0f57-5842-9677-1f956eb2a646
slug: witty-bay-1622
title: 'G2 style fix: the roll limit is bracketed outward from the standing pose (ADR-567)'
created_at: '2026-10-06T17:07:40+00:00'
parents:
- wandering-dune-8500
summary: ''
---
## What

ADR-567: the `printed-legged-robot` style's MEASURE WHERE THE FEET MEET procedure now brackets the inward hip-roll meeting angle outward from the standing pose, one sweep step at a time, records the last clear angle and the first contact, and sets the limit at least two sweep steps short of the first contact. It warns that a wide range's `first_contact` is counted from the lower limit, so on a negative inward side it is the deepest contact, and a limit set from it lies inside the collision. The opened-wide procedure is gone.

## Why

The critic's named unit after `wandering-dune-8500`: the second fresh session showed the ADR-566 wording, taken literally, sets a roll limit inside a collision (feet meet at −20°, a range opened to −45° reports about −35°, two steps short gives −25°). A live guidance defect outranks H1. Engine semantics are deliberately unchanged, as the critic asked: `first_contact` stays lowest-first, which `docs/INTEGRATION.md` already documents correctly.

## Method

- Test first: `test_the_roll_limit_is_bracketed_outward_from_the_standing_pose` in `src/Mod/cadex/cadex_tests/test_agent_guidance.py` pins the bracketing phrases, the deepest-contact warning, their absence from the base, and the absence of `inward limit opened wide` / `read that joint row`. It failed on the ADR-566 style (`1 failed, 10 passed`), then passed after the edit (`11 passed`).
- The ADR-566 test dropped its `short of that measured angle` phrase (the new wording is `short of the first contact by at least two sweep steps`, pinned by the new test); every other ADR-566 phrase is still asserted.
- `cli/tests/test_agent_guidance.py`: a project that chose the style receives `bracket it outward from the standing pose`, and the base does not.
- `docs/DESIGN-LANGUAGE.md` §5 and `docs/probes/orun4/LESSONS.md` (row L7 and the FRESH-SESSION-2 paragraph, which called the defect open) carry the same procedure.

## Result

The style no longer tells an agent to read a roll limit off a wide range's `first_contact`; it brackets the meeting angle outward from the standing pose and sets the limit two sweep steps short of the first contact, both angles recorded.

Gates, after `pixi run build-engine`: `pixi run test-engine` 2601 passed, 58 skipped (337 s). CLI suite with the GPU hidden, in thirds: 400 passed (167 s), 353 passed 1 skipped (331 s), 443 passed (128 s). A single-command whole-suite run hit the 590 s shell limit before finishing (the thirds sum to about 10.4 min, still above the owner's 8-minute target); it was stopped, not failed, and the thirds are the gate of record.

Defects found by the second fresh session and not fixed here (from `docs/probes/orun4/FRESH-SESSION-2.md`), recorded so a later unit can take them:
- **`cadex smoke` false positive, distance mismatch:** an exact-geometry pre-check refused the design on a distance mismatch under 1e-5 mm on a pair 70 mm apart (a tolerance far tighter than the geometry's).
- **`cadex smoke` false positive, threads:** threaded screw engagement counted as overlap.
- Not a Cadex defect, kept for context: the session's hip roll sat at stall in single support.

Assumption: the bracketing loop is worded for a revolute hip roll with a declared sweep step; a slider-limited case is not covered and does not arise in this style. The ledger's G2 rows are now all evidenced and the guidance defect is closed, so narrow-beacon-6703 moves to working; G2's fresh-session proof stands on `ancient-trail-9417` and `wandering-dune-8500`. The tail is two records (this and `wandering-dune-8500`). Next unit per the critic: H1.

Dispatch closed: 1 unit — style's roll-limit procedure brackets outward from the standing pose (ADR-567)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: c651ea36e3432106f4d0171d8282c3a61cf286b1

## State Impact

- target: narrow-beacon-6703 — working: the printed-legged-robot style brackets the inward roll meeting angle outward from the standing pose and sets the limit two sweep steps short of the first contact (ADR-567), closing the guidance defect the second fresh session found; the ledger and both fresh-session proofs stand
