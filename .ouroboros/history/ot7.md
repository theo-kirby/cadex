---
run: ot7
machine: sb1x
started: 2026-09-19T13:29:36
ended: 2026-09-20T03:03:15+00:00
hours: 9.6
state: stopped
iterations: 172
commits: 222
criteria_ticked: 0
criteria_closed: 0
criteria_total: 10
merged: fa75c5318eb226da0e297dd9341a59e58ef8b669
branch: ouroboros/ot7
memory: hypergraph
actor: claude:claude-opus-5
---

# Run ot7

172 iterations in 9.6h on `sb1x`, stopped (critic accepted done 2x in a row). Branch `ouroboros/ot7`, merged as `fa75c531`.

## The numbers

| | |
|---|---|
| iterations | 172 (changed 134, recorded 92) |
| commits | 222 — 268 files changed, 41411 insertions(+), 241 deletions(-) |
| criteria | **this run ticked 0**; 0 of 10 checked at the tip |
| reverts | 0 |
| verdicts | answer 5, continue 110, done_accepted 2, looping 8, reject 9, stuck 38 |
| loop detector | no_frontier ×38 (longest streak 67) |
| roles | actor claude:claude-opus-5, critic claude:claude-opus-5 |
| usage | claude seven_day 1% -> 15% (+14 this run); claude five_hour 7% -> 13% (+6 this run) |

## What landed

- Record ot7 merge review and final verification
- Preserve accepted artifacts across restore comparisons (ADR-398)
- ot7's closing report: one row per design, and a test that holds it (ADR-397)
- The geometry fallback stops reading derived artifact bytes (ADR-396)
- Smoke the model the fixed engine exports, without spending a slot (ADR-395)
- Measure ADR-393's reach on the three retained ot6 designs (ADR-394)
- Pair a connector frame with the component FreeCAD left it on (ADR-393)
- Smoke a paused attempt without spending a slot (ADR-392)
- Collect F7's continue-1: the biped's twelve buried fasteners removed
- Collect F6's continue-3: Robin exhausted, fit clean, smoke failed
- Collect F7's plover-e create turn: the biped the agent actually built
- A second closing smoke gets its own directory (ADR-391)
- Dispatch and collect F6's continue-2: the turn that refused to edit
- Collect F6's continue-1 turn: the sweep the create turn left unmeasured
- Rule ot7-plover-d void as a design result (ADR-390 amendment)
- Collect F7's plover-d create turn, and never publish a bundle that cannot import itself (ADR-390)
- A geometry digest for bytes that are not a function of the inputs (ADR-389)
- Raise the ot7 turn bound to an hour and finalise a dead runner (ADR-388)
- F7's create turn reaches the model and runs out of clock (ADR-356)
- Follow the active run in the operator review dashboard (ADR-387)
- A call that never reached the model spends no frozen slot (ADR-386)
- Recover ot7 deadline crash with relative 48h budget (ADR-385)
- Continue ot7 on Opus with explicit resume model history (ADR-384)
- F6: Robin's create dispatched on Fable — b interrupted at launch, c completed with 0 of 276 failing
- Resume ot7 remaining experiments on Fable (ADR-383)
- ... and 84 more

## Decisions the critic made

- #3 reject: F1 is claimed complete, but fit_summary deliberately omits failing pairs beyond the first 40, contradicting its explicit acceptance criterion.
- #35 looping: The requested biped dispatch produced honest negative evidence, but repeated provider refusals now require a consolidated outcome rather than more collection work.
- #37 answer: The documented dispatch conflict explains the deviation and requires an explicit housekeeping decision rather than rejection.
- #38 looping: The authorized reconcile is sound, but twelve iterations without frontier movement require returning to the outstanding real F4 experiment.
- #39 looping: The requested dispatch was recorded honestly, but six provider refusals and thirteen iterations without frontier movement leave no authorized experiment remaining.
- #40 answer: The report honestly records exhaustion, and further iterations cannot establish the missing design outcomes within the remaining authorization.
- #42 reject: The classifier treats every synthetic assistant error as a usage limit, contradicting its documented rule and incorrectly refunding unrelated failures.
- #44 answer: The iteration preserves useful experimental evidence honestly, but the interrupted call requires a charter-based slot ruling and collector fixes.
- #45 answer: The scheduled reconcile preserves evidence but omits the explicit slot ruling already issued in decision #44.
- #47 stuck: Iteration 47 changed nothing and left iteration 46's verification and causal record unfinished.
- #48 reject: The completed repair provides real evidence, but declaring F4 exhausted after one prompt contradicts the charter and gives its state impact an incorrect outcome.
- #55 answer: The interrupted experiment is recorded honestly and spends no slot, but its measured thinking overhead warrants lowering effort before retrying.
- #63 looping: The iteration added only a waiting record and prescribed repeating it, despite the explicit instruction to make no change while limited.
- #64 stuck: No change was made because the product-agent window remains limited; the charter explicitly permits waiting without manufacturing work.
- #65 stuck: The iteration made no change while honoring the explicit waiting instruction, which the charter permits during a limited product-agent window.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)

## What this taught

The product agent and the actor share one Claude account, so a spent five-hour
window stops both at once. After Claude ran out at 20:17 UTC, the Codex fallback
actor went ahead with the frozen F4–F7 design turns. All six "provider refusals"
are that session limit, each failing in 2–4 s. The critic counted them as spent
attempts, ruled the run exhausted, and in iteration 41 told the actor to stop
the run, which it did by running `ouroboros stop` itself. The tooling half
(F1–F3, F8, F9) landed and is evidenced; the agent half (F4–F7) was never
tried. The charter needs three rules it lacked: a harness limit is not an
attempt, design turns wait for the product agent's harness, and no role may
stop or start the run.

## What this taught — owner-directed wait (2026-09-17)

The live charter reload worked: the loop finished its correction and reconciliation, then preserved the unspent design slots while access remained unproven. A charter-directed wait still dispatches actor and critic turns and triggers generic no-frontier model rotation; a future runner-level waiting state should suppress both, rather than spending subscriptions to reconfirm the hold. One forbidden waiting record was rejected and reverted, so review the final tree rather than treating every rejection as an outstanding defect; this run stopped on its time limit, not successful completion.


## What this taught — final review (2026-09-20)

The completed follow-up did reach the product model: all four designs reached
zero failing static checks, but the arm's purchased-part identity and the
balancer's holding smoke missed their success bars. The biped's smoke used a
re-exported model, leaving an accepted-artifact evidence gap for the next run.
Completion therefore means the bounded experiment finished, not universal
design success; the zero tick count also reflects owner-owned checkboxes.

Review found that successful repeated restores could still prune the accepted
artifacts. ADR-398 defers collection until the accepted pin is settled and
tests retention as well as reopen success. Future lifecycle evidence must
check that the data behind a pin survives, not just that the service says yes.
Keep capacity waits out of the work log and separate a balancer's feedback
requirement from mechanical fit; neither is solved by more bookkeeping.
