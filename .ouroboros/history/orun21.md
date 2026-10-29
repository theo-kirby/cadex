---
run: orun21
machine: sb1x
started: 2026-10-28T17:56:20
ended: 2026-10-29T15:37:04+00:00
hours: 17.4
state: killed
iterations: 39
commits: 56
criteria_ticked: 8
criteria_closed: 8
criteria_total: 13
criteria_unknown: 0
criteria_source: run-local memory snapshot
merged: no
branch: ouroboros/orun21
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun21

39 iterations in 17.4h on `sb1x`, killed (-). Branch `ouroboros/orun21`, not merged.

## The numbers

| | |
|---|---|
| iterations | 39 (changed 39, recorded 0) |
| commits | 56 — 98 files changed, 12228 insertions(+), 526 deletions(-) |
| criteria | **this run completed 8**; 8 of 13 verified met; 0 unknown (run-local memory snapshot) |
| reverts | 0 |
| verdicts | continue 39 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 84% -> 98% (+14 this run); claude five_hour 39% -> 2% (-37 this run) |

## What landed

- orun21 G3: tracking_lin_vel σ/4 on leon V's concept — every walk leg 0.96–0.99, but the policy stands still above 1.1 m/s (1/10); the writer keeps 0.25, next a kernel shaped like the judge's relative tolerance
- orun21 G3 step back: the slow walk read step by step — the policy's near-absolute miss at the band floor, where the tracking kernel is flat; the layer and the judge's denominator ruled out
- orun21 G3/K1: the biped through RECIPE.md alone — speeds scale the writer, turn-in-place exits at 30°, judge on the export (ADR-865)
- orun21 C1: REPORT.md written from what is measured so far — criteria, M0 before/after, tier ADR, go-to-point and terrain per robot, still slow, next run
- orun21 K1: RECIPE.md rewritten as the route a new robot follows: route, go-to-point task, terrain, defaults, budgets, limits (ADR-864)
- orun21 G3: the relay sets substeps from the model's own step; share 0 does not lift leon V's slow walk (0/10 vs 4/10) (ADR-863)
- orun21 G3: G2's task written onto any robot (cadex_joystick.py); leon V's concept reaches and holds every held-out point with no fall but passes 4/10 on slow-walk speed; play reads a fall from the base's COM (ADR-862)
- orun21 T2: the feet block screened against a control; level 4 does not move (1/10 vs 3/10), T2 closes at level 0 and the maze through level 2 on one policy (ADR-861)
- orun21 T2: go-to-point through a maze; the Go1 scan policy passes 10/9/10 of 10 held-out maze seeds at levels 0-2 with no body in a wall (ADR-860)
- orun21 T2-SCAN.md: the feet block is ADR-870
- orun21 T2: go1-scan warm-extended 73.7 M steps; level 4 unreached 50 -> 24/80 but passes stay 1/10 and flat speed drops 10 -> 6
- orun21 T2: a warm start hands the Go1 actor a height scan at zero weight; level 2 1/10 -> 6/10 (ADR-859)
- orun21 T2: go-to-point judged on held-out courses; cadex_goto play --course (ADR-858)
- orun21 T2: terrain laid round the start, so go-to-point points meet it (ADR-857)
- orun21 T1: ADR-856's fall reading taken from the log, not the last line
- orun21 T1: terrain levels from the engine's pool, and the game-inspired curriculum on points reached (ADR-856)
- orun21 T1: a course from a mesh asset is sampled onto the heightfield grid; the dashboard's heightfield is no longer mirrored in y (ADR-855)
- orun21 T1: heightfields train when only spheres and capsules touch them; box or mesh on one is refused (ADR-854)
- orun21 T1: tile patches and mazes, terrain laid out in x and y (ADR-853)
- orun21 T1: the engine places every terrain box; the trainer builds no course (ADR-852)
- orun21 D2: the dashboard's wrong states ranked; bare-run checkpoints play, rebuild pins keep triangles, the card reads the page's run (ADR-851)
- orun21 S1: the two representative iterations re-timed after the cuts (ITERATION.md §9)
- orun21 S1: the part cache is not keyed by the document's object list; restore and build share it (ADR-850)
- orun21 S1: the trainer compiles its witness and view rollout once and keeps compiled programs between runs (ADR-849)
- orun21 S1: cadex export copies the retained accepted attempt; --rebuild re-proves it (ADR-848)
- ... and 16 more

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)
