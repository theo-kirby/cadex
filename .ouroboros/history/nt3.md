---
run: nt3
machine: mmini
started: 2026-09-07T22:39:45
ended: 2026-09-08T09:05:19+00:00
hours: 12.3
state: killed
iterations: 201
commits: 258
criteria_ticked: 0
criteria_closed: 9
criteria_total: 13
merged: d00b86de925d2b88ea410d43c64d1b5b7b0c90d1
branch: ouroboros/nt3
mode: actor-critic
memory: hypergraph
actor: claude:claude-opus-5
---

# Run nt3

201 iterations in 12.3h on `mmini`, killed (-). Branch `ouroboros/nt3`, merged as `d00b86de`.

## The numbers

| | |
|---|---|
| iterations | 201 (changed 67, recorded 67) |
| commits | 258 — 315 files changed, 22668 insertions(+), 238 deletions(-) |
| criteria | **this run ticked 0**; 9 of 13 checked at the tip |
| reverts | 0 |
| verdicts | continue 63, stuck 138 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5, critic codex:gpt-6-astra, maintainer claude:claude-opus-5, overseer claude:claude-opus-5, planner claude:claude-opus-5 |
| usage | claude seven_day 35% -> 54% (+19 this run); claude five_hour 13% -> 65% (+52 this run); codex seven_day 6% -> 51% (+45 this run) |

## What landed

- Check the walk's clearance against the render's bounds (ADR-248)
- docs: remove stale engine-suite count from command guidance
- docs: point onboarding version guidance at project config
- docs(cli): clarify project Git ownership and commit scope
- Preserve project metadata for unchanged CLI sessions
- Keep walk output labels portable in project history
- A design turn can reach the domain-doc convention (ADR-245)
- Keep worker bundles consistent with their content identity
- Teach separate purchased hardware placement in lifecycle design
- Keep inventory counts tied to placed catalog components
- ouroboros #36: Two-servo leg rehearsal stops at the design provider quota
- Sweep clearance where the assembly puts a component
- Record the corrected clearance numbers on the walk that found the defect
- Measure clearance where the assembly puts a component
- Clarify CLI payload schema guarantee
- docs: clarify policy assets regardless of training hardware
- docs: clarify CPU toy training within the offboard boundary
- docs: point agent orientation to current lifecycle state
- docs: describe shipped solver-change recovery
- Verify lifecycle policy and review survive a cold revisit
- Evidence carriage review alongside arm; initial-pose scope; 195 CLI tests pass
- Evidence fresh arm complete headless review; initial-pose limits, 195 CLI tests pass
- Include accepted sections in lifecycle review
- Add headless named-plane sections with cavity-preserving contours
- Verify fresh hinged-arm walk with committed previews
- ... and 12 more

## Bets the planner changed

- #1: glad-snow-3838 — Bet: the walk from a prompt leads; close its two named legs, then re-run; headless review steps down to medium
- #3: rustic-loom-0992 — Bet: the re-run decides the tick; the second mechanism walks from a prompt next; inventory returns to short
- #5: restless-star-0524 — Bet: three modes leads as an evidence unit; the review step is wired to the inventory; the clearance check returns in the inventory''s shape
- #7: crimson-canyon-5993 — Bet: inventory wiring leads after mode parity; clearance must include separated pairs
- #9: humble-stream-3878 — Bet: rerun the walk after clearance, then wire review and probe rendering
- #11: mellow-beacon-8815 — Bet: rerun the walk, deliver CPU views, then integrate review
- #13: nimble-beacon-7598 — Bet: integrate delivered views before section promotion
- #15: witty-brook-9419 — Bet: promote sections after verified preview rehearsal
- #17: sage-crow-3224 — Bet: rehearse complete review one mechanism at a time
- #19: modest-grotto-1192 — Bet: preserve the completed walk across a cold project revisit
- #21: green-wolf-7549 — Bet: fold cold-revisit success and dispatch recovery documentation correction
- #23: first-wing-3387 — Bet: remove stale frontier snapshots from agent orientation
- #25: civic-snow-4700 — Bet: dispatch the offboard-training guidance correction
- #27: empty-rain-5162 — Bet: qualify the ordinary bundled engine through the headless walk
- #29: spring-wolf-7431 — Bet: bound the payload identity guarantee to its actual check

## Decisions the overseer made

- #23 stuck: The reconciliation handoff has repeated without execution, and the critic requires reconciliation and planning before further actor work.
- #45 stuck: Iteration 45 repeats the unchanged scheduling blocker without advancing a frontier criterion, despite the prior steer to reconcile and replan.
- #47 stuck: Iteration 47 repeated the scheduling-only dead end despite the explicit controller hold and advanced no frontier criterion.
- #48 stuck: Iteration 48 repeats the expressly prohibited scheduling-only dead end and leaves the critic’s required rehearsal unresolved.
- #49 stuck: Iteration 49 repeats the scheduling-only dead end; the controller must enforce eligibility before the pending rehearsal can advance.
- #50 stuck: Iteration 50 repeats the controller scheduling dead end before eligibility and provides no new product evidence.
- #51 stuck: Iteration 51 repeats the controller scheduling dead end without eligibility evidence, a rehearsal, or product progress.
- #52 stuck: Iteration 52 repeats the controller scheduling dead end for a fourth unchanged iteration without advancing the pending rehearsal.
- #53 stuck: Iteration 53 repeats the scheduling dead end for a fifth unchanged iteration without eligibility evidence or product progress.
- #54 stuck: Iteration 54 is the sixth unchanged iteration in a controller scheduling dead end, with no new eligibility evidence or rehearsal.
- #55 stuck: Seven unchanged iterations demonstrate that the controller-only eligibility rule is preventing progress; one clock check is a reversible way to resolve it.
- #56 stuck: Eight unchanged iterations expose a controller scheduling loop; the reported clock still precedes eligibility, so another actor check would add no evidence.
- #57 stuck: Nine unchanged iterations show a controller scheduling deadlock, not a product blocker the actor can resolve before eligibility.
- #58 stuck: Ten unchanged iterations demonstrate a controller scheduling deadlock; the pending rehearsal remains the only authorized unit.
- #59 stuck: Eleven unchanged iterations show a controller scheduling deadlock; no new evidence authorizes the pending rehearsal or another unit.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The run that produced the loop detector. 201 iterations, 22,437 lines, 128 new
record nodes, and **one** node changed status. From iteration ~49 onward the
planner wrote the same bet in new words every time -- "retain the conditional
rehearsal after N unchanged iterations" -- because a previous plan had gated the
work on a *wall-clock* condition the actor had no way to satisfy. 138 `stuck`
verdicts and 67 changed iterations out of 201.

Three things came from it: `ouroboros.loops` (motion is not progress: no product
change, no frontier movement, a planner restating itself), a charter ban on
gating a unit on the wall clock, and a 20-iteration overseer history instead of
3, because the overseer could not see a stall it was only shown three frames of.

Replayed against this run's own log, the detector first fires at iteration 50 --
one iteration into the stall -- and never fires in either productive stretch.
