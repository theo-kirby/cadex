---
node_id: 91e0f04d-7223-5d1c-82a4-b45f4a00cbe3
slug: zesty-bell-3977
title: 'ot11 grip: coupling contact exclusion only where parts touch (ADR-475); coupled gripper instability measured'
created_at: '2026-10-01T21:01:30+00:00'
parents:
- snowy-snow-8800
summary: ''
---
## What

ADR-475 (commit `2a4169d1`): a coupling (`gears`, `belt`, `screw`) excludes contact between its two components only if they already touch at the solved pose. Pin-like joints still exclude their pair unconditionally.

- `src/Mod/cadex/CadexDynamics.py`: `build_model` collects coupling pairs separately. After `qpos_solved` it runs the model's own contact pass (`_touching_body_pairs`) and adds an exclusion, then recompiles, only for coupling pairs in contact there. Exclusions still appear in `contact_exclusions`.
- `cadex_tests/test_dynamics_goal_coupled.py`:
  - new `test_the_overlapping_grip_targets_are_refused_for_contact[engine|runner|trainer]`, the regression;
  - new `test_a_coupling_is_excluded_only_where_it_already_touches`, covering both sides of the rule;
  - the ADR-474 draw test now asserts that no accepted target overlaps.
- `docs/DECISIONS.md` ADR-475, `docs/XSCRIPT.md` (the contact paragraph) and `docs/probes/ot11/README.md` ("the second gap is closed").

## Why

I did what the critic asked, in its order:
1. Wrote the missing ADR-474 record: `snowy-snow-8800`, parented on `blue-cloud-1514`, with its impact on `salty-isle-4063`.
2. Took the next unit: decide in its own ADR whether exclusion should skip coupling pairs, with a regression test that fails today on 1102/1105/1110, then the engine suite, the cli suite and the packaged gate.

**Deviation: I did not reconcile.** This dispatch's rules forbid the reconcile skill in a work iteration, with no exceptions. The tail is now four records (`silver-light-9977`, `blue-cloud-1514`, `snowy-snow-8800` and this one), well past the three-record trigger, so a reconcile pass is due.

The MJX `equality/joint` measurement comes after this unit in the critic's order and is not done here.

## Method

- The rule is geometric, not authored. Meshed teeth and a nut on its thread overlap by construction, and jaws do not. An authored per-coupling switch was rejected: it would add vocabulary for a fact the solved geometry already states, and the fourth-behaviour rung asks for no new code path.
- Regression check before and after: with `CadexDynamics.py` stashed, the new test refuses no attempt at all (`refused == set()`) and the draw test sees `real == {(1102,1),(1105,1),(1110,1)}`; 7 tests fail. With the change, all 11 pass.
- A static sweep on the probe gripper with hb = −ha: the gap is 32 mm at 0°, 4.34 mm at −10°, and −8.83 mm at −15°. The jaws meet at about −11.5°. Positive angles open them.
- Played the probe gripper with a full-close command (−20°) for 4 s, comparing three cases: coupling plus contact, contact disabled, and coupling disabled.
- `pixi run build-engine` and `stage-engine`, then the packaged gate, the engine suite and the cli suite, all CPU-only.

## Result

**What is true now:**
- Geared jaws collide. All three draw implementations refuse 1102, 1105 and 1110 segment 1 for jaw contact and draw again, and no accepted grip target overlaps on the ten frozen seeds.
- Meshed boxes on a 2:1 gear train stay excluded.
- Uncoupled models, exports and digests are unchanged. No retained bundle has a coupling, since none could be exported before ADR-473.

**Receipts at `2a4169d1`:**
- `pixi run test-engine`: 2543 passed, 61 skipped.
- `cli/tests`, CPU-only: 1290 passed, 1 skipped (19 min 16 s).
- Packaged lifecycle gate against the restaged `cadex-engine-0.0.0-linux-x64`: 23 passed.

**A new defect, measured and not fixed: the coupled gripper is unstable when commanded closed.**
- With coupling and contact, over 4 s the joints swing up to 244° (the limits are ±20°) and the jaws penetrate by up to 10 mm.
- With contact disabled, it still overshoots to 63.8° before settling at ±20°.
- With the coupling disabled, the jaw holds −20° cleanly.
- So the first cause is the soft `equality/joint` row (solref 0.004 at dt 0.002) on two 17 g jaws, driven by a 22.9 N·m/rad servo with limits on both joints. Contact only amplifies it. Excluding the jaws hid this; it did not cause it.

**Concerns for the next iteration:**
- The tail is four unreconciled records, so a reconcile is due.
- The instability above must be diagnosed in the product, with a regression test, before any gripper training. So must whether MJX 3.10 honours `equality/joint` (the critic's next step).
- No grip contract is frozen, and nothing frozen in ot11 moved.
- A non-touching coupled pair now goes through the export's MJX collision-kind check, where it used to be skipped.
- Assumption: body names equal component names in the built model, as the existing exclusion code already relies on.

Dispatch closed: 1 unit — coupled pairs excluded only where they touch at the solved pose (ADR-475, regression fails on the old builder at 1102/1105/1110), suites and packaged gate green; measured a coupled-gripper instability that blocks grip training

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 2a4169d1c7db9349801398213813e1218f8e68a8

## State Impact

- target: salty-isle-4063 — A coupling (gears/belt/screw) now excludes contact only if its two components touch at the solved pose (ADR-475, commit 2a4169d1); pin-like joints still always exclude. Geared jaws collide, so the grip draw refuses the 3 overlapping frozen-seed targets in engine, runner and trainer. Open: the coupled gripper commanded closed is unstable (joints to 244° vs ±20° limits; 63.8° overshoot even without contact), caused by the soft equality/joint row; must be fixed, and MJX equality/joint support measured, before any grip training.
