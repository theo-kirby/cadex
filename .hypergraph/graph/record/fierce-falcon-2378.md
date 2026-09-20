---
node_id: 308be3f1-d094-564c-88c5-2920851620c5
slug: fierce-falcon-2378
title: A gap the design means is declared, not widened (ADR-373)
created_at: '2026-09-16T19:15:27+00:00'
parents:
- sharp-glacier-3405
summary: ''
---
## What

Corrected ADR-372's claim that a design meaning a 0.05 mm bearing seat "can say
so with `contacts=`", and fixed the product defect that correction exposed:
the agent's instructions named the declaration for a weld and no declaration at
all for an intended gap narrower than the 0.1 mm undeclared-pair default.

- `cli/cadex_cli/agent.py` — `CLI_OVERLAY` now says an intended running gap
  under the default is declared as `clearances=[(a, b, 0.05)]` with the gap the
  design means; that `contacts=[(a, b)]` is not that declaration, because it
  means touching within 0.001 mm and fails a 0.05 mm gap as a missed contact;
  and that a declaration is not a way to silence a pair not thought about.
- `cli/tests/test_turn_loop.py` — pins those three sentences. Verified to fail
  on the old `agent.py` (stashed that file alone; the assertion fires).
- `src/Mod/cadex/cadex_tests/test_fit_intent.py` — a new test pins the fact the
  correction rests on, at the one number ADR-372 named: one 0.05 mm row is
  `below clearance` undeclared, `missed contact` under `contacts=`, clear under
  `clearances=[(a, b, 0.05)]`, and `below clearance` again at 0.02 mm. It pins
  current behaviour rather than failing on old code, and the ADR says so.
- `docs/DECISIONS.md` — ADR-372's sentence corrected in place with a pointer
  forward; ADR-373 appended.

No engine behaviour changed. `clearances=` already accepted any non-negative
minimum (ADR-347) and the comparison already allowed its 1e-9 mm slack
(ADR-353).

## Why

The critic's message ordered two things. First, correct ADR-372's `contacts=`
statement and carry the correction forward from `sharp-glacier-3405`. Second,
pursue F6 only if the capacity gate permits dispatch, and otherwise preserve
every slot and make no change unless a concrete defect advances an F criterion.

The gate was read first, before any other work:
`pixi run python docs/probes/ot7/runner/run.py window` returned `room: false`
with `disabled_reason: "org_level_disabled"` and the probe's result frame
"You've reached your Fable limit" (exit 1, 1.92 s). `claude-fable-5` is still
refused on this account at the organisation level, so **F6 was not dispatched
and all four of its slots, and all four of F7's, remain unspent.** The
seven-day-overage `resets_at` the frame carries is the schedule of a usage
window, not a date for the org-level setting, so it forecasts nothing.

The correction is a concrete defect, and following it into the product found a
second one that advances F1 and F2. ADR-372 taught the agent, in its own
prompt, that a welded pair needs no declaration — and then stopped. The 16
pairs it deliberately left failing on Finch include four bearing seats at
0.05 mm, a thigh turning on the bearing it rides, which is correct design. The
prompt's only instruction for a failing pair was "fix the geometry and build
again", which for a running fit tells the agent to widen a seat that was right,
to a 0.1 mm it never chose, because nothing told it that number is a *default
for pairs nobody declared* rather than a manufacturing rule. ADR-372's remedy
was wrong in the same direction and more precisely so, which is the critic's
point: against a 0.001 mm tolerance, `contacts=` on that pair moves the row
from `below clearance` to `missed contact`. A design following that sentence
would have changed one failure into another and had every reason to read it as
progress.

Carrying it forward, as the critic asked, for `sharp-glacier-3405`: that
record's statement that a design meaning either of ADR-372's two left-failing
groups "can say so with `contacts=`" is **wrong for the 0.05 mm bearing seats**
and right only for the 12 purchased pairs meeting at 0.0 mm. The record graph
is append-only, so the correction lives here and in ADR-372's text rather than
in an edit to that node.

The fixed-joint exemption was not extended; nothing in this unit touches
`_fixed_joint_pairs`, `_check_fit` or any threshold, and transitivity through a
common host stays out.

## Method

1. Read the gate (`run.py window`) — refused, so no design turn.
2. Confirmed the tolerance in source rather than from the ADR:
   `_check_fit` fails a `contact` intent at `distance > 1e-3`
   (`cadex_assembly_worker.py:5866`), and `_ATTACHMENT_CONTACT_MM = 1e-3` is
   the same number the attachment report uses. `clearances=` takes any
   `minimum` ≥ 0 (`cadex_assembly_api.py:1358`).
3. Confirmed the agent's instructions never mention `clearances=` at all —
   the whole fit paragraph in `CLI_OVERLAY` names `contacts=` once, to say not
   to use it for a weld.
4. Wrote the failing prompt test, then the prompt paragraph, then the engine
   regression pin, then the ADR.
5. Suites: `pixi run test-engine` → **2147 passed, 53 skipped** (318.8 s);
   `pixi run python -m pytest cli/tests` → **799 passed, 1 skipped** (531.3 s).
   No protocol op, argument or response shape changed and no payload changed,
   so the packaged gate is not implicated.

## Result

The agent now has, in its own instructions, the declaration for a gap it means:
`clearances=[(a, b, 0.05)]`, with the reason `contacts=` cannot say it. Both
suites are green and nothing is broken. ADR-372 no longer offers a remedy that
would have renamed a failure.

This advances F1 (the prompt no longer leaves the agent to infer a repair from
a default it never chose) and F2 (the declared-intent surface is now reachable
from the instructions, not only from the docs). Neither criterion turns on it
alone.

Assumption recorded: nothing here declares anything on a retained design.
Finch's four bearing seats still read `below clearance` until a design turn
declares them, which keeps the F9 regression floor and every ot6/ot7 receipt
untouched. A future rebuild of Finch that adds the declaration would report
four fewer failing pairs, and that is a design change, not a measurement
changing.

Concern for the next iteration: **F6 and F7 are blocked on provider capacity
with every slot unspent, and the refusal is `org_level_disabled` rather than a
window that empties on a schedule.** Nothing in the receipt forecasts when
`claude-fable-5` returns to this account. The charter's answer stays the
unblocked tooling unit; do not spend a frozen prompt, and do not switch the
experiment's model, which would break comparability with F5 (ADR-363). Three
records are now unreconciled (`golden-lodge-6986`, `sharp-glacier-3405`, this
one), which is the charter's threshold — the next unit is the reconcile pass.

No new dependency.

Dispatch closed: 1 unit — ADR-372's `contacts=` claim corrected, and the agent
told how to declare a gap it means rather than widen one that was right
(ADR-373); F6 not dispatched, gate refused, all eight F6/F7 slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 64b59cee32b9a295f4820898b7b57608ac2046a0

## State Impact

- target: wild-horizon-5461 — The agent's instructions now name the declaration for an intended gap narrower than the 0.1 mm undeclared-pair default: clearances=[(a, b, 0.05)] with the gap the design means, and contacts= explicitly is not it, because it holds a pair to 0.001 mm and fails a 0.05 mm running fit as a missed contact (ADR-373). ADR-372 taught the agent that a welded pair needs no declaration and stopped there, leaving 'fix the geometry and build again' as the only instruction for the four Finch bearing seats at 0.05 mm, which is the wrong repair for a correct running fit. Pinned by cli/tests/test_turn_loop.py, which fails on the old prompt.
- target: narrow-dune-9454 — F6 remains blocked with all four slots unspent: the capacity gate (run.py window, this iteration) returned room=false with disabled_reason org_level_disabled and the probe's result frame 'You've reached your Fable limit' (exit 1, 1.92 s). claude-fable-5 is still refused on this account at the organisation level, so no create prompt was dispatched. The seven-day-overage resets_at the frame carries is a usage-window schedule, not a date for the org-level setting, and forecasts nothing.
- target: brave-stone-9609 — The fit-intent declaration a catalog running fit needs is now reachable from the agent's instructions rather than only from docs/XSCRIPT.md: a bearing seat between a printed part and a lib.bearing body is declared with clearances=, not left to the 0.1 mm undeclared-pair default and not widened to meet it.
