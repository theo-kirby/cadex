---
node_id: 780fcc71-1933-5f58-9371-711299192d51
slug: old-star-3367
title: A welded pair does not define the joint it cannot move (ADR-374)
created_at: '2026-09-16T20:21:28+00:00'
parents:
- loyal-flame-8896
summary: ''
---
## What

ADR-374: a swept pair row now says whether the joint being swept can move that
pair (`relative_motion`), and the CLI's `fit.sweep` joint rows read their
minimum distance, maximum common volume and first contact over the moving
pairs alone, counting them as `pairs_moving` beside `pairs_measured`.

Engine: one key on the row in `_sweep_joint` (`cadex_assembly_worker.py`),
computed on the expression that already decided measure-or-cache, which is
then reused so there is one source of truth. CLI: the three extrema updates in
`sweep_summary` (`cli/cadex_cli/clearance.py`) are guarded by it. A row with no
flag — a revision accepted before this — counts as moving, so an older receipt
reads exactly as it did. Two known-answer tests, both failing on the old code.
`docs/CLI.md`, `docs/XSCRIPT.md` and ADR-374 in the same change.

## Why

This advances **F3** (fit checked across each joint's range) and reaches
**F6/F7** directly. It is the critic's stated condition for acting: a concrete,
untested defect rather than another waiting record.

The probe was taken first and is refused again — `claude-fable-5`,
`seven_day_overage_included` 100 % at `org_level_disabled`, five-hour window at
3 %, exit 1 in 2.37 s, `room: false`. No slot spent; F6's and F7's eight slots
remain unspent. So no design turn was dispatched, per the charter's window
gate, and this iteration took an unblocked engine/CLI unit instead.

The defect: the three numbers a joint row carries are the three facts F3 asks
for, and on any mechanism with welded hardware they were none of them. A pair
the joint cannot move holds its solved-pose measurement at every sample, so a
horn welded flush against the link it turns with — which ADR-372 established is
*correct* design, and which is exactly what a balancer does to horns, bearings
and fasteners — reads 0.0 mm at every angle and takes `first_contact` at the
first sample, the bottom of the declared range. The roll-up took the minimum,
so the weld won every time. Reproduced before touching anything: a knee whose
shin first touches its thigh at 62° reported `minimum_distance_mm: 0.0` and
`first_contact: -90°, [horn, shin]`. ADR-372 fixed this masking on the static
side and did not fix it on the swept side.

## Method

1. Probed the window first (`run.py window --model claude-fable-5`): refused,
   no slot spent.
2. Read the fit surface — `pair_status`, `fit_summary`, `sweep_summary`,
   `attachment_summary`, `_check_fit`, `_check_attachments`, `_measure_clearance`,
   `_sweep_joint`, `extract_tree` — for a reachable defect. Several candidates
   were checked and dismissed as sound: the intent/`fit_failures` agreement
   across the engine/CLI boundary (the engine publishes `minimum_mm: 0.0` for
   `attached`, so both reach the same verdict), the unmatched-declaration hole
   (`assembly.assembly` validates `key <= component_ids`, and
   `_measure_clearance` caps no pairs, so every declaration has a row), and the
   single-pass `moving` expansion (`extract_tree` is breadth-first, so parents
   precede children).
3. Reproduced the roll-up defect against `sweep_summary` directly.
4. Fixed both halves; confirmed the repro now reports 0.4 mm / 62° and that
   unflagged rows still read 0.0 mm / −90°.
5. Engine test: a real-kernel three-sphere fixture — `fixed` at 90° on a
   radius-10 circle, `moving` hinged over [20°, 70°], `carried` welded to
   `moving` and touching it — where nothing the hinge moves ever contacts (the
   two moving pairs meet only at 78.5° and 90°, both outside the range) and the
   weld still reports 0.0 mm and first contact at 20°. It pins the flag on all
   three pairs and both analytic minima.
6. CLI test: the same fixture summarised, plus the same rows with the flag
   stripped.
7. Verified both fail on the old code by stashing each source file in turn.

## Result

Both suites green: `pixi run test-engine` 2148 passed / 53 skipped (280.6 s);
`pixi run python -m pytest cli/tests` 806 passed / 1 skipped (535.9 s). Both
new tests fail on the old code with a `KeyError`. No protocol op, no threshold,
no acceptance behaviour, no `shell/` diff; nothing in `shell/` reads
`clearance_sweep`. The packaged gate was run against a payload
rebuilt and restaged from this change (`pixi run build-engine`,
`pixi run stage-engine`, the staged worker confirmed to carry the new key):
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
test_cadexd_lifecycle.py` 20 passed.

What the next iteration must know:

- **F6 and F7 are still blocked and still wholly unspent.** The probe at this
  iteration read `org_level_disabled` with the five-hour window at 3 %, which
  is the ninth-or-so consecutive refusal. Re-probe before any dispatch; only an
  unrefused probe is evidence. All eight create/continuation slots are intact.
- **This is the eighth product change F6/F7 will run on** (ADR-362, 366, 367,
  368, 370, 371, 372, 373, and now 374), and the second in a row that reaches a
  balancer's welded hardware directly. `docs/probes/ot7/REPORT.md`'s F10
  comparison section counts those changes and is now one behind — whoever
  writes F10 should say nine, not eight, and this is the only bookkeeping this
  unit leaves open.
- **Assumption recorded:** `failing` was deliberately left spanning every pair,
  including rigid ones. A rigid pair that interpenetrates is a real finding and
  the static block reports it too; narrowing the failing set would have been a
  behaviour removal rather than a fix.
- The unreconciled tail is now three records. Reconcile is the critic's call.

Dispatch closed: 1 unit — ADR-374, a welded pair no longer defines the swept
joint it cannot move; engine flag, CLI roll-up, two known-answer tests failing
on the old code, docs and ADR.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 65cbe3ca865402b5cc696fa24979fce79171bd95

## State Impact

- target: chilly-union-8972 — the fit.sweep joint rows read their minimum distance, maximum common volume and first contact over the pairs the joint actually moves, counting them as pairs_moving; a rigid pair no longer pins the minimum at a weld's 0.0 mm or names first contact at the bottom of the range (ADR-374)
- target: forest-wind-0342 — every swept pair row published in clearance_sweep carries relative_motion, true when exactly one side is inside the swept joint's moving subtree (ADR-374)
- target: rapid-grove-9687 — F7 still blocked and wholly unspent; the ninth product change it will run on lands, the second in a row reaching welded hardware
- target: narrow-dune-9454 — F6 still blocked on the same org-level Fable refusal (probed again: org_level_disabled, five-hour 3 %, no slot spent); ADR-374 lands as the ninth product change F6 will run on, and it reaches a balancer's welded horns, bearings and fasteners directly
