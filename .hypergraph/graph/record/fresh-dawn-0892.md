---
node_id: cbaa82dd-53ba-5f62-92a4-173fac710944
slug: fresh-dawn-0892
title: F7's biped smokes pass on the re-exported model, and the fix shuts the project (ADR-395)
created_at: '2026-09-20T01:27:23+00:00'
parents:
- weathered-pebble-8544
summary: ''
---
## What

**F7's biped smokes pass — on the model today's engine exports — and the fix
that made it pass shuts the project it fixed (ADR-395).** No prompt was sent,
no model was called, no slot was spent, and `ot7-plover-e` was not touched:
everything below was measured on the copy `ot7-plover-e-reexport`, whose
`continue-2` and `continue-3` remain unspent.

**The measurement.** Re-running the accepted script through the ADR-393 engine
re-exports a model that **agrees with its own solve exactly** — 0 of 29 bodies
disagreeing, worst 8.620781476393591e-33 mm and 1.2074182697257333e-06°,
against the accepted pin's 24 of 29 at 121.86102740417053 mm — and that model
smokes **pass** in 35.0 s: state finite throughout; penetration **0 breaches**
with both shins on the floor at 0.3214283954748017 mm against a 0.5 mm
tolerance; resting after a 0.2683688948842189 mm drop at 0.18159412499621788°
of tilt, base `c_pelvis`, `kind: free`, end speed 1.2e-07 mm/s; the one
termination rule unfired; 51 samples over 1.0 s at 50 Hz on MuJoCo 3.10.0. The
half that never produced a verdict before now does: the exact-BREP check passes
**406 of 406 pairs across all 51 samples** with `initial_pose_agrees: true`.
The control is the same probe on the accepted pin, which reproduces iteration
167's refusal — `initial pose disagrees with published clearance:
('c_bearing_hip_l', 'c_bearing_hip_r')` — exactly.

**The new red line.** `ot7-plover-e` **can no longer be opened**. The restore
pass refuses in 89.4 s with `CADEXD_RESTORE_FAILED` (accepted `a00d1aea…`,
restored `9ef44502…`) and the ADR-389 geometry fallback refuses with it
(`the rebuilt model is not the accepted one`). It is right about the bytes and
wrong about the design: exactly **2 of 90 outputs** changed — the MJCF, and the
training task whose only two differing fields are that MJCF's `sha256` and
`bytes` — while every BREP artifact, every canonical definition and every
solved placement is identical, and two independent rebuilds wrote the same
model bytes. Both the project digest and the geometry digest carry a non-BREP
output's artifact bytes (`project_digest`'s ADR-068 clause and the `else`
branch of `_entries` that the geometry digest shares), so the fallback built
for *the same model serialized twice* has no answer for *the same model
exported better*.

Landed: `docs/probes/ot7/runner/reexport_smoke.py` (the probe),
`cli/tests/test_reexport_smoke.py` (six fixtures), ADR-395, the REPORT.md
iteration-170 section, a REGRESSION.md section, the runner README section, and
the 8.0 KB receipt `docs/probes/ot7/retained/plover-e-reexport.json`.

## Why

The critic's message named this unit exactly: close F7's last open requirement
without a slot by re-exporting `ot7-plover-e`'s retained MJCF through the fixed
engine — the same full-restore path ADR-394's regression half used — and
running `mjcf_agreement.py` and the smoke against the fresh export, recording
exactly why if it still could not.

What I did differently, and why: the restore **refuses**, so there is no fresh
export inside the accepted pin and `run.py smoke` still reads the pre-fix
model. The refusal leaves the rebuilt attempt on disk, so the smoke was taken
on that attempt instead, through the shipped `command_smoke` with its bundle
read from the named attempt rather than from the pin. That is a verdict, taken
without a slot, with a control — and it is not a `run.py smoke` receipt, which
the report and the receipt both say in those words.

Frontier: `rapid-grove-9687` (F7) for the smoke, `forest-wind-0342` (the
engine) and `mild-ledge-7157` (the charter, through F9) for the openability
defect, and `salty-isle-4063` for ADR-393 verified end to end on the design
that found it.

## Method

**A copy, then the tool, then the control, then the result.** `ot7-plover-e`
was copied without its `evidence/`, `agent.json` or git repository; the
original was opened for nothing but reading. `reexport_smoke.py` has three
halves — `restore`, `compare`, `smoke` — and every number in the receipt came
out of the committed tool rather than the scratch script that found the
behaviour: the copy was deleted and remade so the tool's own `restore` produced
the rebuilt attempt the rest measures.

The `smoke` half keeps every check the shipped reader makes — an artifact must
hash to its entry and live inside its attempt, the attempt must have built, the
destination must not overwrite the project or the attempt — minus the one that
cannot hold here, that the result's digest equals the project's accepted
digest. `cli/tests/test_reexport_smoke.py` pins exactly those, plus
`compare`'s ability to find the one changed output among unchanged siblings:
six fixtures, no engine, no MuJoCo, 0.02 s.

The order mattered. The probe was pointed at the **accepted pin** first, where
it reproduced the known refusal, before it was pointed at the rebuild; a tool
that returns `pass` is evidence only once it has been shown returning the known
failure. Determinism was checked the same way: two independent restores of the
same bytes, in two fresh copies, produced the same restored digest
`9ef44502…` and the same model `71b8b39c…`, so the digest moved because the
engine changed and for no other reason.

Verification: `pixi run python -m pytest cli/tests` — **855 passed, 1 skipped
in 553.44 s** (849 before this unit, plus its six fixtures). No engine,
protocol or payload change in this unit, so no engine suite or packaged gate is
implicated; iteration 168's engine run (2195 passed, 53 skipped) and packaged
gate (23 passed) remain the current numbers for the ADR-393 code these
measurements exercise.

## Result

**F7's sixth requirement has a measured verdict for the first time: the biped
passes a bounded holding smoke, on the model its own accepted script exports
under the current engine, with the geometry half passing too.** Whether a
verdict taken off the accepted pin satisfies the bar is the owner's call; the
report claims only what it measured and names the difference in its own words.
F7's other five requirements were already met, and its two continuations are
still unspent.

**What is broken, and it is not F7's alone.** A project accepted before an
engine change to a *derived* artifact cannot be reopened — the ADR-389
geometry fallback cannot distinguish a better export from a changed design,
because both digests include non-BREP artifact bytes. The immediate cost:
`ot7-plover-e`'s remaining continuations are **unspendable**, since a design
turn opens with `restore=True` and would be refused before a provider session
exists (the ADR-386 `unreached` shape). This is the next engine-side unit, and
the smallest candidate change is in `project_geometry_digest`'s entries rather
than in `open_project`. Nothing else regressed: the three retained ot6 copies
open, restore and report 406/44, 276/39 and 105/20 unchanged, because ADR-393
changes nothing they export [rec: weathered-pebble-8544].

**Assumption recorded.** Reading a bundle from a non-pinned attempt of the same
accepted revision is a measurement, not an acceptance: nothing was written into
any project store, the copy's accepted pin and digest are unchanged
(`accepted_pin_preserved: true`), and no `ot7-*` design's script, parameters or
accepted state moved. The charter's no-actor-design-edits rule is intact.

No new dependency. The unreconciled tail is one record deep after this one.

Dispatch closed: 1 unit — F7's biped smokes pass on the re-exported model (0 of
29 bodies out, 406 of 406 pairs clear), taken without a slot and against its
own control, and the same re-export shows that ADR-393 shut `ot7-plover-e`
against `open_project` (ADR-395).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: e6cebcda1ca605c40dc9c16cdf3dddfb5e99fc34

## State Impact

- target: rapid-grove-9687 — F7's sixth requirement has a measured verdict: the biped's re-exported model smokes pass (finite, 0 penetration breaches, resting at 0.268 mm drop and 0.182 deg tilt, 406 of 406 exact-solid pairs clear across 51 samples, frame-0 agreement gate satisfied), with the accepted pin's model as the failing control. No slot spent; continue-2 and continue-3 unspent but currently unspendable, because a design turn opens with restore=True and ot7-plover-e now refuses to open.
- target: forest-wind-0342 — A project accepted before an engine change to a derived artifact cannot be reopened: ot7-plover-e refuses with CADEXD_RESTORE_FAILED and the ADR-389 geometry fallback refuses with it, though exactly 2 of 90 outputs changed (the MJCF and the task pinning its digest) with every BREP artifact, definition and solved placement identical across two deterministic rebuilds. Both project_digest and project_geometry_digest carry a non-BREP output's artifact bytes.
- target: salty-isle-4063 — ADR-393 is verified end to end on the design that found it: rebuilt under the fixed engine, ot7-plover-e's model agrees with its solve at 0 of 29 bodies disagreeing (worst 8.6e-33 mm, 1.2e-6 deg) against 24 of 29 at 121.861 mm before, and the rollout it feeds passes every smoke check.
- target: chilly-union-8972 — docs/probes/ot7/runner/reexport_smoke.py adds restore/compare/smoke halves that measure an accepted design's re-export without writing a store: the smoke half runs the shipped command_smoke with its digest-checked bundle read from a named attempt rather than the accepted pin, keeping every check but accepted-digest equality; cli/tests/test_reexport_smoke.py pins it with six fixtures.
- target: mild-ledge-7157 — F9's 'existing projects keep opening' has one measured exception, bounded and explained in REGRESSION.md: ot7-plover-e alone, from ADR-393's changed export; the three retained ot6 copies are unaffected. CLI suite 855 passed, 1 skipped in 553.44 s.
