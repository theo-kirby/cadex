---
node_id: ade6fc2c-3195-5812-a8d0-7642c1c69a99
slug: sharp-glacier-3405
title: A welded pair is not an undeclared pair (ADR-372)
created_at: '2026-09-16T18:54:35+00:00'
parents:
- golden-lodge-6986
summary: ''
---
## What

The sixth F6/F7 capacity probe of 2026-09-16, and then the defect it left room
for: **a welded pair is no longer held to the gap an unrelated pair is held
to** (ADR-372, commit `43dfe452`).

The probe first. `run.py window --model claude-fable-5` was refused again, exit
1 in 1.92 s, `room: false`: `seven_day_overage_included` 100 % with
`overageDisabledReason: org_level_disabled`, `seven_day` 54 %, `five_hour`
26 %, the result frame carrying "You've reached your Fable limit". No slot was
spent, no prompt was dispatched; F6's four slots and F7's four stay unspent and
no `ot7-robin-b` or `ot7-plover-b` exists.

Then the unit. `_check_fit` held every pair with no explicit declaration to the
default 0.1 mm, including a pair the assembly **welds** with an unsuppressed
`fixed` joint. So mounting hardware flush against what carries it — which is
what a fixed joint asks for — failed `below clearance` at 0.0 mm, and the only
escape was a `contacts=` entry repeating the weld the script had already
written. It also contradicted ADR-370, one iteration old: that report names a
weld whose solids *never meet* as a finding, while this check failed the same
pair for meeting.

Now `_fixed_joint_pairs` is factored out of `_check_attachments` so one reading
of "these two are welded" serves both checks, and a welded pair with no
explicit declaration carries the implied intent
`{"kind": "attached", "minimum_mm": 0.0, "joints": [...]}`, published on the
row so a reader reaches the same verdict the engine did. The CLI's
`pair_status` reads that kind as `clear`; publishing `minimum_mm: 0.0` beside
it means a reader predating the branch reaches the same verdict from the number
alone.

## Why

The critic's message: correct the reconcile-debt handoff, then re-probe
capacity and dispatch F6 only if permitted, and if refused "preserve all slots
and make no change unless a concrete unblocked defect advances an F criterion".
The probe refused, so this is the second clause.

**The correction the critic asked for, carried forward.**
`golden-lodge-6986`'s Result said the reconcile debt was four nodes. It is
one. Commit `8d7cd55e` had already folded `soft-journey-2954`,
`mellow-marsh-0749` and `honest-sky-8719` before that record was written;
only `golden-lodge-6986` itself is unreconciled, and with this node the tail is
two. A record is append-only, so the correction lives here rather than in that
file.

The unit advances **F1** (the agent sees measured fit) and **F2** (fit intent
is declared and checked) directly. It is the same defect class the run keeps
finding — the product knowing less about the design than the checker beside it
— and this instance is the sharpest yet, because the checker was punishing
*correct* design and the repair it implied was to loosen a joint that was
right.

The measurement is what made it a unit rather than an opinion. On the retained
ot6 biped, **16 of Finch's 32 `below clearance` rows are a `fix_*` weld at
0.0 mm** between a host and the part mounted on it: `pelvis`↔its two hip
servos and two hip bearings, each `thigh`↔its horn, centre screw, knee servo
and knee bearing, each `shin`↔its horn and centre screw. Those 16 are the
reading a design turn was asked to repair.

The judgement call: **the implication is the weakest one available.** It
exempts the pair from the gap and asserts nothing else. Overlap above
1e-6 mm³ still fails, so Heron's buried servo tab is still an intersection; an
unmeasured pair still fails; an explicit `contacts=`/`clearances=` entry on the
same pair still wins; a welded pair that does *not* touch stays ADR-370's
separate advisory fact, because a standoff or a captive fastener is a
legitimate design; and a suppressed fixed joint grants no exemption (ADR-371).
Rigidity is deliberately **not** inferred transitively through a common host.

## Method

1. `pixi run python docs/probes/ot7/runner/run.py window --model
   claude-fable-5` — refused, `room: false`, no slot spent.
2. Read the defect out of the retained evidence before touching code:
   `comparison.json`'s Finch block, then `ot7-retained-finch/script.py`, whose
   `purchase()` helper welds every purchased part to its host with
   `assembly.joint("fixed", …, label="fix_" + name)`.
3. Engine: `_fixed_joint_pairs`, the `attached` implication in `_check_fit`,
   and `joint_data`/`assembly_output` passed at the one call site.
4. CLI: the `attached` branch in `pair_status` and `welded by <joints>` as the
   `cadex clearance` detail cell.
5. Tests, each red on the old code and checked so by neutralising only the
   behaviour (`if not intent and joints:` → `if False and joints:`), not the
   signature: `test_welded_pair_is_not_held_to_the_undeclared_gap` covers the
   exempt pair and the six that are not (overlap, unmeasured, two explicit
   declarations, suppressed, wrong kind, wrong assembly, other pair), and the
   real-kernel Heron-defect driver gains a welded flush `mount`/`stud` pair
   measured at 0.0 mm. In `cli/tests/test_clearance.py` the same rig is built
   and accepted twice through the real engine, once with the weld and once
   without — `pass` against `fail`, which is what says the joint is the
   difference and not the distance — plus the `pair_status` table including a
   pre-ADR reader that sees only `minimum_mm`.
6. The agent's system prompt, `docs/XSCRIPT.md`, `docs/CLI.md`,
   `docs/INTEGRATION.md`, the `assembly.assembly` docstring, ADR-372.
7. Green: `pixi run test-engine` **2146 passed, 53 skipped** (275.3 s);
   `pixi run python -m pytest cli/tests` **798 passed, 1 skipped** (530.8 s);
   `pixi run build-engine` + `pixi run stage-engine`, then the packaged gate
   `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
   test_cadexd_lifecycle.py` **20 passed**.
8. F9 checked rather than assumed: Finch's published rows re-read today through
   the unchanged `fit_summary` give **362 clear, 12 intersections, 32 below
   clearance, 44 failing** — identical to `comparison.json` — because every
   retained row carries `intent: null`.

## Result

**What is true now.** A design that welds two components and mounts them flush
is no longer told it has a fit failure for doing so. Commit `43dfe452`;
ADR-372; four docs and the system prompt updated with it.

For the next iteration:

- **The F6/F7 gate is still shut, measured this iteration.** Sixth probe,
  2026-09-16: exit 1 in 1.92 s, `org_level_disabled`, seven-day-with-overage
  100 %, five-hour 26 %, `room: false`. Only an **unrefused** probe is evidence
  it lifted. Re-probe before any dispatch.
- **The reconcile debt is two nodes**: `golden-lodge-6986` and this one. Its
  own Result said four; that was wrong, and `8d7cd55e` is the commit that
  proves it. A work dispatch cannot fold either.
- **The retained receipts do not move, and F9's floor is intact** — verified,
  not assumed, by the re-read above. A retained design only changes if it is
  rebuilt, and rebuilding one is a design turn nobody may take here.
- **The number to expect if Finch is ever rebuilt**: 44 → 28 failing rows. The
  16 that remain are 12 pairs of *purchased* parts at 0.0 mm that share a host
  but are welded only to it (a servo against the screws through its tabs, a
  servo against the horn on its output), and 4 bearing seats at 0.05 mm. Both
  are declarable with `contacts=`; neither is inferred.
- **The open question this leaves.** Whether two parts welded to the same host
  should be exempt from each other is a real design question and is
  deliberately unanswered: transitive rigidity would exempt pairs no joint
  names, and 12 of Finch's rows are exactly that case. It is worth a decision,
  not a guess.
- No new dependency, no TODO, no stub, nothing left red. `build/engine/` was
  re-staged for the gate; it is a build output and is not committed.

Dispatch closed: 1 unit — the gate re-probed and still refused, so the unit
became the defect beside it: a welded pair is no longer held to the undeclared
pair's gap (ADR-372), with the reconcile-debt handoff corrected to one node.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 43dfe45217457625abb200a11b4dc763ce05493c

## State Impact

- target: wild-horizon-5461 — The static half of the build reply stops failing a pair the design welds: an unsuppressed fixed joint exempts the pair from the 0.1 mm undeclared minimum and publishes the implied intent {kind: attached, minimum_mm: 0.0, joints: [...]} on the row, so flush-mounted hardware reads clear while overlap, unmeasured pairs, explicit declarations and suppressed welds are unchanged. Measured cause: 16 of Finch's 32 below-clearance rows are fix_* welds at 0.0 mm. Engine 2146 passed/53 skipped, cli/tests 798 passed/1 skipped, packaged gate 20 passed on a freshly staged payload.
- target: forest-wind-0342 — _fixed_joint_pairs is factored out of _check_attachments in cadex_assembly_worker.py and is the one reading of a welded pair shared by the attachment report and the fit check; _check_fit takes joint_data and assembly_output and applies the attached implication only to a pair with no explicit fit_intent. _FIT_DEFAULT_MINIMUM_MM names the 0.1 mm that was a literal. No protocol op, argument or response shape changed and acceptance behaviour is unchanged.
- target: chilly-union-8972 — cli/cadex_cli/clearance.py pair_status reads intent kind 'attached' as clear, and cadex clearance writes 'welded by <joint names>' as the pair's detail; the published minimum_mm 0.0 makes a reader predating the branch reach the same verdict. cli/cadex_cli/agent.py's system prompt tells the agent not to declare a contact that repeats a weld. docs/CLI.md, docs/XSCRIPT.md and docs/INTEGRATION.md carry the contract.
- target: narrow-dune-9454 — F6 remains blocked: a sixth capacity probe on 2026-09-16 refused claude-fable-5 at the organisation level (org_level_disabled, seven_day_overage_included 100 %, seven_day 54 %, five_hour 26 %) in 1.92 s with room false. It spent no slot; all four F6 slots stay unspent and no ot7-robin-b exists. No prompt was dispatched.
- target: rapid-grove-9687 — F7 remains blocked behind F6 on the same measured refusal, all four slots unspent; the sixth probe is the current evidence.
