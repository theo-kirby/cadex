---
run: orun1
machine: sb1x
started: 2026-10-02T12:59:09
ended: 2026-10-03T09:31:15+00:00
hours: 15.9
state: killed
iterations: 33
commits: 55
criteria_ticked: 0
criteria_closed: 0
criteria_total: 6
merged: 3e345fd26623ad28b662595b1ce81c63eabbf54b
branch: ouroboros/orun1
memory: hypergraph
actor: claude:claude-opus-5-5
---

# Run orun1

33 iterations in 15.9h on `sb1x`, killed (-). Branch `ouroboros/orun1`, merged as `3e345fd2`.

## The numbers

| | |
|---|---|
| iterations | 33 (changed 30, recorded 17) |
| commits | 55 — 124 files changed, 17009 insertions(+), 364 deletions(-) |
| criteria | **this run ticked 0**; 0 of 6 checked at the tip |
| reverts | 0 |
| verdicts | continue 30, stuck 3 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5 |
| usage | claude seven_day 8% -> 23% (+15 this run); claude five_hour 2% -> 9% (+7 this run) |

## What landed

- orun1 D4: DESIGN-LANGUAGE carries ADR-494's cap and leg rules
- orun1 D4: ADR-494 a joint is one small cap, a leg is long against it
- orun1 D4: balancer trial 4 — fit pass, mounting 12/12 via .mounting(), judge v2 3/5
- orun1 D3: ADR-493 a board is screwed down by its own .mounting()
- orun1 D3: ADR-492 a bolt holds only by its thread, and the fit allows the thread
- orun1 D3: ADR-491 servo.bay(ledge=4) gives the lead-side tab screw its thread
- orun1 D4 hexapod trial 1: fit/sweep pass, mounting 49/49, frozen v2 1 of 2 (loses to c on proportions)
- ouroboros #25: no record
- orun1 D4 balancer trial 3: fit/sweep pass, mounting 11/11, frozen v2 4 of 5
- guidance: comma after the press-fit clause in HOLD EVERY PART
- D3/D4: the catalog wheel is a spoked rim and its tyre a part of its own; mounting check holds a tyre on its wheel's rim (ADR-489)
- D3: mounting check requires a bolt to fit its hole; catalog M1.6 fasteners (ADR-488)
- D4 trial 2: balancer at 9eac2291 -- sweep now passes (ADR-487), mounting 5/9 (no M1.6 bolt, no gearmotor bay), frozen v2 3 of 5; record ADR-487
- ouroboros #18: no record
- D4 trial 1: balancer from the frozen prompt -- 9/9 held, static fit clean, sweep incomplete (catalog D-shaft), frozen v2 3 of 5
- D4: freeze the seven plain prompts before any generation, and the versus runner that judges a new design with frozen v2
- D3: every build reply says what holds each purchased part -- screws on a hole axis, its own bay, press fit or a drive's output; contact only, inside a shell or nothing is reported (ADR-486)
- ouroboros #14: no record
- D2: design language and overlay rewritten from the owner's ratings, inside out as the procedure; face, soft primitive, hidden hardware and split-lines-only removed; ot10 rubric retired (ADR-479 to ADR-484)
- D1: frozen judge v2 on held-out, measured once -- 97.3% gap-pair agreement (36/37), Love>No holds, tau-b 0.436 over 325 pairs; ot10 baseline 13.5% (ADR-478)
- D1: pairwise hero-only judge built on dev -- v1 81.5%, v2 90.7% (mirror identical); v2 frozen before any held-out call (ADR-478)
- D1 baseline: ot10's frozen judge on all 26 held-out designs -- 13.5% gap-pair agreement, Love>No fails, tau-b -0.079
- ouroboros #5: no record
- ouroboros #4: no record
- D1 baseline: held-out metrics and their test, before any judge call
- ... and 2 more

## Decisions the critic made

- #9 stuck: Nothing changed this iteration: no diff, no handoff and an empty final message.
- #10 stuck: For the second iteration running there is no diff, no handoff and no final message, while the next D1 unit is fully specified in the README.
- #24 stuck: No diff, no handoff and no final message this iteration, while a concrete D3 catalog gap from trial 3 is waiting.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

**Stopped by the owner at iteration 33, for scope rather than progress.**
The charter's premise was too narrow. It wrote one design language for one
kind of machine: small printed robots on hobby servos, in a style the owner
rated. The owner's verdict on reading the rewritten language was that this
is *one style* Cadex should offer, not the definition of Cadex design.
Cadex must also design an industrial vacuum robot, a crane, or eventually a
factory. Write the next charter as a general base that every design gets,
plus styles a project chooses, and test it on subjects of very different
scale.

**Do not tell the agent to make things "look engineered".** The owner
rejected the phrase: it sounds fake and invites decoration that only imitates
engineering. The rule is form follows function. A part is there because it
has a job, and the look comes from the job, the loads and the way the part is
made.

**What generalises, and was merged:**
- the F1 reopen fix;
- the mounting check (bolt fit, thread engagement, board `.mounting()`, the
  servo bay ledge);
- the catalog additions;
- the owner-calibrated judge method. Frozen v2 agreed with the owner on 36
  of 37 held-out gap pairs, against 13.5% for ot10's rubric.

Calibrating a judge against owner ratings is the reusable part. It is how
any style can be defined.

**Proportion rules learned on one thing over-fit.** ADR-494 (joint cap, leg
length) came from balancer and hexapod trials scored by a judge trained on 55
small robots. Such rules belong to a style, not to the base.

**Three stuck iterations (#9, #10, #24) were empty actor turns** with no diff
and no message, each followed by a normal turn. Treat them as harness noise
unless they cluster.
