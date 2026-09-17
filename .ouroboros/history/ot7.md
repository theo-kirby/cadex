---
run: ot7
machine: sb1x
started: 2026-09-17T10:53:10
ended: 2026-09-17T16:11:11+00:00
hours: 1.3
state: killed
iterations: 148
commits: 175
criteria_ticked: 0
criteria_closed: 0
criteria_total: 10
merged: no
branch: ouroboros/ot7
memory: hypergraph
actor: claude:claude-fable-5
---

# Run ot7

148 iterations in 1.3h on `sb1x`, killed (limit resets in 29 min: sage credits at claude.ai/settings/usage?from=cc_cli_limit_message, to continue.). Branch `ouroboros/ot7`, not merged.

## The numbers

| | |
|---|---|
| iterations | 148 (changed 111, recorded 77) |
| commits | 175 — 206 files changed, 29910 insertions(+), 114 deletions(-) |
| criteria | **this run ticked 0**; 0 of 10 checked at the tip |
| reverts | 0 |
| verdicts | answer 5, continue 89, looping 8, reject 9, stuck 37 |
| loop detector | no_frontier ×38 (longest streak 67) |
| roles | actor claude:claude-fable-5, critic claude:claude-fable-5 |
| usage | claude seven_day 7% -> 50% (+43 this run); claude seven_day_overage_included 13% -> 100% (+87 this run); claude five_hour 11% -> 5% (-6 this run) |

## What landed

- F6: Robin's create dispatched on Fable — b interrupted at launch, c completed with 0 of 276 failing
- Resume ot7 remaining experiments on Fable (ADR-383)
- Absent provenance is unknown, not printed (ADR-382)
- A modified purchase says what it was cut from (ADR-381)
- A fixed joint holds a pose; it does not require touching (ADR-380)
- A weld and a declared gap on the same pair contradict each other (ADR-379)
- F6 window probe five: still refused, and the fixed gate read it right
- Cite ADR-378's own commit in the closing report
- A gap the motion closes is a failing fit (ADR-378)
- Cite ADR-377's own commit in the closing report
- A design that toppled and settled is not resting on the floor (ADR-377)
- Cite ADR-376's own commit in the closing report
- The frame that bound the call is the reading, in both directions (ADR-376)
- Cite ADR-375's own commit in the closing report
- A joint nobody bounded is a coverage hole, not a silence (ADR-375)
- The swept row's motion flag is pinned against its contract (ADR-374)
- The closing receipts count ADR-374, and the contract names its field
- A welded pair does not define the joint it cannot move (ADR-374)
- F9's weld-exemption table says only what it models
- F9's regression receipt says what the checker now does, and pins both columns
- A gap the design means is declared, not widened (ADR-373)
- A welded pair is not an undeclared pair (ADR-372)
- A suppressed joint is not missing coverage (ADR-371)
- A fixed joint that holds nothing is measured and said (ADR-370)
- A refused probe reads the frame that rejected (ADR-369)
- ... and 61 more

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
