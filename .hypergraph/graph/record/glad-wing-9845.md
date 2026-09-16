---
node_id: 879e71ce-05f4-54b7-86bc-e867870b3692
slug: glad-wing-9845
title: A weld and a declared gap on the same pair contradict each other (ADR-379)
created_at: '2026-09-16T23:18:58+00:00'
parents:
- jolly-current-9257
summary: ''
---
## What

ADR-379. ADR-372 stopped holding a welded pair to the undeclared-pair
0.1 mm gap and kept one escape hatch, in its own words: "an explicit
`contacts=` or `clearances=` declaration on the same pair still wins — the
author saying '0.5 mm here' outranks the joint."

That hatch is how ot6's floating-horn defect survived F4. On
`ot7-heron-repair-d` the frozen repair prompt and all three continuations
reached the model, each asking for every failing check to be resolved, and
the run ended with `comp_horn_shoulder` 0.2 mm from `comp_upper_arm` and
`comp_horn_elbow` 0.2 mm from `comp_forearm` — the same gap ot6's hand-run
probe found. Both pairs are welded (`weld_horn_shoulder`, `weld_horn_elbow`)
and both carry `{"kind": "clearance", "minimum_mm": 0.05}` from the same
script. Static fit read 0 of 105 failing, swept read 0, and the agent's own
ledger wrote the outcome down: "4 declared ≥0.05 mm clearances measure
0.0999999–0.2 mm (…horn pockets both joints)". Two continuations that named
no failure left the design unchanged, correctly, because nothing named one.

The declaration did not outrank the joint. It contradicted it, and the
product resolved the contradiction in favour of whichever one silenced the
pair.

Fixed: a `clearances=` declaration on a pair an **unsuppressed** fixed joint
welds is itself the failing check, `clearance under weld`. The declared
minimum is not consulted — no measured gap makes "one rigid body" and "a
running gap" both true — so the pair fails below it and above it alike. The
engine publishes the welding joints on that declaration
(`{"kind": "clearance", "minimum_mm": …, "joints": [...]}`) so a reader
reaches the same verdict, and the `fit` block carries a note naming the two
repairs: close the gap and declare the pair with `contacts=`, or stop welding
two components meant to stay apart. Removing only the declaration is not a
repair either — it leaves the gap, reported by `fit.attachments` (ADR-370)
instead of hidden behind a passing check.

Landed in `f37e8a08`, engine `_check_fit` plus the CLI blocks that read its
rows. No new op, no `OP_ARG_SPECS` change, no `shell/` diff.

## Why

The critic's message: the frontier has not moved in 33 iterations; pick one
criterion from the charter's done criteria, name it, and do the smallest
thing that moves it — while keeping the waiting exception, spending no design
slot, not repeating a capacity probe within minutes, and leaving the run
lifecycle alone.

**What I did instead of what it also asked.** It said "make no changes or
waiting records". I made a change. Its first paragraph asks for a criterion
to be moved and its second asks for no change, and the two cannot both be
followed; I took the first, because the charter's own question policy says to
take an unblocked tooling or test unit when the product agent's harness is
limited and only to stand still when none is left. One was left.

I did **not** probe the F6 window. The last probe was at 2026-09-16T22:32
UTC (`vast-water-9886`, sixth refusal) and this iteration began at 22:47 —
fifteen minutes. The refusal is an organisation-level setting, not a clock,
and the critic asked for hours between checks. No frozen prompt was sent, no
`ot7-*` design was edited, no model was switched and nothing touched the run
lifecycle.

The criterion this advances is **F6**, and **F7** behind it. Their bar is
"zero failing static **and swept** fit checks", and until this change a
balancer or a biped could meet it the way Heron did: weld a part on, declare
a gap under the weld, and every check passes while nothing but the joint
holds the part. It is the same error class as ADR-377 and ADR-378 — a fact
the product had and did not judge — in the gate the two unspent designs must
clear. It also closes the one defect F4 measured and could not name.

## Method

1. Read the F4 and F5 assessments in `docs/probes/ot7/REPORT.md` looking for a
   reproduced defect rather than a guess, and found F4's last paragraph: "the
   horn is 0.2 mm from its link, exactly where ot6's probe found it, and every
   report the agent reads calls that gap a passing declared clearance."
2. Confirmed it in the data, not the prose: `turn-3/clearance.json` on
   `ot7-heron-repair-d` carries both horn pairs at 0.2 mm with
   `{'kind': 'clearance', 'minimum_mm': 0.05}`, and `script.py:328,334` welds
   each of them (`weld(c_horn_sh, c_ua, S, "weld_horn_shoulder")`).
3. Read `_check_fit` and found both facts already side by side: `intents` and
   `welded` in the same loop, with the explicit declaration simply winning.
4. Engine: the contradiction appended to `fit_failures`, and `joints`
   published on the clearance intent — only there, so no intent any project
   already published changes shape. CLI: `pair_status` returns the new status,
   `fit_summary` carries `WELDED_CLEARANCE_NOTE`, `cadex clearance` writes the
   detail and the note, the review's `offending_pairs` includes it, and the
   agent's system prompt says never to declare a gap on a pair it welds.
5. Tests. The real-OCCT fixture in `test_fit_intent.py` already **was**
   Heron's shape (`horn` welded to `link`, declared 0.05 mm, measured 0.2 mm)
   asserting `fit_failures == []`; it now asserts `['clearance under weld']`.
   Eight parametrised engine cases cover the contradiction at 0.0, 0.02 and
   0.2 mm, under an overlap, across a suppressed weld and against a contact
   declaration. ADR-370's end-to-end weld test asserted `verdict: pass` with
   an empty failing list and now asserts the named pair, its `joints` and the
   note, its attachment report unchanged. ADR-372's one "outranks the joint"
   assertion is reversed in place.
6. Replayed the rule over the twenty `clearance.json` receipts in the
   operator's `ot7-*` projects: **zero** rows, because no accepted revision
   was built by an engine that published `joints` on a clearance intent.
   `test_adr_379_moves_no_retained_number` pins the same on the three
   committed retained receipts, which carry no `intent` key at all.
7. Verified red on the old code by stashing only the two product files: 6
   engine failures (including the real-OCCT fixture) and 3 CLI failures.
8. Gates: `pixi run test-engine` **2,160 passed, 53 skipped**;
   `pixi run python -m pytest cli/tests` **823 passed, 1 skipped**;
   `build-engine` and `stage-engine` exit 0 with the new line present in the
   staged worker; `CADEX_ENGINE_ROOT=build/engine/… pytest
   test_cadexd_lifecycle.py` **21 passed**.

## Result

**The product now names the defect that F4's four repair turns could not
see.** A pair a design welds and declares a running clearance on fails
`clearance under weld` at any gap, in the build reply, in
`docs/clearance.md`, and in the review's offending pairs, with the two
repairs stated. `docs/XSCRIPT.md`, `docs/CLI.md`, `docs/INTEGRATION.md`, the
agent's system prompt, `docs/DECISIONS.md` and `docs/probes/ot7/REPORT.md`
carry it.

**No recorded number moves.** The ot7 report's counts are what the accepting
engines published, and no retained receipt carries a clearance intent with
joints. What a *rebuild* of `ot7-heron-repair-d` would now report is two
failing pairs where it reported none — F4's measured result stands as
recorded, and the defect it left behind is nameable.

What the next iteration must know:

- **F6 is still blocked and F7 behind it, all eight slots unspent.** No probe
  was taken this iteration; the last was `vast-water-9886` at
  2026-09-16T22:32 UTC, refused on `org_level_disabled`. The exits are
  unchanged: the owner enabling usage credits, or the
  `seven_day_overage_included` reset at 2026-09-18T14:00Z, which falls after
  this run's `stop.until` of 2026-09-17T04:25:13Z. When a probe answers, the
  unit is `run.py robin "$PROJECTS/ot7-robin-b" --model claude-fable-5`.
- **This is a behaviour change to what "zero failing fit checks" means**, and
  F5's and F4's bars were judged under the older rule. Both are exhausted and
  their results are recorded as measured; F6 and F7 will be judged under this
  one, which is the point of landing it before they run.
- No new dependency. No red tree. The tail is now four unreconciled records
  (`sunny-brook-2439`, `jolly-current-9257`, this one, plus `vast-water-9886`
  reconciled already) — a reconcile pass is due soon by the charter's count.

Dispatch closed: 1 unit — ADR-379 makes a weld and a declared running gap on
the same pair a failing fit check, closing the hole through which ot6's
floating-horn defect survived F4's whole four-turn repair; engine 2,160
passed, CLI 823 passed, packaged gate 21 passed, nine tests red on the old
code, and no design edited or slot spent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: f37e8a08dcb747c85412cafe200560e4d29a1916

## State Impact

- target: winter-key-1482 — F2's checker gains a fifth finding, ADR-379: a clearances= declaration on a pair an unsuppressed fixed joint welds is itself the failing check, 'clearance under weld', at any measured gap. The declared minimum is not consulted, because no gap makes 'one rigid body' and 'a running gap' both true. The engine publishes the welding joints on that declaration so a reader reaches the same verdict; the fit block, cadex clearance and the review's offending pairs all carry the status, and the block names the two repairs (close the gap and declare contacts=, or stop welding). A contacts= declaration on a welded pair agrees with the joint and is unchanged; a suppressed weld raises no contradiction. Reported, never refused. This narrows ADR-372's 'an explicit declaration still wins'.
- target: narrow-dune-9454 — F6's bar of zero failing static and swept fit checks is now harder to meet falsely: a balancer cannot weld a part on, declare a gap under the weld and pass. F6 itself remains blocked with all four slots unspent; no probe was taken this iteration and no frozen prompt was sent.
- target: rapid-grove-9687 — F7's bar tightens the same way and F7 remains blocked behind F6 with all four slots unspent.
- target: polished-forest-0215 — F4's measured result is unchanged and its numbers do not move: no retained receipt carries a clearance intent with joints. What it produced is a checker correction (ADR-379) that finally names the defect F4 left behind — both horn pairs welded to their links and declared a 0.05 mm clearance at a measured 0.2 mm, passing every check across four turns. A rebuild of ot7-heron-repair-d would now report two failing pairs where it reported none.
