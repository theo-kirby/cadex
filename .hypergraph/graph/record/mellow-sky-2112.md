---
node_id: 6227dc17-ceaa-5daf-b991-38d1542ceb04
slug: mellow-sky-2112
title: Every build reply carries the swept fit beside the static one (ADR-366); F6 and F7 still blocked by the org-level Fable refusal
created_at: '2026-09-16T15:33:49+00:00'
parents:
- idle-crow-9434
summary: ''
---
## What

Every build reply now carries the **swept** fit beside the static one
(ADR-366). `fit.sweep` is computed by `sweep_summary` from the
`clearance_sweep` the `inspect scope=clearance` value the bridge already
reads carries, so it costs no second engine call and no second measurement:
coverage, one compact row per limited joint with its minimum distance,
maximum common volume and first-contact value with the pair that reached it,
and **every** pair that interpenetrates anywhere in a range, by name, with
the joint it is through. It keeps its own verdict — `fit["verdict"]` stays
the solved pose — and is advisory: a failing swept fit is reported, never
refused.

`cli/cadex_cli/clearance.py`, `bridge.py` (`_sweep_line`), `report.py` (a
`sweep` line under the `fit` line), the system prompt in `agent.py`, the
runner's per-turn `swept_fit` row, `docs/CLI.md`, `docs/XSCRIPT.md`,
`docs/probes/ot7/REPORT.md`, the runner README, and six tests in
`cli/tests/test_clearance.py`.

No engine, protocol, payload or `shell/` code is touched. No design turn
was dispatched and no frozen prompt was spent.

## Why

F6 is the run's highest-ranked open criterion and it is **still blocked**:
`run.py window` refused again this iteration in 2.2 s — five-hour 4 %,
`seven_day` 51 %, `seven_day_overage_included` 100 %, overage
`org_level_disabled`, "You've reached your Fable limit." The charter's
answer to a limited harness is an unblocked tooling unit, and ADR-362 set
the shape for this one: after F5 exhausted with one count of its bar
failing because the reply did not carry the count, the fix was to put the
count in the reply.

The other half of F5's bar has the same hole, measured on the same design.
F5's create turn (`flat-cove-2253`) accepted an arm whose two revolute
joints declared limits (±90°, ±100°) and whose assembly declared no
`sweep_step_degrees`, so the engine ran no sweep and published none — and
the reply said nothing about it, because the fit block is the solved pose
and says so in its own `source` line. The agent found the gap one
continuation later (`easy-otter-0439`), after which the sweep's geometry
made it narrow both ranges. F5's bar, and F6's and F7's, is "zero failing
static **and swept** fit checks"; half of it was invisible in the one place
the charter put the other half.

## Method

1. Probed the window first (spends no slot): refused, org-level Fable limit,
   five-hour 4 %. No design turn is dispatchable, so this is a tooling unit.
2. Read the producer before summarising it: `_measure_joint_sweeps` and
   `_sweep_joint` in `cadex_assembly_worker.py`, and the `clearance_sweep`
   fallback in `CadexInspection.py`. The per-joint result carries
   `minimum_distance_mm`, `maximum_common_volume_mm3` and
   `first_contact_<unit>` per pair, and an unswept joint carries the
   engine's own reason.
3. `sweep_summary(value, maximum_volume=…)` in `clearance.py`, folded into
   `fit_summary` as `["sweep"]`. Failing is **overlap through the motion** —
   a maximum common volume above the same threshold the static block uses —
   plus any pair the engine could not measure. Distance is reported, not
   judged: a declared contact sits at 0 mm through a whole range, so a
   distance rule would make every attached horn a failure. Verdict is `pass`
   only when every limited joint was swept to completion with no overlap;
   `incomplete` carries the per-joint reason; `unavailable` is the F5 case,
   carrying the engine's declare-the-steps reason.
4. Six tests, all six red on the previous code. Two are live against the
   real engine: the same hinge built with and without `sweep_step_degrees`,
   where the static verdict passes either way — the F5 shape exactly — and
   the reply is the difference between `sweep pass: 1 joint swept, minimum
   distance 16 mm` and `sweep unavailable` with the reason. The others are
   known-answer fixtures: a knee whose two pairs overlap at −55° and −70°
   beside an unswept slider (fail names both overlaps with their angles and
   still carries the slider's reason), an unmeasured pair, and three ways of
   having nothing measured, none of which is a pass.
5. Checked parity with the command the agent can call itself: the live test
   asserts `fit_summary(write_clearance(..., sweep=True) value)['sweep']`
   equals the block the bridge put in the reply.
6. Ran the whole CLI suite, found five real regressions in the pinned
   progress line, fixed them forward and pinned the three new phrases, then
   ran the whole suite again on the final tree.

## Result

`pixi run python -m pytest cli/tests` — **783 passed, 1 skipped, exit 0**
in 8 m 48 s, the whole suite on the final tree. The new tests were confirmed
red on the stashed pre-change modules. An earlier full run on the same
change caught five real regressions and they are fixed, not waived: the
progress line the parent logs is pinned character for character in
`test_mcp_protocol.py`, and adding the swept phrase to it broke all five
pins. They now expect `sweep unavailable` beside the static phrase, and a
new parametrised test pins the three phrases a published sweep produces —
`sweep pass`, `sweep fail: N overlapping pair(s) over K of N joint(s)
swept`, `sweep incomplete: K of N joint(s) unswept` — so a swept overlap can
never reach the log as a bare `fit pass`. No engine, protocol, payload or
`shell/` code is touched and `fit_summary` has no importer outside `cli/`,
so no engine suite or packaged gate applies.

What is true now: a design turn's reply carries measured motion fit, and a
design with limited joints and no declared step is told so in the reply
rather than one continuation later. F6 and F7 will run on a product two
changes newer than F5's (ADR-362 and ADR-366); `docs/probes/ot7/REPORT.md`
records that, and says the swept-coverage column in the F6/F7 rows is
measured on the newer product. F5 is not re-run and stands as measured.

Deliberately not taken, and named in the ADR: the engine skips
`_measure_joint_sweeps` entirely when neither step is declared, so nothing
enumerates the limited joints that went unswept, and the reply says
`unavailable` with the engine's reason rather than counting them. Making
the engine emit an `incomplete` row per limited joint in that case is an
engine change with ADR-027 goldens behind it and is a separate unit, worth
taking only if a design turn shows the reason alone is not enough.

Operative for the next iteration, unchanged from `idle-crow-9434`:
**`claude-fable-5` is refused on this account at the organisation level**
while the five-hour window sits at 1–4 %, so F6 and F7 cannot be dispatched
by any five-hour reset. All four slots of each are unspent. The product
agent's model stays `claude-fable-5` (ADR-363 preserved it and F5 ran on
it); switching it to `claude-opus-5` would break the F5–F7 comparison and
is a charter question for the owner, not an actor's call. It remains the
one decision that would unblock F4–F7 today.

No new dependency. Three unreconciled records now sit ahead of the
reconcile mark (`wandering-ocean-3301`, `idle-crow-9434`, this one), so the
next actor iteration is due a reconcile pass under the charter's rule.

Dispatch closed: 1 unit — ADR-366, every build reply carries the swept fit
beside the static one; F6 and F7 still blocked by the org-level Fable
refusal with all four slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: b65ec710b993605073d3846ccfdd70be1f6f97c4

## State Impact

- target: wild-horizon-5461 — ADR-366: the measured fit the agent sees now includes the swept half. fit.sweep is computed by sweep_summary from the clearance_sweep the same inspect scope=clearance value carries (no second engine call): coverage, one row per limited joint with minimum distance, maximum common volume and the joint value of first contact with the pair that reached it, and every pair interpenetrating anywhere in a range. It keeps its own verdict so fit['verdict'] stays the solved pose; pass requires every limited joint swept to completion with no overlap, and missing coverage is never a pass. Advisory: reported, never refused. The bridge progress line and the prose report carry both halves, the system prompt says motion fit is measured and that an unswept joint has been checked at one pose only, and docs/CLI.md and docs/XSCRIPT.md document it. cli/tests 783 passed, 1 skipped; six new tests red on the previous code, two live against the real engine.
- target: curious-quill-9036 — the published swept measurements now reach the agent in the build reply itself rather than only through inspect scope=clearance path=/clearance_sweep (ADR-366), summarised per joint with the three facts F3 asks for. Known gap named and not taken: the engine skips _measure_joint_sweeps entirely when neither step is declared, so nothing enumerates the limited joints that went unswept and the block says unavailable with the engine's declare-the-steps reason instead of counting them; emitting an incomplete row per limited joint is an engine change with ADR-027 goldens behind it and is a separate unit.
- target: narrow-dune-9454 — F6 remains blocked and unspent: this iteration's window probe was refused again in 2.2 s by the same org-level Fable limit (five-hour 4 %, seven_day 51 %, seven_day_overage_included 100 %, overage org_level_disabled), so no design turn was dispatched and no ot7-robin-b exists. When it runs it will run on a product two changes newer than F5's: ADR-362's inventory block and now ADR-366's swept fit.
- target: rapid-grove-9687 — F7 follows F6 and is blocked by the same org-level Fable refusal with all four slots unspent; it will also run on the ADR-362 + ADR-366 product.
- target: chilly-union-8972 — the CLI's build replies now carry fit.sweep beside fit and inventory (ADR-366), computed in cadex_cli.clearance.sweep_summary and folded into fit_summary; bridge._sweep_line puts both halves in the parent's progress line, report.human_lines prints a sweep line with one line per unswept joint and per overlapping pair, and the --json envelope carries it inside fit. The fake_cadexd clearance_value helper takes an optional sweep.
