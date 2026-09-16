---
node_id: 92647aa2-14af-51be-ac4e-adaf853dcc76
slug: humble-harvest-9420
title: A design that toppled and settled is not resting on the floor (ADR-377)
created_at: '2026-09-16T22:09:08+00:00'
parents:
- clear-spark-8613
summary: ''
---
## What

ADR-377. `cadex smoke`'s `support` check passed any free base that was
touching the environment floor and had stopped moving — which a design that
falls over satisfies the moment it lands. Reproduced on F6's own mechanism:
the retained ot6 balancer, copied to `ot7-robin-smoke` and smoked for the
first time in this run, topples at zero torque in 0.38 s and comes to rest
**101.3° over, 43.5 mm lower, chassis on the floor**, and `support` reported
`pass: true`. The receipt already carried `tilt_degrees: 101.3` and no check
read it. Fixed: the base's attitude is read **against the pose its accepted
keyframe gave it** and must stay within `--max-tilt-degrees`, default 30°.
Two known-answer fixtures, the first red on the old child.
`docs/CLI.md`, `docs/DECISIONS.md` and `docs/probes/ot7/REPORT.md` carry it.
Commits `cf06d2b8`, `b5a66272`.

**Correction, as the critic asked:** `clear-spark-8613`'s closing line said
the unreconciled tail was three records and the handoff said four. Both are
wrong. `fcd0c5ab` reconciled through `solar-arrow-5671`; only
`clear-spark-8613` was pending before this record. No separate housekeeping
record was written, and reconciliation is not due.

## Why

The critic's message, in order: correct the tail count; keep F6 next and
dispatch only after the availability probe permits; while refused, make no
change unless a concrete reproduced defect advances an F criterion.

Availability first. `run.py window --model claude-fable-5` at 22:05 UTC was
refused outright again — `seven_day_overage_included` 100 %,
`overageDisabledReason: org_level_disabled`, five-hour 11 %, exit 1 in 1.97 s,
`room: false`. Fifth refusal on the same organisation setting. The probe
spends no slot. So no F6 dispatch and no model switch.

That left the question F6 runs into the moment it *is* dispatched: F5–F7 each
end on "a passing smoke rollout", and the only two designs left both fail by
falling over. The smoke had never been run on a design that falls. Running it
on the retained balancer — no slot, no design edit, a copy — found the defect:
the gate that F6 and F7 must clear cannot tell standing from fallen. That is
the worst error class for this run's mission, since it would let an F6 or F7
receipt claim a pass for a robot lying on its side.

## Method

1. Probed availability (above). Refused; no design turn dispatched.
2. Read `smoke_runner.run`'s four checks against `docs/CLI.md`. `support`
   passes on floor existence, `touching_floor` (any geom, not the base's),
   linear speed under `--rest-speed-mm-s`, and finiteness. `tilt_degrees` and
   `drop_mm` are measured, reported and read by nothing.
3. Reproduced on real geometry before changing anything: copied
   `ot7-retained-robin` to `ot7-robin-smoke` and ran `cadex smoke --seconds 2`.
   Verdict fail, but `support.pass: true` with `tilt_degrees 101.3`,
   `drop_mm 43.5`, `speed_mm_s 9.4e-06`. Robin's verdict failed only on its own
   termination rule (fired at 0.38 s) and 2.7 mm of chassis in the floor; a
   design with no exported task and a softer landing would have passed.
4. Built a fixture whose known answer isolates it: `TOPPLING_TOWER`, a 100 mm
   tower standing 15° over — past the 11.3° its footprint holds — at a tenth of
   Earth's gravity with stiff contact, so the landing sinks 0.2 mm, under
   tolerance. On the old child, run by path from `git show HEAD:`, that
   rollout is **`verdict: pass, failing: []`** at 90° absolute tilt and 40.9 mm
   of drop. That is the defect in one line.
5. Fixed: `tilt_from_start_degrees`, the angle between the base's local +Z at
   the keyframe and at the last sample, joins the pass condition under
   `--max-tilt-degrees`. Measured against the keyframe rather than the world,
   so a base *modelled* lying down and holding reads 0 rather than 90.
   `tilt_degrees` keeps its old absolute meaning and is still reported.
6. The default is a threshold, not a guess: Finch standing ends 9×10⁻⁶ ° from
   its keyframe attitude, the resting-block fixture 0°, the toppled balancer
   101.3°. 30° is orders above every settled measurement and well under any
   topple, and it is a flag.
7. Tests: `test_a_design_that_topples_and_settles_fails_support_on_its_attitude`
   (75° from the keyframe, the only failing line, passing again at 120°) and
   `test_a_base_accepted_lying_down_holds_that_pose_and_passes` (90° absolute,
   0° from its keyframe, pass) — the guard against reading attitude absolutely.
8. Re-ran both real designs on the new code: Robin now reports
   `support: comp_chassis has turned 101.3° away from its accepted pose
   (limit 30°)`; Finch's standing smoke still passes support at 9×10⁻⁶ °.
   Finch's overall verdict fails on ot6's known screw-engagement overlaps,
   which its earlier receipt did not carry because that receipt predates the
   exact-BREP component check — not this change.
9. Full CLI suite: **814 passed, 1 skipped, 530.97 s** (812 + the two new
   tests). No engine change, so no engine suite or packaged gate was required.

## Result

The smoke gate F5–F7 end on can now tell a design that held its pose from one
that fell onto the floor, on both fixtures and on the two real designs
measured. `docs/probes/ot7/REPORT.md`'s product-version list is **eleven**,
not ten: ADR-377 is a change an F6 or F7 receipt reads, unlike the runner-only
ADR-376.

One interpretation call, made under the question policy and recorded here:
the charter's F8 wording is "the design rests on the environment floor", and a
toppled robot lying still on the floor satisfies that sentence read
literally. I read it as the charter's pair — "rests on the floor **or holds
its grounded base**" — meaning the design holds the pose it was accepted in,
and made the change the smallest reversible one: a flag, defaulting to a
measured threshold, reported in the receipt, refusing nothing. Raising
`--max-tilt-degrees` restores the old behaviour exactly. If the owner reads
F8 the other way, one default moves.

**Availability is unchanged and F6 remains blocked.** Five probes now — 14:29,
14:50, 17:02, 21:37 and 22:05 UTC — all refused on the same
`org_level_disabled` setting. F6's four slots and F7's four are unspent; no
`ot7-robin-b` or `ot7-plover-b` exists. F10 cannot close. No frozen prompt was
spent, no `ot7-*` design was edited, and `ot7-retained-robin` is byte-for-byte
untouched: the smoke ran on `ot7-robin-smoke`, a copy, whose receipts stay in
that project directory. No role stopped, started or restarted anything. No new
dependency.

For the next iteration: probe before assuming either way; if it comes back
unrefused, dispatch F6's frozen `robin.create.prompt.txt` into a fresh
`ot7-robin-b`, then F7's `plover.create.prompt.txt` into `ot7-plover-b`. Know
going in that a two-wheeled balancer given no torque falls over in under half a
second, so an F6 smoke pass needs a design that stands unaided — that is now a
measured fact of the run, not a surprise waiting in a receipt. The
unreconciled tail is two records after this one.

Dispatch closed: 1 unit — ADR-377 makes the smoke rollout read the attitude it was already measuring, after the retained ot6 balancer toppled 101.3° and passed its support check; F6 stays blocked on a fifth refusal at 22:05 UTC with all eight slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: b5a66272b25b153f09e9eebf74e2b478f4f9b48c

## State Impact

- target: chilly-union-8972 — cadex smoke's support check gains the base's attitude (ADR-377): tilt_from_start_degrees, the angle between the base's local +Z at its accepted keyframe and at the last sample, joins the pass condition under --max-tilt-degrees (default 30, measured against Finch's 9e-06 standing and the toppled balancer's 101.3). Read against the keyframe, so a base modelled lying down and holding reads zero; tilt_degrees keeps its absolute meaning. Reproduced on the retained ot6 balancer copied to ot7-robin-smoke, which toppled 101.3 degrees and passed the old support check, and on a toppling-tower fixture the old child passes with an empty failing list. Nothing is refused; raising the flag restores the old behaviour. docs/CLI.md updated; CLI suite 814 passed, 1 skipped.
- target: narrow-dune-9454 — F6 stays blocked: a fifth probe at 2026-09-16T22:05Z was refused on the same org_level_disabled setting (seven_day_overage_included 100 %, five-hour 11 %), all four slots unspent and no ot7-robin-b. Its mechanism was measured meanwhile: the retained ot6 balancer at zero torque topples in 0.38 s and rests 101.3 degrees over, so an F6 smoke pass requires a design that stands unaided, and the smoke check that F6's bar ends on now reports the topple instead of passing it (ADR-377).
- target: rapid-grove-9687 — F7 unchanged and still blocked behind F6 by the same refusal, all four slots unspent and no ot7-plover-b; ADR-377's attitude check applies to its smoke too, a biped's failure mode being the same fall.
- target: mild-ledge-7157 — ot7's product-version list in docs/probes/ot7/REPORT.md is eleven changes, not ten: ADR-377 is the first since F5 that an F6 or F7 receipt reads through its smoke rather than its fit. Correction to clear-spark-8613 and the iteration 106 handoff: fcd0c5ab reconciled through solar-arrow-5671, so only clear-spark-8613 was pending, not three or four.
