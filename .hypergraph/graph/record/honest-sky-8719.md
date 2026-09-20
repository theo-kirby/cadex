---
node_id: f313bf6a-a123-5534-830a-90291ae5ab97
slug: honest-sky-8719
title: A fixed joint that holds nothing is measured and said (ADR-370)
created_at: '2026-09-16T17:57:00+00:00'
parents:
- mellow-marsh-0749
summary: ''
---
## What

The product can now measure what its fixed joints actually hold, and every
fit surface says it (ADR-370).

**The gap this closes.** F4's measured result is "two of three ot6 defects
resolved". The third is Heron's floating servo horns, and the reason the
product agent stopped there is in the product, not the model: on
`ot7-heron-repair-d` the design welds each horn to its link with a `fixed`
joint *and*, in the same `assembly.assembly` call, declares the pair a
**clearance of 0.05 mm**. Measured at 0.2 mm, that pair clears all four of
ADR-347's checks honestly. The agent's own fit-intent ledger lists it among
four declared clearances that pass. Only the evidence collector disagreed, and
only because `REPAIR_ATTACHMENTS` in `docs/probes/ot7/runner/run.py` hard-codes
two component names the product does not know. A checker whose right answer
lives in the harness is this run's diagnosis pointed at itself.

**The change.** `_check_attachments` in `cadex_assembly_worker.py` reports one
row per component pair joined by an unsuppressed `fixed` joint: the joint
output names that declare it, the distance and common volume already measured
by `_measure_clearance`, and `touching` (within the same 0.001 mm tolerance a
declared contact is held to, or overlapping), `not touching`, or `unknown` with
the engine's reason. It is published as `attachments` beside `world_geometry`;
the `clearance` inspect scope carries it; `attachment_summary` in
`cli/cadex_cli/clearance.py` is the block a build reply carries inside `fit`,
with its own verdict; the progress line ends `welded: N of M pair(s) not
touching` whenever the assembly welds anything; and `cadex clearance` writes
the rows under its pair table.

**It reports, never fails.** No `fit_failures` entry and no verdict changes, so
the charter's four checks stay four, acceptance is untouched, F9's regression
floor is unmoved, and F4's and F5's exhausted results stay comparable with
F6's and F7's. That restraint is also honest about the one false-positive
class: a standoff, a shim or a captive fastener between two welded parts is a
legitimate design, and only the design knows which it is. The block says so,
and says what to do when it is not: close the gap and declare the pair a
contact.

## Why

The critic's message asked for no change unless a concrete unblocked defect
warranted work, and for a fresh capacity probe before any F6 dispatch. I did
both, in that order.

**The probe first, and it refused again** — the fourth refusal, 2026-09-16 UTC, `claude-fable-5`, exit 1 in 1.87 s, `seven_day_overage_included` at
100 % with `overageDisabledReason: org_level_disabled`, five-hour at 20 %,
seven-day at 53 %, `room: false`. It spends no slot: F6's four and F7's four
remain unspent and no `ot7-robin-b` exists. No prompt was dispatched and no
design turn was attempted.

So the unit had to be an unblocked defect, and this is the one the run's own
evidence names. It is not a waiting record and not bookkeeping: it is product
code, two test files, three user-facing docs and an ADR, and it advances F1 —
"the agent sees measured fit" — by putting in front of the agent the one fact
the collector had and the product did not. It also serves F6 and F7 directly
when the gate opens: both the balancer and the biped will weld horns, bearings
and fasteners to links.

I did not touch a design, a prompt, a project or the run's lifecycle.

## Method

`run.py window --model claude-fable-5` → refused. Then read the evidence
rather than guessing at it: `ot7-heron-repair-d/script.py`'s twelve `weld(...)`
calls against `evidence/f4-repair/turn-3/clearance.json`. Ten of the twelve
welded pairs measure exactly 0.0 mm; the two that do not are
`comp_horn_shoulder`/`comp_upper_arm` and `comp_horn_elbow`/`comp_forearm`,
both at 0.2 mm, both declared clearances of 0.05 mm, and both are exactly the
collector's hard-coded pair list. Zero false positives on the only real design
available to measure it against, which is what decided the shape of the check.

Tests written first, against measured numbers:

- `cadex_tests/test_fit_intent.py`'s real-kernel fixture now welds its
  0.2 mm horn/link pair and declares it a 0.05 mm clearance — Heron's exact
  shape — so `fit_failures` on that pair is now `[]` and the attachment row is
  what names it, beside a welded pair that really touches. A pure test pins
  the suppressed joint, the non-fixed joint, another assembly's joint, two
  joints over one pair, and the pair with no measurement.
- `cli/tests/test_clearance.py` gains a rig whose script prints "every part
  fits": `verdict: pass`, `failing: []`, and `fit.attachments` carrying
  `a`–`b` at 1.2 mm under `weld_gap` while the touching weld is not reported.
  Plus the absent-vs-empty distinction and the progress-line phrase.

Both fail on the old code (the engine one cannot import `_check_attachments`;
the CLI one gets no `attachments` key at all). One correction on the way: the
first rig left `a`–`c` touching and undeclared, which the *existing* default
0.1 mm check failed — declaring that contact is what made the rig say only the
thing it is meant to say.

Verification, all after the change:

- `pixi run test-engine`: **2145 passed, 53 skipped** in 279.8 s.
- `pixi run python -m pytest cli/tests`: **790 passed, 1 skipped** in 533.1 s.
  Two later refinements (the markdown wording for an unavailable report, a
  parenthesisation in `_fit_line`) were re-run as
  `test_clearance.py` (57 passed) plus every other CLI file that reads a
  clearance report or a fit summary -- `test_project_docs`, `test_retained_fit`,
  `test_ot7_runner`, `test_review_server`, `test_walk`: 241 passed, 1 skipped.
- The **packaged gate** on a payload staged from this change:
  `pixi run build-engine` and `pixi run stage-engine` succeeded, the staged
  `Mod/cadex/cadex_assembly_worker.py` carries `_check_attachments`, and
  `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py` is **20 passed**.
- **An ot6 project still opens and still reads the same.** `cadex clearance`
  on a throwaway copy of `ot7-retained-heron` (read-only: the command builds
  and accepts nothing) produced a pair table identical to the committed one
  except for the two rows ADR-353's comparison slack already changed, and an
  attachment section reading *"No published attachment report for this
  accepted revision"*. It claims nothing about welds it never measured.

## Result

**What is true now.** The product measures what its fixed joints hold, and the
agent sees it in the same reply as the fit block, with the same "this is a
measurement, not your printout" framing. The knowledge that was hard-coded in
the evidence collector is now in the engine, where a design that has never
been seen by this run can trip it. Commit `3b27f62e`; ADR-370;
`docs/XSCRIPT.md`, `docs/CLI.md` and `docs/INTEGRATION.md` updated with it.

For the next iteration:

- **The F6/F7 gate is still shut, measured this iteration.** The fourth probe,
  2026-09-16, refused `claude-fable-5` at the organisation level
  (`org_level_disabled`, seven-day-with-overage 100 %, five-hour 20 %),
  exit 1 in 1.87 s, `room: false`. It spent no slot. F6's four slots and F7's
  four remain unspent; no `ot7-robin-b` or `ot7-plover-b` exists. Re-probe
  before any dispatch: only an unrefused probe is evidence it lifted.
- **The reconcile debt is now three nodes**: `soft-journey-2954`,
  `mellow-marsh-0749` and this one. A work dispatch cannot fold any of them.
- **Two deliberate non-changes, so nobody reads them as oversights.** The
  collector's `REPAIR_ATTACHMENTS` stays hard-coded: its seed's accepted
  revision predates this engine and publishes no report, and rewriting a
  receipt's own checker would make F4's evidence unreproducible. And the
  finding is **not** a fit failure, on purpose -- making it one would change
  the failing set on every ot6 copy, break F9's regression floor and make F4's
  and F5's exhausted results incomparable with F6's and F7's.
- **The one judgement call to know about.** "Welded but not touching" has a
  real false-positive class: two parts welded across a standoff or a shim. On
  the only real design available to measure -- `ot7-heron-repair-d`, twelve
  welded pairs -- it fired on exactly the two the ot6 probe found by hand and
  on nothing else. Both the block and the docs say the case out loud rather
  than hiding it.
- No new dependency, no TODO, no stub, nothing left red. The staged payload in
  `build/engine/` now carries this change; it is a build output and is not
  committed.

Dispatch closed: 1 unit — the gate re-probed and still refused, so the unit
became the defect F4's own result names: a fixed joint that holds nothing is
now measured by the engine and carried into every build reply (ADR-370).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 3b27f62e97fb57da1c4abc12dcf04c36b3a978e9

## State Impact

- target: wild-horizon-5461 — The build reply's fit block gains a third half (ADR-370): attachments, one row per pair joined by an unsuppressed fixed joint, carrying the joints that declare it, the measured distance and common volume, and touching / not touching / unknown, computed in the engine from the published pair measurements and never from stdout. The progress line ends 'welded: N of M pair(s) not touching' and cadex clearance writes the rows. Engine 2145 passed/53 skipped, cli/tests 790 passed/1 skipped, packaged gate 20 passed on a freshly staged payload.
- target: forest-wind-0342 — _check_attachments in cadex_assembly_worker.py publishes 'attachments' beside 'world_geometry' on the assembly output, and the clearance inspect scope carries it: absent on a revision accepted before ADR-370, an empty list on an assembly with no fixed joint. No fit verdict, failing set or acceptance behaviour changes; a legacy ot6 project still opens and its pair table is unchanged.
- target: chilly-union-8972 — cli/cadex_cli/clearance.py gains attachment_summary with its own verdict (touching / reported / unknown / none / unavailable), embedded in fit_summary, in _fit_line's progress phrase and in the clearance.md writer. docs/CLI.md, docs/XSCRIPT.md and docs/INTEGRATION.md's inspect row carry the contract.
- target: polished-forest-0215 — F4's residual is explained rather than left as a model failure: Heron's two horns pass all four checks because the design welds each to its link and declares the same pair a 0.05 mm clearance. The product now measures that gap itself, so the fact the collector's hard-coded REPAIR_ATTACHMENTS held is in the engine. The collector is deliberately unchanged, since the seed's accepted revision publishes no report and rewriting a receipt's checker would make F4's evidence unreproducible.
- target: narrow-dune-9454 — F6 remains blocked: a fourth capacity probe on 2026-09-16 refused claude-fable-5 at the organisation level (org_level_disabled, seven_day_overage_included 100 %, five_hour 20 %) in 1.87 s with room false. It spent no slot; all four F6 slots stay unspent and no ot7-robin-b exists. No prompt was dispatched.
- target: rapid-grove-9687 — F7 remains blocked behind F6 on the same measured refusal, all four slots unspent; the fourth probe is the current evidence.
