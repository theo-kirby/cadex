---
run: ot8
machine: sb1x
started: 2026-09-20T14:45:21
ended: 2026-09-21T02:26:29+00:00
hours: 7.7
state: stopped
iterations: 10
commits: 18
criteria_ticked: 0
criteria_closed: 0
criteria_total: 6
merged: no
branch: ouroboros/ot8
memory: hypergraph
actor: claude:claude-opus-5
---

# Run ot8

10 iterations in 7.7h on `sb1x`, stopped (critic accepted done 2x in a row). Branch `ouroboros/ot8`, not merged.

## The numbers

| | |
|---|---|
| iterations | 10 (changed 10, recorded 7) |
| commits | 18 — 47 files changed, 4652 insertions(+), 57 deletions(-) |
| criteria | **this run ticked 0**; 0 of 6 checked at the tip |
| reverts | 0 |
| verdicts | continue 7, done_accepted 2, done_rejected 1 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5, critic claude:claude-opus-5 |
| usage | claude seven_day 15% -> 25% (+10 this run); claude five_hour 3% -> 37% (+34 this run) |

## What landed

- ot8 G6: the closing report, one row per experiment (ADR-403)
- ot8 G5: the regression floor measured at the final revision
- ot8 G4: the balancer's failed smoke is a measured control requirement (ADR-402)
- ot8 G2: the arm reaches zero failing fit with every purchased part catalogued
- ot8 G3: the biped's smoke passes on its own accepted pin (ADR-401)
- ot8 G1: freeze the experiment contract and reuse the collector (ADR-400)

## Decisions the critic made

- #8 done_rejected: G6's artifacts and tests look real, but the charter makes reconciling part of G6, and three records are still unreconciled, so the frontier still shows G4–G6 open.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The bounded follow-up resolved two evidence gaps in one product turn each:
Heron's purchased parts kept catalog identity, and Plover's own accepted
artifacts passed smoke. Robin's failed smoke is a control requirement with a
measured contract, not an unfinished geometry repair. Keep experiment completion
separate from design success in the next charter. The owner boxes remain unticked
even though the critic accepted done; review the receipts before checking them.
