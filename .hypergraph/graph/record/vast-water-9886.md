---
node_id: b5a29178-70dd-5f8c-80ee-1103798e7438
slug: vast-water-9886
title: A gap the motion closes is a failing fit (ADR-378)
created_at: '2026-09-16T22:32:28+00:00'
parents:
- humble-harvest-9420
summary: ''
---
## What

ADR-378. The swept fit block could fail a pair on exactly two things: a
common volume over the threshold, and a pair the engine could not measure.
The **minimum distance** it measured through each joint's range — the whole
reason for sweeping — was reported and held against nothing, so F2's third
and fourth checks (a declared clearance below its minimum, an undeclared pair
closer than the default 0.1 mm) existed at the solved pose only. Reproduced
on real OCCT solids before changing anything: a hinge that takes two unit
spheres from **10.751594 mm** apart at the solved pose to **0.04 mm** at 90°,
never touching, zero common volume at all 71 samples — static `pass, 0
failing`, correctly, and swept `pass, 0 failing` with the 0.04 mm printed
beside it.

Fixed: a swept pair fails `below clearance` against the pair's own minimum,
under three narrowing rules that keep the swept block strictly additive to
the static one — only a pair this joint moves, only a pair the static block
calls clear, never a declared contact or a welded pair. Replayed over all
twenty-one retained ot7 `clearance.json` files the new rule adds **zero**
failures, so no number in the closing report moves. Two known-answer
fixtures, the real-OCCT one in the engine suite and three in the CLI suite,
two of them red on the old module. `docs/CLI.md`, `docs/XSCRIPT.md`, the
agent's system prompt, `docs/DECISIONS.md` and
`docs/probes/ot7/REPORT.md` carry it. CLI only: no engine, protocol, payload
or `shell/` change.

## Why

The critic's message: keep F6 next and dispatch only when the availability
probe permits; if capacity remains refused, make no change unless another
concrete reproduced defect advances an F criterion, and do not expand the
smoke success criteria to fill waiting time.

Availability first. `run.py window --model claude-fable-5` was refused again:
`seven_day_overage_included` 100 %, `overageDisabledReason:
org_level_disabled`, five-hour 13 %, exit 1 in 2.42 s, `room: false`. Sixth
refusal on the same organisation setting. No F6 dispatch, no model switch,
no frozen prompt spent.

So the unit is a defect, and deliberately **not** in the smoke: F6 and F7 are
each judged on "zero failing static **and swept** fit checks", and the swept
half of that bar could only be failed by an overlap. That is the same error
class ADR-377 found in `support` — a number measured, printed and judged
against nothing — in the one other gate the two remaining designs must clear.
The agent's own system prompt said so in plain words ("The swept verdict
judges overlap only"), which is how the hole survived four F5 turns.

## Method

1. Probed availability (above). Refused; nothing dispatched.
2. Read `sweep_summary` against F2's four checks and `_check_fit`. The swept
   path has no intent lookup and no distance threshold; `_check_fit` runs on
   the solved-pose rows only.
3. Searched the retained evidence for a real occurrence before building one:
   across all twenty-one ot7 `clearance.json` files, no pair closes below its
   minimum through a range that the solved pose found clear. The retained ot6
   designs do not either — Finch's knees hold 1 mm through 0–90°
   (`docs/probes/ot7/sweep/README.md`). So the defect is reachable but not
   yet realised, which is why a fixture had to produce it.
4. Reproduced on real geometry, not argued from the code. Two unit spheres,
   the fixed centre 12.04 mm from the hinge axis and the moving centre 10 mm
   from it, swept 20°→90° at 1° through the real `_measure_joint_sweeps`
   under `FreeCADCmd`. Measured: solved 10.751593998 mm, swept minimum
   0.039999999 mm, maximum common volume 0.0, no first contact. Fed through
   the current `fit_summary`: **`sweep pass`, 0 failing**.
5. Fixed in `cli/cadex_cli/clearance.py`. `sweep_summary` takes `minimum`,
   reads the solved-pose rows of the same published value for their `intent`
   and their static verdict, and fails a swept row `below clearance` when
   `minimum_mm - minimum_distance_mm` exceeds the ADR-353 slack. The row
   carries `minimum_mm` and the solved pose's `distance_mm` beside the swept
   extrema.
6. The three narrowing rules are what make it additive, and each has its own
   reason: a rigid pair repeats a number the static block already judged
   (ADR-374); a pair failing at the solved pose is named there once; a
   declared contact or a fixed joint's implied `attached` intent is exempt
   exactly as it is at rest (ADR-372).
7. Verified the "no receipt moves" claim rather than asserting it: replayed
   `fit_summary` over all twenty-one retained `clearance.json` files under
   both modules. Identical failing counts, zero new swept failures.
8. Wording followed the behaviour: `sweep fail: N overlapping pair(s)` became
   `N failing pair(s)` in the progress line and the prose report, each swept
   pair line gained its status, and the system prompt's "judges overlap only"
   paragraph was replaced with the three failure kinds and the two
   exemptions.
9. Tests. Engine:
   `test_a_hinge_that_grazes_closes_a_gap_the_solved_pose_cannot_see`, the
   real-OCCT fixture above, asserting the analytic 0.04 mm and that the
   common volume is zero everywhere — it pins that a real sweep produces a
   close approach a volume-only rule is blind to by construction. CLI:
   `test_a_gap_the_motion_closes_fails_the_swept_check`,
   `test_the_swept_minimum_is_the_one_the_solved_pose_held_the_pair_to` and
   `test_the_swept_check_adds_to_the_solved_pose_check_and_never_repeats_it`,
   carrying those measured numbers. The first two are red on the old module
   (`assert 'pass' == 'fail'`); the third is green on both, which is the
   point of it. A fourth case joined `test_mcp_protocol.py`'s progress-phrase
   parametrisation.

## Result

The swept fit block now applies the pair's own minimum through the range.
A design whose motion closes a gap it declared, or closes below 0.1 mm with
nothing declared, reaches the agent as a named failing pair with both
numbers, and `fit.sweep.verdict` is no longer `pass` for it. F6's and F7's
"zero failing swept fit checks" is a bar an overlap-only rule could not
express.

Evidence: CLI suite 818 passed, 1 skipped in 556.65 s, plus a 369-passed re-run of every
file importing the agent module after the system-prompt edit; engine suite 2,152 passed, 53 skipped in 321.32 s. No engine, protocol or
payload code changed, so no packaged gate applies to this unit;
`test_project_tool_surface.py` 13 passed, and the tool surface itself is
unchanged — only the prompt's description of what the swept verdict judges.

Concerns and assumptions the next iteration needs:

- **F6 remains blocked on provider capacity, every slot unspent.** Sixth
  consecutive refusal, `org_level_disabled` at the organisation level, which
  no role here may change. The probe costs no slot; keep probing before each
  dispatch attempt and do not fall back to another harness.
- **Assumption, stated because it is a judgement call:** a swept pair that
  already fails at the solved pose is *not* repeated in the swept block. The
  alternative — reporting it in both — would inflate every failing count on
  designs like retained Finch and Robin, whose undeclared zero-gap seatings
  fail statically in their dozens, and would tell the agent nothing about the
  motion. If a later unit wants "worse through the range than at rest" as a
  distinct finding, it is a new status, not a loosening of this one.
- The product is now **twelve** changes newer than the one F5 ran on; the
  report's product-version section lists all twelve and is what an F6 or F7
  row must be read across.
- The unreconciled tail is two records before this one, so reconciliation is
  not yet due.

Dispatch closed: 1 unit — ADR-378, the swept fit check now holds each pair's
measured minimum against the minimum the design gave it, reproduced on real
OCCT solids and adding zero failures to every retained receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 61353ac804fe153f8356fb3fb8d132b0eae7a694

## State Impact

- target: wild-horizon-5461 — The swept fit block the agent's build reply carries now judges the minimum distance it measures, not only overlap (ADR-378). A swept pair fails `below clearance` when its minimum through a joint's range misses the pair's own minimum — its declared `clearances=` value, or `minimum_clearance_mm` (0.1) for an undeclared pair — by more than the ADR-353 slack. Reproduced on real OCCT solids before the change: a hinge taking two unit spheres from 10.751594 mm apart at the solved pose to 0.04 mm at 90 degrees, never touching, zero common volume at all 71 samples, read `sweep pass, 0 failing` with the 0.04 mm printed beside it. Three narrowing rules keep the block strictly additive to the static one: only a pair this joint moves (ADR-374), only a pair the static block calls clear, and never a declared `contact` or a fixed joint's implied `attached` intent (ADR-372). Replayed over all twenty-one retained ot7 clearance.json files the rule adds zero failures, so no published receipt moves. `sweep_summary` takes `minimum` and publishes it in `thresholds`; the failing row carries `minimum_mm` and the solved pose's `distance_mm`. The progress line and prose report say `N failing pair(s)` rather than `N overlapping pair(s)` and each swept pair line carries its status; the system prompt's "the swept verdict judges overlap only" is replaced by the three failure kinds and the two exemptions. Engine suite 2152 passed, 53 skipped; CLI suite 818 passed, 1 skipped, plus 369 passed re-running every file importing the agent module. Commits 6ce89fff, 61353ac8.
- target: narrow-dune-9454 — F6 remains blocked on provider capacity with every slot unspent: the sixth consecutive availability probe of `claude-fable-5` was refused at the organisation level (`org_level_disabled`, seven-day-overage window 100 %, five-hour 11-13 %, exit 1 in 2.42 s, `room: false`), so no frozen create prompt was dispatched and none was spent. The product F6 will be judged on is now twelve changes newer than F5's, the twelfth being ADR-378: until it, the "zero failing swept fit checks" half of F6's bar could only be failed by an overlap.
