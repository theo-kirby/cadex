---
node_id: a831fc79-f641-5ff6-a6c8-14f0c18ee9c3
slug: wild-eagle-4128
title: The closing receipts count ADR-374, and the contract names relative_motion
created_at: '2026-09-16T20:41:58+00:00'
parents:
- old-star-3367
summary: ''
---
## What

Three documents and one test, all about the same fact: **ADR-374 landed and the
receipts that compare designs against the product did not count it.**

- `docs/probes/ot7/REPORT.md`'s F10 product-version section said F6 and F7 run
  on a product **three** changes newer than F5's, naming ADR-362, ADR-366 and
  ADR-367 with ADR-368 as a follow-up. It is now **nine** — ADR-362, 366, 367,
  368, 370, 371, 372, 373 and 374 — each with its commit, what it publishes,
  and what F5's four turns did not have. Seven change the measured fit surface
  a design reads; the other two are the inventory block beside it and the
  repair wording in the agent's own prompt.
- `docs/probes/ot7/REGRESSION.md` said "three of the four checker changes"
  landed after the retained designs were accepted are outside its
  weld-exemption table. It is now four of five, with ADR-374's swept roll-up
  named and its reason given: it reads a joint row's three numbers over the
  pairs that joint moves, and there is no joint row in a retained receipt to
  read.
- `cli/tests/test_retained_fit.py` gains
  `test_the_retained_receipts_publish_no_sweep_to_roll_up`, which pins that
  claim through `sweep_summary` on all three retained receipts rather than
  through the raw `clearance_sweep` key: verdict and coverage `unavailable`,
  no joint row, no `pairs_moving`, nothing failing, and the published reason.
- `docs/INTEGRATION.md`'s published-sweep section now names
  `relative_motion` — the rule that sets it, what a reader rolling a joint row
  up must do with it, and that the key is **absent** on a revision accepted
  before ADR-374 and counts as moving. ADR-374's entry in `docs/DECISIONS.md`
  carries a dated line saying that documentation should have been in its own
  commit and was not.

No product behaviour changed. `cli/tests/test_retained_fit.py` 12 passed in
0.02 s; `test_response_schemas.py` and `test_engine_purity_guardrails.py`
64 passed in 1.41 s (they are what pins `docs/INTEGRATION.md` against
`OP_RESPONSE_SPECS` and `OP_ARG_SPECS`); the full `cli/tests` run is reported
in `## Result`.

## Why

F6 and F7 are the ranked frontier and both are blocked. I probed the gate
first: `run.py window --model claude-fable-5` at 2026-09-16, **refused in
2.12 s** — rejected `rate_limit_event` on `seven_day_overage_included`,
synthetic `rate_limit` assistant frame, HTTP 429 "You've reached your Fable
limit", `disabled_reason: org_level_disabled`, windows five-hour 6 % /
seven-day 55 % / with-overage 100 %, `room: false`. That is a void call by
ADR-355 and spent no slot; F6 and F7 keep all eight. So no design turn was
dispatched, per the charter's rule that design turns wait for the product
agent.

The critic asked, as housekeeping before the unit, that REPORT.md's F10
comparison be corrected from eight product changes to nine including ADR-374.
The report was further behind than that: it said **three**. Correcting it
properly meant reading each of the nine, which surfaced two more places one
iteration behind on the same change — the regression receipt's checker-change
list, and `docs/INTEGRATION.md`, which documents ADR-370's `attachments` and
ADR-371's `skipped` rows but never gained ADR-374's `relative_motion`. That
last one is not bookkeeping: INTEGRATION.md is the process contract both
front ends read, and AGENTS.md requires the doc to move in the same change as
the behaviour. So the unit is the whole catch-up, with the receipt's new claim
test-pinned rather than asserted.

This is what the critic's message asked for, plus the two documents that were
wrong for the same reason. It is not a fifth waiting record: every edit states
a fact about the product, and the one new test fails if the retained receipts
ever acquire a sweep without the receipt being rewritten.

## Method

1. `run.py window --model claude-fable-5` — refused, receipt read above, no
   slot spent, no prompt dispatched.
2. Read ADR-362, 366, 367, 368, 370, 371, 372, 373 and 374 in
   `docs/DECISIONS.md` and their commits (`fd3b3643`, `b65ec710`, `d6a52b02`,
   `3cd8905e`, `3b27f62e`, `45a2fe2c`, `43dfe452`, `64b59cee`, `65cbe3ca`),
   and rewrote REPORT.md's product-version section one paragraph per change.
3. Added the ADR-374 bullet to REGRESSION.md's "what that table models, and
   what it does not" list, beside ADR-370's, ADR-371's and ADR-373's.
4. Wrote the test first against the three retained receipts, whose right
   answer is known in advance — they publish `clearance_sweep.status:
   unavailable` with no joints — and pinned it through `sweep_summary` so the
   receipt's wording and the product cannot drift apart.
5. Documented `relative_motion` in INTEGRATION.md's published-sweep section
   and noted the catch-up in ADR-374.
6. Ran `cli/tests/test_retained_fit.py`, the two protocol-document guards, and
   the full `cli/tests` suite: **809 passed, 1 skipped in 529.40 s**. No engine
   suite and no packaged gate: nothing under `src/` changed, and the only
   executable edit is a CLI test.

## Result

The three receipts and the contract document now say what the product does as
of ADR-374. `docs/probes/ot7/REPORT.md` no longer understates the difference
between F5's product and F6/F7's by six changes, which was the one number the
report's own comparison rests on. The engine and the CLI are unchanged; the
only executable change is one new test.

The F6/F7 gate is still shut: `claude-fable-5` was refused again today at the
organisation level, `room: false`, no slot spent. F6 and F7 stand with all
eight create and continuation slots unspent, which is not exhaustion. Nothing
here dispatches, extends, stops or restarts anything.

Assumption recorded: the state graph says REPORT.md's F10 comparison was "one
behind at eight". It was three, not eight — the eight was the state node's own
previous count, not the report's. The report is now nine and matches
`narrow-dune-9454` and `rapid-grove-9687`; the stale "one behind at eight"
sentences in those two nodes are for the next reconcile to drop.

Concern for the next iteration: `docs/INTEGRATION.md`'s nested response fields
are pinned by nothing. `test_response_schemas.py` compares only top-level
response keys against `OP_RESPONSE_SPECS`, so an advisory field added inside a
scope value — `attachments`, `intent`, `relative_motion` — can land
undocumented exactly as this one did, and only a reader noticing catches it.
That is a real, demonstrated gap with a known answer, and it is the kind of
unit available while the gate is shut.

Dispatch closed: 1 unit — the closing receipts and the process contract count ADR-374; the F6/F7 gate probed and still refused, no slot spent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 60f298bc74408a744fb22ce9c9dbb296998c503a

## State Impact

- target: first-snow-5587 — REPORT.md's F10 product-version section now lists nine product changes since F5 (ADR-362, 366, 367, 368, 370, 371, 372, 373, 374), one paragraph each with its commit and what it publishes; it previously said three. No done claim changed.
- target: eager-summit-3153 — REGRESSION.md's 'what that table models' list is now four of five checker changes, with ADR-374's swept roll-up named as outside it (no joint row in a retained receipt to read), pinned by the new cli/tests/test_retained_fit.py::test_the_retained_receipts_publish_no_sweep_to_roll_up; cli/tests 809 passed, 1 skipped.
- target: narrow-dune-9454 — the 'REPORT.md is one behind at eight' note is spent: the report now says nine and matches this node. F6 probed again on 2026-09-16 (run.py window --model claude-fable-5): refused in 2.12 s, org_level_disabled, windows 6 / 55 / 100 %, room false, no slot spent; all four slots remain unspent.
- target: rapid-grove-9687 — same: the report's count now matches this node at nine, and the same refused probe leaves F7's four slots unspent.
- target: chilly-union-8972 — docs/INTEGRATION.md's published-sweep section now documents relative_motion (the rule, the roll-up it implies, and its absence on a revision accepted before ADR-374); ADR-374's entry carries a dated line that this belonged in its own commit.
