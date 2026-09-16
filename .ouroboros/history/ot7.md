---
run: ot7
machine: sb1x
started: 2026-09-16T09:50:46
ended: 2026-09-16T14:28:00+00:00
hours: 0.6
state: killed
iterations: 75
commits: 94
criteria_ticked: 0
criteria_closed: 0
criteria_total: 10
merged: no
branch: ouroboros/ot7
memory: hypergraph
actor: claude:claude-fable-5-1
---

# Run ot7

75 iterations in 0.6h on `sb1x`, killed (2 stuck verdict(s) in a row). Branch `ouroboros/ot7`, not merged.

## The numbers

| | |
|---|---|
| iterations | 75 (changed 68, recorded 46) |
| commits | 94 — 164 files changed, 18961 insertions(+), 82 deletions(-) |
| criteria | **this run ticked 0**; 0 of 10 checked at the tip |
| reverts | 0 |
| verdicts | answer 5, continue 56, looping 4, reject 3, stuck 7 |
| loop detector | no firing |
| roles | actor claude:claude-fable-5-1, critic codex:gpt-6-astra |
| usage | claude seven_day 3% -> 51% (+48 this run); claude seven_day_overage_included 5% -> 100% (+95 this run); claude five_hour 51% -> 0% (-51 this run); codex seven_day 54% |

## What landed

- Every build reply carries the published catalog identity, advisory (ADR-362)
- F5 continue-3 on ot7-heron-c completed: no edit, static 0 of 105, sweep clean, smoke passing, servos and horns uncatalogued; F5 exhausted
- Restore actor fallback and document account refresh (ADR-361)
- REPORT.md: F5 attempts cell reads 3, all (three completed turns on ot7-heron-c)
- F5 continue-2 on ot7-heron-c completed: bench deleted by the agent, static fit 0 of 105, sweep complete with zero overlap, smoke passing, servos and horns still uncatalogued (receipt, REPORT.md, runner README)
- ADR-360 correction: an unknown describe_api section is refused after the argument-free engine request has been answered; only the section argument never reaches the engine (docs/CLI.md, ADR-360, slender-union-6486)
- ADR-360: describe_api reaches the model as an index and per-section pages under a measured 21,500-character budget; section is the bridge's argument, never the engine's; no design turn, window 52 % against the 45 % bound
- F5: continue-1 completed on ot7-heron-c — static fit 1 of 120 failing (bench as world geometry), sweep complete on both joints with zero overlap, servos and horns still uncatalogued, smoke passing; continue-2 next
- F5: the arm create turn completed on ot7-heron-c — static fit 7 of 120 failing, no sweep declared, servos and horns uncatalogued; describe_api still refused at 82,523 characters; continue-1 next after the reset
- ADR-359: describe_api fits one tool result; the ot7 collector dispatches at medium effort
- ot7 report: F5 row counts two accepted probe scripts of three written, F4 row counts four completed turns
- F5: the arm create call on ot7-heron-b interrupted at the 30-minute bound — no design written, no slot spent, retry ot7-heron-c
- F4: continue-3 completed on ot7-heron-repair-d — no edit, unchanged script re-accepted at f03054d6, DECISION and NOTE design_specs lines written, F4 exhausted
- F4: continue-2 completed on ot7-heron-repair-d — no failing check named, no edit, unchanged script re-accepted; one continuation left
- ot7 runner: read the five-hour window before every frozen prompt, pause without room (ADR-358)
- F4: continue-1 completed on ot7-heron-repair-d — zero failing product checks static and swept, catalog servos restored, bench removed, horn gap still declared as clearance; two continuations left
- ot7 runner: the repair prompt is F4's first prompt, not its only one; resume the next continuation without replay (ADR-357)
- F4: the frozen repair prompt completed on ot7-heron-repair-d — zero failing product checks, two of three defects resolved, horn gap declared not closed; repair-c void
- ouroboros #46: no record
- F4: frozen repair prompt reached the model on ot7-heron-repair-b; timed out at the 30-minute bound, no submission
- ot7 runner: a synthetic frame alone is not a usage limit; auth failures spend their slot (ADR-355)
- ot7 runner: usage-limit calls are void; classify the six pre-restart calls (ADR-355)
- ot7 charter: usage-limit failures are void; restart (ADR-355)
- docs: hand off ot7 as exhausted and incomplete
- Record frozen F4 collector refusal and unchanged fit evidence
- ... and 27 more

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
