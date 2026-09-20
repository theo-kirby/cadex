---
node_id: 516d7f7b-0810-552f-85de-9c2fd3bd6bc6
slug: weathered-pebble-8544
title: The window shut, so ADR-393's reach on the ot6 copies was measured at zero (ADR-394)
created_at: '2026-09-20T00:56:26+00:00'
parents:
- glad-chart-3979
summary: ''
---
## What

**No design turn was dispatched, and F9's other half was re-measured under the
ADR-393 engine (ADR-394).** The window probe on `claude-opus-5` read the
five-hour window at **70 %** against the runner's 45 % gate — `room: false`,
resetting 2026-09-20T02:10Z — so `continue-2` stayed unspent and the critic's
own stated fallback was taken.

**The question F9 owed.** ADR-393 changed how every joint's connector frames
are read, and the three retained ot6 designs are read back through that engine
whenever F9 opens them. ADR-393 states its historical reach in prose: only a
weld written hardware-first, and only through frames. Prose is a claim, and
"no difference" is the one answer that is worthless unless it was looked for.
Nothing in the fit surface can see the defect — static clearance, the sweep and
the inventory all read component placements, which the swap never touched.

**The answer: ADR-393 touches none of the three.** Finch's `purchase()`,
Robin's `fix_{name}` and Heron's `weld()` all pass the carrying component's
connector first, so FreeCAD's `ensureUnconnectedIsSecondRef` never swapped any
of their 24, 21 and 12 fixed joints (of 28, 23 and 14; the rest are revolutes).
Measured on all four retained attempts of each — the ot6-era export, the two
from the ot7 restore audit, and a rebuild under the fixed engine — **every body
agrees exactly**: 0 of 29, 0 of 24, 0 of 15 disagreeing at 0.0 mm and 0.0°, and
each design's MJCF is **byte-identical across all four attempts**.

**The fit half, re-read under the fixed engine.** Each `ot7-open-*` copy was
read twice in a fresh process, once from published measurements and once
through `open_project`'s full restore, which re-runs the accepted script and so
exercises ADR-393's new refusal path: **406/44, 276/39, 105/20**, pair-for-pair
identical between the two reads, accepted revisions preserved, and no joint
refused at `stage: native_connector_frames`. Restores took 7.209 / 5.341 /
2.384 s.

Landed: `docs/probes/ot7/runner/mjcf_agreement.py` (the probe),
`cli/tests/test_mjcf_agreement.py` (four fixtures), ADR-394, the REGRESSION.md
section, the REPORT.md iteration-169 section, the runner README section, and
the 6.1 KB receipt `docs/probes/ot7/retained/adr393-reach.json`.

## Why

The critic's message named this exactly: spend F7's `continue-2` while the Opus
window is open, and **"if the call is void or the window is spent, record it and
start F9's regression on the ot6 copies, stating ADR-393's historical reach."**
The window is spent at 70 %, so the second branch applies. No frozen prompt was
sent and no `ot7-*` design was touched: the three projects read here are the
`ot7-open-*` copies, and `ot7-plover-e` was only read as a retained artifact.

Frontier: `mild-ledge-7157` (the ot7 charter) through F9, with
`salty-isle-4063` (dynamics on MuJoCo) carrying the measured reach of the
ADR-393 fix and `chilly-union-8972` (the CLI and its probes) carrying the new
tool.

## Method

**The probe, then its control, then the designs — in that order.** A
measurement tool that returns zero on three designs is evidence only once it
has been shown returning the right nonzero. So `mjcf_agreement.py` was written
first and pointed at `ot7-plover-e`'s pre-fix model, where it returned **24 of
29 disagreeing, worst `c_tabscrew_knee_l_0` at 121.86102740417053 mm and
179.99999879258172°** — iteration 167's figure, recomputed by an independent
route (that one was computed ad hoc; this one composes the body tree from the
XML and the placements from `result.json`).

`cli/tests/test_mjcf_agreement.py` pins the arithmetic on hand-written fixtures
whose answers are stated in the file before they run: a child 20 mm along its
parent's +X turned a quarter turn about Z agrees exactly; the same child
written as the **inverse** of that transform — ADR-393's shape — is caught at
its exact 28.284271247461902 mm and 180.0°; a body with no solved placement is
`no_placement` and never a pass; and the tolerance decides a borderline body.
Four passed in 0.02 s.

The designs were then measured from their own retained artifacts, and the
restore half through `cli.main`'s ordinary `_engine_session(..., restore=True)`
so it is the real `open_project` path and not a reimplementation.

Verification: `pixi run python -m pytest cli/tests` — **849 passed, 1 skipped in 554.00 s** (845 before this unit, plus its four fixtures). No
engine, protocol or payload change in this unit, so no engine suite or packaged
gate is implicated; iteration 168's engine run (2195 passed, 53 skipped) and
packaged gate (23 passed) are the current numbers for the ADR-393 code these
measurements exercise.

## Result

F9's regression holds under the ADR-393 engine, and the fix's historical reach
on the three retained ot6 designs is **measured at zero**, with a nonzero
control to show the probe works. `docs/probes/ot7/REGRESSION.md` and
`REPORT.md` carry both tables; the receipt is `retained/adr393-reach.json`.

**What is still open, unchanged by this unit.** F7's smoke. `ot7-plover-e` is
`paused` with `continue-2` and `continue-3` unspent, and the only route to a
passing smoke is a turn that re-accepts the design so its MJCF is rebuilt under
the fixed engine — `cadex smoke` reads the accepted revision's *retained*
artifacts, and the stored `plover_model-model.xml` (`c4c47094…`) came out of the
pre-fix engine. The critic ruled that a legitimate use of `continue-2`; the
window refused it, not the reasoning. Dispatch it after 02:10Z, and do not
spend `continue-3` on the same question.

**Assumption recorded.** The probe's 1e-4 mm / 1e-4° tolerance is the same one
iteration 168's connector-sides fixture used, chosen because the Ondsel
solver's own convergence residual is around 1e-6 mm. Nothing measured here came
near it: every retained body agreed at exactly 0.0.

No new dependency. No actor edit to any design. The unreconciled tail is three
records deep now (`pale-dew-4616`, `glad-chart-3979`, this one), so a reconcile
is due soon under the charter's every-five-or-three rule.

Dispatch closed: 1 unit — the window shut at 70 %, so F9's regression was
re-measured under the ADR-393 engine and the fix's reach on Finch, Robin and
Heron measured at zero, with `ot7-plover-e`'s pre-fix model as the nonzero
control (ADR-394).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: bf2ec7f3a12d38982a2392c3232095b129dcd9ae

## State Impact

- target: mild-ledge-7157 — F9's regression re-measured under the ADR-393 engine: the three retained ot6 copies open, restore and report 406/44, 276/39, 105/20 pair-for-pair identical between published and rebuilt reads, with no joint refused at stage: native_connector_frames. CLI suite 849 passed, 1 skipped.
- target: salty-isle-4063 — ADR-393's historical reach is measured, not argued: Finch, Robin and Heron write every weld host-first, so all four retained attempts of each export a body tree that agrees exactly with its solve (0 of 29, 0 of 24, 0 of 15 disagreeing, MJCF byte-identical across all four). ot7-plover-e's pre-fix model is the nonzero control at 24 of 29.
- target: chilly-union-8972 — docs/probes/ot7/runner/mjcf_agreement.py composes an exported MJCF body tree down to world against the solve's component_placements, reading retained artifacts only; cli/tests/test_mjcf_agreement.py pins its arithmetic on four hand-written fixtures.
- target: rapid-grove-9687 — F7 unchanged: the Opus five-hour window read 70% against the runner's 45% gate, so continue-2 was not dispatched; the receipt stays paused with two continuations unspent and the smoke unproven.
