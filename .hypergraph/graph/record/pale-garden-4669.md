---
node_id: ba6dbcc4-306b-524b-b105-18522a667afd
slug: pale-garden-4669
title: Sweep coverage is published whether or not a step is declared (ADR-367); F6/F7 blocked by the Fable org limit until 2026-09-18
created_at: '2026-09-16T16:12:00+00:00'
parents:
- mellow-sky-2112
summary: ''
---
## What

The published sweep now reports **coverage whether or not a step is
declared** (ADR-367). An assembly that declares neither `sweep_step_degrees`
nor `sweep_step_mm` is `incomplete` with one row per limited joint naming
it, its kind, its unit and the declaration it is missing, so the build reply
reads `sweep incomplete: 2 of 2 joint(s) unswept` instead of
`sweep unavailable`. An assembly with no limited joint at all reports
complete coverage of an empty set, which `sweep_summary` already read as
`unavailable` with its own reason and which `cadex clearance --sweep` now
says in its coverage line rather than printing a bare "complete".
`unavailable` keeps exactly one meaning: a revision accepted by an older
engine.

`src/Mod/cadex/cadex_assembly_worker.py` (the guard and the publish site),
`cli/cadex_cli/clearance.py` (the `--sweep` coverage line),
`cli/cadex_cli/agent.py` (the system prompt's two sentences on what
`incomplete` and `unavailable` mean), two new tests in
`test_cadexd_lifecycle.py`, the live F5-shape test in `test_clearance.py`
and the legacy-project sweep test, plus `docs/XSCRIPT.md`, `docs/CLI.md`,
`docs/INTEGRATION.md` and ADR-367. Commit `d6a52b02`.

No design turn was dispatched and no frozen prompt was spent. F6's create
prompt and all three continuations are unspent; no `ot7-robin-b` exists.

## Why

F6 is the run's highest-ranked open criterion and remains **blocked**. I ran
the window probe first, as the critic asked: it refused in 2.27 s —
`five_hour` 9 %, `seven_day` 52 %, `seven_day_overage_included` **100 %**
with `overageDisabledReason: org_level_disabled`, "You've reached your Fable
limit." The rejected overage window's `resets_at` is 1789740000, which is
**2026-09-18 14:00 UTC — about 46 hours away**. That is the operative new
fact: F6 and F7 are not waiting on a five-hour reset and not waiting on
hours; under `claude-fable-5` they are unreachable for roughly two days.

I did not take the critic's "make no change" branch, and this is the
deviation to state plainly. That branch is the charter's when *no* unblocked
unit is left; one was left, and the previous iteration named it. ADR-366
recorded a gap it deliberately did not take and set its own trigger: worth
taking "only if a design turn shows the reason alone is not enough". A
design turn already had. F5's create turn on `ot7-heron-c`
[rec: flat-cove-2253] accepted an arm whose two revolute joints declared
limits (±90°, ±100°) and whose assembly declared no `sweep_step_degrees`;
the agent found the gap one continuation later [rec: easy-otter-0439],
spending a slot on it. F6 and F7 run the same bar with the same reply, and
this is the one thing left on F3's evidence list that would have cost them
the same slot. Making the change idle for two days to avoid a third tooling
unit would be the expensive choice, not the conservative one.

## Method

1. Probed the window before anything else (spends no slot): refused,
   org-level Fable limit, reset computed at 2026-09-18 14:00 UTC.
2. Read the producer rather than assuming the shape of the fix.
   `_measure_joint_sweeps` **already** emits exactly the row F3 wants for an
   unswept limited joint — `{"joint": …, "kind": …, "unit": …, "status":
   "incomplete", "reason": "sweep_step_degrees is not declared on the
   assembly, so this limited revolute joint was not swept"}`. That path is
   how a design declaring `sweep_step_mm` alone learns about its hinges. The
   entire defect was that the dispatch site guarded the call with
   `if sweep_steps:`, so it was never reached when *neither* step was
   declared. The fix is deleting the guard; ADR-366's estimate that this was
   an engine change with goldens behind it was right about the zone and
   wrong about the size.
3. Checked the cost before committing to it, because "publish a sweep on
   every assembly" sounds expensive. It is not: with no step declared every
   joint short-circuits on the step check before `_bounded_sweep_call`, so
   no geometry runs and no subprocess spawns. The lifecycle test asserts
   `elapsed_seconds < 1.0` and measures well under a millisecond.
4. Checked what it could break. The assembly *definition* is untouched
   (`cadex_assembly_api.py` still omits the keys when undeclared), so
   accepted identity and legacy definitions are unaffected; the
   `CadexInspection` fallback for results with no `clearance_sweep` key
   stays, so retained projects read as before; no engine test asserted the
   key's absence.
5. Two lifecycle tests, parametrised on limited-joint and no-limited-joint,
   asserting the published result, the row's name and reason, that no pairs
   were measured, the elapsed bound, and the same enumeration through
   `inspect scope=clearance path=/clearance_sweep` with no rebuild.
   Confirmed red on stashed source with `KeyError: 'clearance_sweep'` —
   and confirmed first that the lifecycle suite reads the **source** tree,
   not the installed copy, by reverting the installed module and watching
   the tests still pass.
6. The live CLI test that builds the F5 shape both ways changed from
   asserting `unavailable` to asserting the named joint, its reason, the
   counts and the exact reply line.
7. One consequence I did not plan for and did fix: the legacy-project
   `--sweep` report began printing a bare `Coverage: complete.` for a design
   with no joints at all. True but readable as a swept mechanism, and it
   disagreed with the reply block beside it, which calls that case
   `unavailable`. The markdown now carries the same sentence.

## Result

`pixi run test-engine` — **2,144 passed, 53 skipped** in 4 m 34 s (2,142
before this unit). `pixi run python -m pytest cli/tests` — **783 passed, 1
skipped** in 8 m 47 s, re-run after the doc and system-prompt edits. The
packaged gate, against a freshly staged payload whose
`cadex_assembly_worker.py` was confirmed to carry the change:
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
test_cadexd_lifecycle.py` — **20 passed**. One `pixi run build-engine` and
one `pixi run stage-engine`, the unit's single build. No `shell/` code
touched.

**F3's last named gap is closed.** The build reply now names *which* limited
joints went unchecked, not only that a sweep is absent — on the exact shape
that cost F5 a continuation. F1, F2, F8 and F9 are unchanged.

**F6 and F7 remain blocked with all four slots each unspent**, and the cause
is now dated: `claude-fable-5` is refused at the organisation level until
**2026-09-18 14:00 UTC**. Waiting on a five-hour reset does not help; `run.py
window` is the cheap check and says why. The product agent's model stays
`claude-fable-5` per ADR-363 — switching it is a charter question for the
owner, not an actor's call, and it remains the one decision that would
unblock F6 and F7 before Friday. The next iteration should re-probe, and if
it is still refused, should note that F6/F7 will run one product change
newer than F5 by two ADRs now (ADR-362 and ADR-367), which the closing
report's "Product version" paragraph must be extended to say.

Assumption recorded: complete coverage of an empty set is the right thing
for an assembly with no limited joint to publish, rather than a third status
name. It is what the CLI already interpreted for the agent, and adding a
status would have been a protocol-visible enum change for a case two
surfaces already describe in words.

No new dependency. No protocol op, argument or page contract changed; the
response gains one key on an assembly output and the shell passes the scope
value through untouched.

Dispatch closed: 1 unit — ADR-367, sweep coverage is published whether or
not a step is declared, so an assembly declaring neither names every limited
joint it left unswept; F6 and F7 still blocked by the Fable org-level
refusal until 2026-09-18 14:00 UTC, all eight slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d6a52b02f7e95bdab2b7352a3fb43c941819b316

## State Impact

- target: curious-quill-9036 — ADR-367: the engine publishes clearance_sweep on every assembly, not only one declaring a step. The dispatch site's 'if sweep_steps:' guard was the whole defect: _measure_joint_sweeps already emitted an incomplete row naming a limited joint whose kind's step is undeclared, and was simply never reached when neither step was declared. An assembly declaring neither is now incomplete with one row per limited joint (name, kind, unit, missing declaration), so the build reply reads 'sweep incomplete: N of N joint(s) unswept' instead of 'sweep unavailable' — the exact shape that cost F5 a continuation. It costs no measurement: every joint short-circuits before any geometry call, elapsed_seconds under 1 ms. An assembly with no limited joint reports complete coverage of an empty set, which sweep_summary already read as unavailable with its own reason and which cadex clearance --sweep now says in its coverage line; unavailable keeps one meaning, a revision accepted by an older engine. The definition is untouched so accepted identity and legacy definitions are unaffected. This closes the known gap curious-quill-9036 named as deliberately not taken. Evidence: two lifecycle tests red on the previous code with KeyError: 'clearance_sweep'; the live F5-shape CLI test now asserts the named joint and the reply line; test-engine 2,144 passed 53 skipped; cli/tests 783 passed 1 skipped; packaged gate 20 passed on a freshly staged payload.
- target: narrow-dune-9454 — F6 is still blocked with all four slots unspent and the cause is now dated: the window probe refused in 2.27 s with seven_day_overage_included at 100%, overageDisabledReason org_level_disabled, and the rejected window's resets_at (1789740000) is 2026-09-18 14:00 UTC, about 46 hours out. No design turn dispatched, no ot7-robin-b exists, the frozen prompts are unchanged and the model stays claude-fable-5 per ADR-363.
- target: rapid-grove-9687 — F7 remains blocked behind F6 by the same org-level Fable refusal until 2026-09-18 14:00 UTC, with all four slots unspent.
- target: first-snow-5587 — The closing report's 'Product version' paragraph will need extending: F6 and F7 now run two product changes newer than F5, ADR-362 and ADR-367, rather than one. F5 is not re-run and no frozen prompt changed.
