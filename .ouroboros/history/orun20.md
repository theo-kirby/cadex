---
run: orun20
machine: sb1x
started: 2026-10-24T07:01:04
ended: 2026-10-24T16:18:35+00:00
hours: 5.2
state: killed
iterations: 6
commits: 10
criteria_ticked: 1
criteria_closed: 1
criteria_total: 11
criteria_unknown: 0
criteria_source: run-local memory snapshot
merged: no
branch: ouroboros/orun20
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun20

6 iterations in 5.2h on `sb1x`, killed (-). Branch `ouroboros/orun20`, not merged.

## The numbers

| | |
|---|---|
| iterations | 6 (changed 6, recorded 0) |
| commits | 10 — 42 files changed, 9522 insertions(+), 49 deletions(-) |
| criteria | **this run completed 1**; 1 of 11 verified met; 0 unknown (run-local memory snapshot) |
| reverts | 0 |
| verdicts | continue 6 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 20% -> 23% (+3 this run); claude five_hour 16% -> 23% (+7 this run) |

## What landed

- orun20 S1h variant B: lofted jaw, round nose and chin tips (leon-soft-head-b rev 77ee9670): head 0 sharp corners, 4 under 4 mm (left ear slot); G1 clean; corners.py skips periodic seams
- orun20 S1h variant A: lofted soft head (leon-soft-head-a rev 3df4a511): 3 rounded panels, half-disc ears; head 153 -> 23 sharp corners; G1 clean; corners.py --part
- orun20 S1 roll-out: leon-soft's body regions rounded (rev 3699a3fd): 37 body panels 0 sharp, smallest 6.42 mm; sharp corners 313 -> 153 (all on the head); leon-sleek baseline 092997dd
- orun20 S1 rung 3-4: leon-soft from leon I (baseline 092997dd, measures identical); rounded skin regions round panel corners (saddle lab: 12 sharp -> 0, >= 6.19 mm), cut-panel fillets refused; corners.py reads the pinned attempt (ADR-311)
- orun20 K2: corners.py measures a build's sharp-edge share and its panels' outline-corner radii; leon I baseline
- orun20 K1: cadex hero --only views (six fixed cameras from the design's front) and a labelled hero-grid (ADR-792); leon I's set

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)
